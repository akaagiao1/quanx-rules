"""CLI: python -m quanx_rules --repository owner/repo --output dist."""

import argparse
import json
from pathlib import Path
import sys

from .build import build_archive
from .convert import FORMATS
from .upstream import download_snapshot, resolve_snapshot


def main():
    parser = argparse.ArgumentParser(description="Synchronize all MetaCubeX categories to QuanX and Surge")
    parser.add_argument("--format", choices=[*FORMATS, "all"], default="quanx", dest="output_format")
    parser.add_argument("--output", type=Path, default=Path("dist"))
    parser.add_argument("--repository", required=True, help="owner/repository for subscription URLs")
    parser.add_argument("--archive", type=Path, help="offline snapshot archive; requires --sha")
    parser.add_argument("--sha", help="full upstream commit SHA, otherwise resolve sing once")
    parser.add_argument("--cache", type=Path, default=Path(".cache"))
    parser.add_argument("--allow-large-removal", action="store_true")
    args = parser.parse_args()
    if args.archive and not args.sha:
        parser.error("--archive requires --sha")
    try:
        sha = args.sha or resolve_snapshot()
        source = args.archive or args.cache / f"{sha}.tar.gz"
        if not args.archive:
            print(f"Downloading upstream commit {sha}", flush=True)
            download_snapshot(sha, source)
        formats = list(FORMATS) if args.output_format == "all" else [args.output_format]
        for name in formats:
            output = args.output / name if args.output_format == "all" else args.output
            summary = build_archive(source, output, sha, args.repository,
                                    allow_large_removal=args.allow_large_removal, output_format=name)
            print(json.dumps({key: value for key, value in summary.items() if key != "manifests"}, indent=2))
    except (OSError, ValueError) as exc:
        print(f"Synchronization failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
