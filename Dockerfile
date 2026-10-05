FROM python:3.14-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    BLUECHEESE_STATE=/state BLUECHEESE_REPLAY=/replay
WORKDIR /app
COPY requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-deps --no-build-isolation . \
    && groupadd --gid 10001 bluecheese \
    && useradd --uid 10001 --gid 10001 --create-home bluecheese \
    && mkdir /state /replay /telemetry \
    && chown 10001:10001 /state /replay
USER 10001:10001
EXPOSE 8501
HEALTHCHECK --interval=15s --timeout=3s --start-period=20s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health')"
CMD ["python", "-m", "streamlit", "run", "src/bluecheese/interfaces/demo.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true", "--browser.gatherUsageStats=false"]
