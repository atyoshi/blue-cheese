import argparse
import json
from pathlib import Path

from bluecheese.adapters.sqlite_store import EvidenceStore
from bluecheese.application.import_pcap import import_eve, import_pcap
from bluecheese.application.investigate_alert import case_report, triage_alert


def main():
    parser = argparse.ArgumentParser(prog='bluecheese')
    parser.add_argument('--data-dir', default='./bluecheese-data')
    commands = parser.add_subparsers(dest='command', required=True)
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
    args = parser.parse_args()
    directory = Path(args.data_dir)
    try:
        if args.command == 'import-eve':
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
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        parser.exit(1, f'bluecheese: {exc}\n')


if __name__ == '__main__':
    main()
