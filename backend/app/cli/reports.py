"""CLI for downloading and importing official AT XLSX reports."""

from __future__ import annotations

import argparse
import json

from sqlalchemy.orm import Session

from ..core.config import get_settings
from ..db.session import get_engine
from ..reports.loader import load_reports, report_status
from ..reports.registry import REPORTS, REPORTS_BY_KEY, ReportSpec


def _specs(names: list[str] | None) -> list[ReportSpec]:
    if not names:
        return list(REPORTS)
    unknown = [name for name in names if name not in REPORTS_BY_KEY]
    if unknown:
        raise SystemExit(f"Unknown report key(s): {', '.join(unknown)}")
    return [REPORTS_BY_KEY[name] for name in names]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    load_parser = subparsers.add_parser("load", help="Download and import reports")
    load_parser.add_argument("--only", nargs="*", help="Import only these source keys")
    load_parser.add_argument(
        "--no-download", action="store_true", help="Use files already in data/reports"
    )
    load_parser.add_argument(
        "--force", action="store_true", help="Re-import reports with unchanged checksums"
    )

    subparsers.add_parser("status", help="Show imported official reports")

    args = parser.parse_args(argv)
    settings = get_settings()
    engine = get_engine()
    with Session(engine) as session:
        if args.command == "status":
            print(json.dumps(report_status(session), indent=2))
            return

        specs = _specs(args.only)
        results = load_reports(
            session,
            settings,
            specs,
            download=not args.no_download,
            force=args.force,
        )
        payload = [result.__dict__ for result in results]
        print(json.dumps(payload, indent=2))
        if any(
            result["status"] in {"missing", "download_failed", "parse_failed"}
            for result in payload
        ):
            raise SystemExit(1)


if __name__ == "__main__":
    main()
