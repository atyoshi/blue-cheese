"""Inspectable, bounded triage policy. No model is required for the demo."""

from bluecheese.domain.models import TriageResult

POLICY_VERSION = 'rules-v1'


class TriageAgent:
    def analyze(self, alert: dict, related: list[dict]) -> TriageResult:
        severity = alert['severity']
        signature = (alert['signature'] or '').lower()
        priority = 'high' if severity == 1 else 'medium' if severity == 2 else 'low'
        reasons = [f"Suricata severity {severity if severity is not None else 'unknown'}." ]

        if 'info' in signature or 'teamviewer' in signature:
            if priority == 'high':
                priority = 'medium'
            reasons.append('Signature appears informational or describes remote access software.')

        supporting = [event for event in related if event['event_type'] in ('flow', 'dns', 'http', 'tls')]
        if supporting:
            reasons.append(f'{len(supporting)} related network observation(s) are available for review.')
        else:
            reasons.append('No related network observations were found in this import.')

        return TriageResult(
            priority=priority,
            disposition='needs_review',
            rationale=' '.join(reasons),
            evidence_ids=tuple([alert['id']] + [event['id'] for event in supporting[:5]]),
            limitations=(
                'A signature match does not establish malicious intent.',
                'Related records show activity, not whether the activity was authorized.',
            ),
        )
