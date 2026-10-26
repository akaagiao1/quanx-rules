"""CLI: python -m quanx_rules --repository owner/repo --output dist."""

import argparse
import json
from pathlib import Path
import sys

from .build import build_archive
from .upstream import download_snapshot, resolve_snapshot


def main():
    parser = argparse.ArgumentParser(description="Synchronize all MetaCubeX categories to QuanX")
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
        summary = build_archive(source, args.output, sha, args.repository,
                                allow_large_removal=args.allow_large_removal)
        print(json.dumps({key: value for key, value in summary.items() if key != "manifests"}, indent=2))
    except (OSError, ValueError) as exc:
        print(f"Synchronization failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
