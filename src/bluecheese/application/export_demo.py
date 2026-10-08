"""Generate reproducible offline presentation exports, without starting a worker."""

import argparse
from pathlib import Path

from bluecheese.agents.reporting import json_report, markdown_report
from bluecheese.application.demo_runtime import SCENARIOS, DemoRuntime
from bluecheese.application.report_bundle import export_bundle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", default="bluecheese-data")
    parser.add_argument("--out", default="demo-exports")
    parser.add_argument(
        "--bundles",
        action="store_true",
        help="Also export immutable offline-verifiable bundles",
    )
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    runtime = DemoRuntime(args.state)
    try:
        for scenario, variants in SCENARIOS.items():
            for variant in variants:
                report = runtime.run(scenario, variant)
                base = out / f"{scenario}-{variant}"
                base.with_suffix(".json").write_text(
                    json_report(report) + "\n", encoding="utf-8"
                )
                base.with_suffix(".md").write_text(
                    markdown_report(report), encoding="utf-8"
                )
                if args.bundles:
                    export_bundle(runtime, report, out / f"{scenario}-{variant}.bundle")
                print(f"{base}: {report['verdict']}")
    finally:
        runtime.close()


if __name__ == "__main__":
    main()
