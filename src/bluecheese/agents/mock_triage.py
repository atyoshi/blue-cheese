from bluecheese.domain.models import NormalizedAlert, TriageResult

class MockTriageAgent:
    """Temporary deterministic stand-in for a future agent."""

    def analyze(self, alert: NormalizedAlert) -> TriageResult:
        if alert.severity is not None and alert.severity <= 2:
            priority = "medium"
        else:
            priority = "low"

        return TriageResult(
            priority=priority,
            disposition="needs_review",
            rationale=(
                "Mock result based only on the Suricata severity. "
                "No contextual investigation has been performed."
            ),
        )
