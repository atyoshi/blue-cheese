from typing import Protocol

from bluecheese.domain.models import NormalizedAlert, TriageResult


class TriageAgent(Protocol):
    def analyze(self, alert: NormalizedAlert) -> TriageResult:
