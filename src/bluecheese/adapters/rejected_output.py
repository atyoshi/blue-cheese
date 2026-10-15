"""Opt-in, bounded local candidate retention, separate from evidence and exports."""

import hashlib
import json
import os
import re
from pathlib import Path


def content_hash(value):
    data = value if isinstance(value, str) else json.dumps(value, sort_keys=True)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


class RejectedOutputSink:
    """Retain only rejected response text; callers never pass headers or error bodies."""

    max_bytes = 16384

    def __init__(self, directory, *, secrets=()):
        self.directory = Path(directory)
        self.secrets = tuple(secret for secret in secrets if secret)

    def __call__(self, candidate, metadata):
        text = candidate
        for secret in sorted(self.secrets, key=len, reverse=True):
            text = text.replace(secret, "[REDACTED]")
        text = re.sub(
            r"(?i)(\b(?:bearer|basic)\s+)[A-Za-z0-9+/_.=:-]+",
            r"\1[REDACTED]",
            text,
        )
        text = re.sub(
            r"""(?i)((?:["']?(?:api[_-]?key|password|secret|access[_-]?token)["']?)\s*[:=]\s*)("[^"\n]*"|'[^'\n]*'|[^\s,;}]+)""",
            r'\1"[REDACTED]"',
            text,
        )
        encoded = text.encode("utf-8")
        record = {
            **metadata,
            "redacted": text != candidate,
            "truncated": len(encoded) > self.max_bytes,
            "candidate": encoded[: self.max_bytes].decode("utf-8", errors="ignore"),
        }
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        # Accept only generated identifiers, never model-provided filenames.
        identity = "-".join(
            str(metadata[key]) for key in ("run_id", "role", "operation_id")
        )
        name = hashlib.sha256(identity.encode()).hexdigest() + ".json"
        path = self.directory / name
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            json.dump(record, output, ensure_ascii=True, indent=2)
            output.write("\n")
        return {
            "status": "SAVED",
            "redacted": record["redacted"],
            "truncated": record["truncated"],
        }
