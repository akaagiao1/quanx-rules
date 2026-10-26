"""Retrieve one immutable upstream snapshot with bounded retries."""

import http.client
import json
from pathlib import Path
import re
import tempfile
import time
import urllib.error
import urllib.request

API = "https://api.github.com/repos/MetaCubeX/meta-rules-dat/commits/sing"
ARCHIVE = "https://codeload.github.com/MetaCubeX/meta-rules-dat/tar.gz/{}"
SHA_PATTERN = re.compile(r"[0-9a-f]{40}")


def _retry(operation, delay):
    for attempt in range(3):
        try:
            return operation()
        except (OSError, http.client.HTTPException, ValueError):
            if attempt == 2:
                raise
            time.sleep(delay * (2 ** attempt))


def _request(url):
    return urllib.request.urlopen(urllib.request.Request(
        url, headers={"User-Agent": "quanx-rules", "Accept": "application/vnd.github+json"}), timeout=60)


def resolve_snapshot(*, api_url=API, retry_delay=2) -> str:
    def fetch():
        with _request(api_url) as response:
            value = json.load(response)
        sha = value.get("sha", "")
        if not isinstance(sha, str) or not SHA_PATTERN.fullmatch(sha):
            raise ValueError("upstream returned an invalid commit SHA")
        return sha
    return _retry(fetch, retry_delay)


def download_snapshot(sha: str, destination: Path, *, archive_url=None, retry_delay=2) -> None:
    if not SHA_PATTERN.fullmatch(sha):
        raise ValueError("expected a full commit SHA")
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    def fetch():
        with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as target:
            temporary = Path(target.name)
            try:
                with _request(archive_url or ARCHIVE.format(sha)) as response:
                    expected = response.headers.get("Content-Length")
                    size = 0
                    while block := response.read(1024 * 1024):
                        size += len(block)
                        if size > 1024 * 1024 * 1024:
                            raise ValueError("upstream archive exceeds 1 GiB")
                        target.write(block)
                    if size == 0 or (expected is not None and size != int(expected)):
                        raise ValueError("incomplete upstream archive")
                target.close()
                temporary.replace(destination)
            finally:
                temporary.unlink(missing_ok=True)
    _retry(fetch, retry_delay)
