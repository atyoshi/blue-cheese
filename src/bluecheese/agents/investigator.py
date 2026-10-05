"""Deterministic evidence policy behind a replaceable provider interface."""
import time
from typing import Protocol

PROVIDER_LABEL = 'Deterministic demo provider (offline rules; no model)'


class BudgetExceeded(RuntimeError):
    pass


class EvidenceTools:
    """Fixed scope/snapshot, bounded typed queries, auditable retrieval ledger."""
    def __init__(self, store, scenario, variant, snapshot, max_calls=6,
                 max_seconds=5.0, clock=time.monotonic):
        self.store = store
        self.scope = (scenario, variant, snapshot)
        self.max_calls = max(0, int(max_calls))
        self.max_seconds = max(0.0, float(max_seconds))
        self.clock = clock
        self.started = clock()
        self.activity = []
        self.retrieved = {}

    def call(self, tool, **args):
        if tool not in ('get_event', 'list_alerts', 'find_events_by_ip', 'search_events'):
            raise ValueError('Unknown typed tool')
        if len(self.activity) >= self.max_calls or self.clock() - self.started >= self.max_seconds:
            raise BudgetExceeded('Tool-call or elapsed-time limit reached')
        result = getattr(self.store, tool)(*self.scope, **args)
        rows = ([result] if result else []) if tool == 'get_event' else result
        self.retrieved.update({r['id']: r for r in rows})
        self.activity.append(dict(tool=tool, arguments=args, returned_ids=[r['id'] for r in rows]))
        if self.clock() - self.started >= self.max_seconds:
            raise BudgetExceeded('Elapsed-time limit reached during query')
        return result

    def validate(self, ids):
        for event_id in ids:
            if event_id not in self.retrieved:
                raise ValueError(f'Invented, cross-case or unseen citation: {event_id}')
            if self.store.get_event(*self.scope, event_id) is None:
                raise ValueError(f'Citation outside fixed snapshot: {event_id}')


class InvestigationProvider(Protocol):
    label: str

    def investigate(self, tools: EvidenceTools, falsification: bool) -> dict: ...


def active_flow(row):
    n = row['normalized']
    amount = n.get('bytes_toserver')
    return n['event_type'] == 'flow' and n.get('flow_state') == 'established' and isinstance(amount, (int, float)) and amount >= 10000


def failed_flow(row):
    n = row['normalized']
    return n['event_type'] == 'flow' and n.get('flow_state') == 'closed' and n.get('bytes_toserver') == 0 and n.get('bytes_toclient') == 0


class Falsifier:
    def check(self, tools, alert):
        # This independent query is executable and can reveal a failed connection
        # that the Investigator's initial alert retrieval never observed.
        rows = tools.call('find_events_by_ip', ip=alert['normalized']['src_ip'], limit=100)
        relevant = [r for r in rows if r['normalized'].get('flow_id') == alert['normalized'].get('flow_id') and r['normalized']['event_type'] == 'flow']
        counters = [r['id'] for r in relevant if failed_flow(r)]
        return dict(
            status='evidence contradicted' if counters else ('not observed' if relevant else 'not available'),
            checked='Alternative explanation: the alerted flow closed with zero bytes in both directions.',
            query=tools.activity[-1], returned_ids=[r['id'] for r in relevant],
            counterevidence_ids=counters,
            limitation='Flow counters cannot establish intent; missing flow evidence cannot clear an alert.')


class DemoInvestigator:
    label = PROVIDER_LABEL

    def investigate(self, tools, falsification=True):
        alerts = tools.call('list_alerts', limit=20)
        result = dict(verdict='UNCERTAIN', hypothesis='No alert available for investigation.',
                      supporting_ids=[], contradicting_ids=[], claims=[],
                      disconfirmation_test='Find the alerted flow closing with zero bytes in both directions.',
                      unresolved=['Intent and endpoint activity are not available in network logs.'],
                      falsifier=dict(status='disabled', checked='Falsification disabled', returned_ids=[]))
        if not alerts:
            result['unresolved'].append('No alert observed in this snapshot.')
            return result
        alert = alerts[0]
        result['hypothesis'] = 'The alerted connection may be command and control traffic.'
        result['supporting_ids'] = [alert['id']]
        flows = tools.call('search_events', event_type='flow', limit=100)
        relevant = [r for r in flows if r['normalized'].get('flow_id') == alert['normalized'].get('flow_id') and r['normalized']['src_ip'] == alert['normalized']['src_ip'] and r['normalized']['dest_ip'] == alert['normalized']['dest_ip']]
        active = [r['id'] for r in relevant if active_flow(r)]
        result['supporting_ids'] += active
        if active:
            result['verdict'] = 'SUSPICIOUS'
        else:
            result['unresolved'].append('No established high-volume alerted flow observed.')
        if falsification:
            check = Falsifier().check(tools, alert)
            result['falsifier'] = check
            result['contradicting_ids'] = check['counterevidence_ids']
            if check['counterevidence_ids']:
                result['verdict'] = 'UNCERTAIN' if active else 'BENIGN_CONFOUNDER'
                if active:
                    result['unresolved'].append('Conflicting flow counters require independent validation.')
            if check['status'] == 'not available':
                result['unresolved'].append('Flow evidence needed to test the alternative explanation is unavailable.')
        result['claims'] = [dict(text='A sensor alert flags this connection; this is not proof of compromise.', citations=[alert['id']])]
        if active:
            result['claims'].append(dict(text='Related established flows report at least 10,000 outbound bytes.', citations=active))
        if result['contradicting_ids']:
            result['claims'].append(dict(text='Related flow evidence reports a closed connection with zero bytes.', citations=result['contradicting_ids']))
        return result


def validate_report(report, tools):
    ids = report['supporting_ids'] + report['contradicting_ids']
    for claim in report['claims']:
        ids += claim['citations']
    ids += report['falsifier'].get('returned_ids', [])
    ids += report['falsifier'].get('counterevidence_ids', [])
    tools.validate(ids)


def investigate(store, scenario, variant, *, falsification=True, max_calls=6,
                max_seconds=5.0, provider=None, clock=time.monotonic):
    provider = provider or DemoInvestigator()
    snapshot = store.snapshot()
    tools = EvidenceTools(store, scenario, variant, snapshot, max_calls, max_seconds, clock)
    warnings = ['Synthetic data; rule-based verdicts are not a measurement of LLM performance.',
                'Log text and enrichment are untrusted. Claims use normalized telemetry fields.',
                'Evidence retrieval is capped at 100 rows per query; results may be incomplete.']
    try:
        report = provider.investigate(tools, falsification)
        if clock() - tools.started >= tools.max_seconds:
            raise BudgetExceeded('Elapsed-time limit reached')
    except BudgetExceeded as error:
        warnings.append(str(error))
        report = dict(verdict='UNCERTAIN', hypothesis='Investigation did not complete within its budget.',
                      supporting_ids=[], contradicting_ids=[], claims=[],
                      disconfirmation_test='Retrieve related flow counterevidence within budget.',
                      unresolved=['Evidence collection or falsification remains incomplete.'],
                      falsifier=dict(status='not available', checked='Budget exhausted', returned_ids=[]))
    validate_report(report, tools)
    report.update(scenario=scenario, variant=variant, snapshot=snapshot,
                  provider=provider.label, warnings=warnings, tool_activity=tools.activity,
                  budget=dict(calls=len(tools.activity), max_calls=tools.max_calls,
                              elapsed_seconds=round(clock() - tools.started, 6),
                              max_seconds=tools.max_seconds), falsification_enabled=falsification)
    return report
