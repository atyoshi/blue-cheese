"""Validate a user-supplied local telemetry path before starting ingestion."""

import os
import stat
from pathlib import Path


def readable_eve_path(value):
    if not str(value).strip():
        raise ValueError(
            "Enter the path to an existing Suricata EVE file on this server."
        )
    path = Path(str(value).strip()).expanduser().resolve()
    try:
        # Nonblocking open prevents a mistaken FIFO/device path from hanging the UI.
        descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise ValueError(f"EVE source must be a regular file: {path}")
        finally:
            os.close(descriptor)
    except FileNotFoundError:
        raise ValueError(
            f"EVE file does not exist: {path}. Select the sensor's actual output file. "
            "/telemetry is a Docker mount; native launches use a host path."
        ) from None
    except PermissionError:
        raise ValueError(
            f"EVE file is not readable by the app's operating-system user: {path}"
        ) from None
    return path
