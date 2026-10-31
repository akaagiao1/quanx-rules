"""Publish validated output with normal commits to a dedicated branch."""

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from .build import check_removal, validate_output
from .convert import ConversionError


def _git(*args, cwd, allowed=(0,)):
    result = subprocess.run(["git", *map(str, args)], cwd=cwd, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"}, timeout=300)
    if result.returncode not in allowed:
        # Remote errors can contain credential-bearing URLs; keep them out of logs.
        raise RuntimeError(f"git {args[0]} failed with exit code {result.returncode}; check connectivity, credentials and branch permissions")
    return result


def publish(output: Path, remote: str, branch=None, *, allow_large_removal=False) -> bool:
    output = Path(output).resolve()
    summary = validate_output(output)
    output_format = summary.get("format", "quanx")
    branch = branch or output_format
    if branch != output_format:
        raise ConversionError(f"{output_format} output must be published to the {output_format} branch")
    with tempfile.TemporaryDirectory(prefix="quanx-publish-") as temp:
        checkout = Path(temp)
        _git("check-ref-format", "--branch", branch, cwd=checkout)
        lookup = _git("ls-remote", "--exit-code", "--heads", remote, f"refs/heads/{branch}",
                      cwd=checkout, allowed=(0, 2))
        exists = lookup.returncode == 0
        _git("init", "-b", branch, cwd=checkout)
        _git("remote", "add", "origin", remote, cwd=checkout)
        if exists:
            _git("fetch", "--depth=1", "origin", f"refs/heads/{branch}", cwd=checkout)
            _git("reset", "--hard", "FETCH_HEAD", cwd=checkout)
            previous = json.loads((checkout / "reports/summary.json").read_text(encoding="utf-8"))
            check_removal(previous, summary, allow_large_removal)
        for item in checkout.iterdir():
            if item.name == ".git":
                continue
            if item.is_dir() and not item.is_symlink():
                shutil.rmtree(item)
            else:
                item.unlink()
        shutil.copytree(output, checkout, dirs_exist_ok=True)
        _git("add", "--all", cwd=checkout)
        if exists and _git("diff", "--cached", "--quiet", cwd=checkout, allowed=(0, 1)).returncode == 0:
            print("No output changes; no commit created.", flush=True)
            return False
        _git("-c", "user.name=github-actions[bot]", "-c",
             "user.email=41898282+github-actions[bot]@users.noreply.github.com",
             "commit", "-m", f"rules: synchronize upstream {summary['source_sha'][:12]}", cwd=checkout)
        _git("push", "origin", f"HEAD:refs/heads/{branch}", cwd=checkout)
        print(f"Published {summary['categories']:,} categories to {branch}.", flush=True)
        return True


def main():
    parser = argparse.ArgumentParser(description="Publish validated QuanX or Surge subscriptions")
    parser.add_argument("--output", type=Path, default=Path("dist"))
    parser.add_argument("--remote", required=True)
    parser.add_argument("--branch", help="defaults to the output format; must match it")
    parser.add_argument("--allow-large-removal", action="store_true")
    args = parser.parse_args()
    try:
        publish(args.output, args.remote, args.branch, allow_large_removal=args.allow_large_removal)
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"Publication failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
