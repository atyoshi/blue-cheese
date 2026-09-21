import argparse
from dataclasses import asdict
import json

from bluecheese.adapters.suricata import read_suricata_alerts
from bluecheese.agents.mock_triage import MockTriageAgent


def main() -> None:
    parser = argparse.ArgumentParser(prog="bluecheese")
    parser.add_argument("eve_json", help="Path to Suricata eve.json")
    parser.add_argument(
        "--triage",
        action="store_true",
        help="Run the mock triage role",
    )
    args = parser.parse_args()

    triage_agent = MockTriageAgent()

    for alert in read_suricata_alerts(args.eve_json):
        output = {"alert": asdict(alert)}

        if args.triage:
            output["triage"] = asdict(triage_agent.analyze(alert))

        print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
