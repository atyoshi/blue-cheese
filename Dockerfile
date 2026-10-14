FROM node:22-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.14-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 BLUECHEESE_STATE=/state
WORKDIR /app
COPY requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock
COPY pyproject.toml ./
COPY src ./src
COPY --from=frontend /src/bluecheese/interfaces/static ./src/bluecheese/interfaces/static
RUN pip install --no-deps --no-build-isolation . \
    && groupadd --gid 10001 bluecheese \
    && useradd --uid 10001 --gid 10001 --create-home bluecheese \
    && mkdir /state /telemetry \
    && chown 10001:10001 /state
USER 10001:10001
EXPOSE 8501
HEALTHCHECK --interval=15s --timeout=3s --start-period=20s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/health')"
CMD ["python", "-m", "bluecheese.interfaces.server", "--host", "0.0.0.0", "--port", "8501", "--no-browser"]
