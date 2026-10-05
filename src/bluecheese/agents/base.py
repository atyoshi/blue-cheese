from typing import Protocol

from bluecheese.domain.models import TriageResult


class TriageAgent(Protocol):
    def analyze(self, alert: dict, related: list[dict]) -> TriageResult:
        ...
