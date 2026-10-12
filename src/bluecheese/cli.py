import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from bluecheese.adapters.sqlite_store import EvidenceStore
from bluecheese.application.import_pcap import import_eve, import_pcap
from bluecheese.application.investigate_alert import case_report, triage_alert


def main():
    parser = argparse.ArgumentParser(prog='bluecheese', description='Run without arguments to open the operational GUI.')
    parser.add_argument('--data-dir', help='State directory (GUI: bluecheese-operations; legacy CLI: bluecheese-data)')
    commands = parser.add_subparsers(dest='command')
    commands.add_parser('import-eve').add_argument('path')
    pcap = commands.add_parser('import-pcap')
    pcap.add_argument('path')
    pcap.add_argument('--suricata', default='suricata')
    pcap.add_argument('--config')
    pcap.add_argument('--rules')
    alerts = commands.add_parser('alerts')
    alerts.add_argument('--import-id')
    alerts.add_argument('--limit', type=int, default=100)
    for name in ('triage', 'evidence', 'report'):
        commands.add_parser(name).add_argument('event_id')
    web = commands.add_parser('serve', help='Start the local analyst interface')
    web.add_argument('--port', type=int, default=8765)
    gui = commands.add_parser('gui', help='Open the real-telemetry analyst console')
    gui.add_argument('--port', type=int, help='Explicit port; otherwise start at 8501 and try the next free port')
    doctor_parser = commands.add_parser('doctor', help='Offline configuration/schema checks (stop GUI first)')
    doctor_parser.add_argument('--eve')
    retention = commands.add_parser('retention', help='Preview bounded unpinned evidence deletion (stop GUI first)')
    retention.add_argument('--before-sequence', type=int, required=True)
    retention.add_argument('--apply', action='store_true')
    bench = commands.add_parser('benchmark', help='Isolated synthetic ingestion backlog measurement')
    bench.add_argument('--records', type=int, default=1000)
    args = parser.parse_args()
    if args.command is None:
        args.command = 'gui'
        args.port = None
    directory = Path(args.data_dir or ('./bluecheese-operations' if args.command in ('gui', 'doctor', 'retention') else './bluecheese-data'))
    try:
        if args.command == 'benchmark':
            from bluecheese.application.benchmark import benchmark

            output = benchmark(args.records)
        elif args.command == 'doctor':
            from bluecheese.application.doctor import doctor

            output = doctor(directory, args.eve)
            print(json.dumps(output, indent=2))
            if not output['ok']:
                parser.exit(1)
            return
        elif args.command == 'retention':
            from bluecheese.adapters.duckdb_store import (
                EvidenceStore as OperationalStore,
            )

            if not (directory / 'evidence.duckdb').is_file():
                raise ValueError('No operational evidence database in data directory')
            store = OperationalStore(directory / 'evidence.duckdb')
            try:
                output = store.retention(args.before_sequence, apply=args.apply)
            finally:
                store.close()
        elif args.command == 'gui':
            result = subprocess.run(
                [sys.executable, '-m', 'streamlit', 'run',
                 str(Path(__file__).parent / 'interfaces' / 'console.py'),
                 '--server.address=127.0.0.1',
                 *([f'--server.port={args.port}'] if args.port is not None else []),
                 '--server.headless=true',
                 '--browser.gatherUsageStats=false',
                 '--client.toolbarMode=minimal',
                 '--theme.base=dark',
                 '--theme.primaryColor=#38bdb4',
                 '--theme.backgroundColor=#0b1220',
                 '--theme.secondaryBackgroundColor=#132035',
                 '--theme.textColor=#e5edf6',
                 '--theme.font=sans-serif'],
                env={**os.environ, 'BLUECHEESE_STATE': str(directory.resolve())},
                check=False,
            )
            if result.returncode:
                parser.exit(result.returncode)
            return
        elif args.command == 'import-eve':
            output = import_eve(args.path, directory)
        elif args.command == 'import-pcap':
            output = import_pcap(args.path, directory, args.suricata, args.config,
                                 args.rules)
        elif args.command == 'triage':
            output = triage_alert(directory, args.event_id)
        elif args.command == 'report':
            output = case_report(directory, args.event_id)
        elif args.command == 'serve':
            from bluecheese.interfaces.web import serve

            serve(directory, port=args.port)
            return
        else:
            with EvidenceStore(directory / 'bluecheese.sqlite3') as store:
                if args.command == 'alerts':
                    output = store.list_alerts(args.import_id, args.limit)
                else:
                    output = store.resolve(args.event_id)
        print(json.dumps(output, indent=2))
    except KeyboardInterrupt:
        parser.exit(130, '\nBlue Cheese stopped.\n')
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        parser.exit(1, f'bluecheese: {exc}\n')


if __name__ == '__main__':
    main()
