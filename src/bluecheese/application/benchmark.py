"""Isolated synthetic backlog benchmark; not a detection or sustained-rate claim."""

import json
import math
import resource
import sys
import tempfile
import time
from pathlib import Path

from bluecheese.application.demo_runtime import DemoRuntime


def percentile(values, fraction):
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * fraction) - 1)]


def benchmark(records=1000):
    if not 1 <= records <= 100000:
        raise ValueError('Benchmark record count must be 1..100000')
    with tempfile.TemporaryDirectory(prefix='bluecheese-benchmark-') as temporary:
        root = Path(temporary)
        path = root / 'eve.json'
        with path.open('wb') as stream:
            for index in range(records):
                event = {
                    'timestamp': '2026-01-01T00:00:00+00:00',
                    'event_type': 'alert' if index % 10 == 0 else 'flow',
                    'src_ip': '192.0.2.10', 'dest_ip': '198.51.100.20',
                    'src_port': 41000, 'dest_port': 443, 'proto': 'TCP',
                    'flow_id': index // 10,
                }
                if event['event_type'] == 'alert':
                    event['alert'] = {'signature': 'Synthetic benchmark alert', 'severity': 2}
                else:
                    event['flow'] = {'state': 'closed', 'bytes_toserver': 100, 'bytes_toclient': 100}
                stream.write(json.dumps(event).encode() + b'\n')
        runtime = DemoRuntime(root / 'state', load_fixtures=False)
        durations = []
        try:
            started = time.perf_counter()
            tick = time.perf_counter()
            if not runtime.start(path=path, replay=False, interval=3600):
                raise RuntimeError(runtime.status()['status'])
            runtime.stop()
            durations.append(time.perf_counter() - tick)
            while runtime.follower.committed < path.stat().st_size:
                tick = time.perf_counter()
                result = runtime.poll_once()
                durations.append(time.perf_counter() - tick)
                if result['bytes_read'] == 0:
                    raise RuntimeError('Benchmark ingestion stalled')
            elapsed = time.perf_counter() - started
            counts = runtime.command('counts', 'live', 'external')
            if counts['accepted'] != records or counts['invalid']:
                raise RuntimeError('Benchmark record accounting failed')
            return {
                'synthetic': True, 'workload': 'finite backlog, 10% alerts, 90% flows',
                'records': records, 'input_bytes': path.stat().st_size,
                'elapsed_seconds': round(elapsed, 6),
                'backlog_records_per_second': round(records / elapsed, 2),
                'polls': len(durations),
                'poll_duration_seconds': {f'p{int(f * 100)}': round(percentile(durations, f), 6) for f in (0.5, 0.95, 0.99)},
                'process_lifetime_peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == 'darwin' else 1024),
                'counts': counts, 'provider_calls': 0,
                'limitations': ['Not sustained-rate testing or sensor-to-report latency.',
                                'Synthetic data does not validate detection quality.',
                                'Peak RSS includes interpreter/dependency initialization.'],
            }
        finally:
            runtime.close()
