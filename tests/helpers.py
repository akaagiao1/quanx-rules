import io
import json
import tarfile
from pathlib import Path

SHA = "a" * 40
BASE = {
    "asn/AS1.json": {"ip_cidr": "192.0.2.0/24"},
    "geo/geoip/cn.json": {"ip_cidr": "198.51.100.0/24"},
    "geo/geosite/google.json": {"domain_suffix": "google.com"},
    "geo-lite/geoip/cn.json": {"ip_cidr": "203.0.113.0/24"},
    "geo-lite/geosite/google.json": {"domain": "google.test"},
}


def archive(path: Path, extra=None, remove=(), members=None):
    files = dict(BASE)
    files.update(extra or {})
    for name in remove:
        files.pop(name)
    items = members if members is not None else list(files.items())
    with tarfile.open(path, "w:gz") as target:
        for name, rule in items:
            data = rule if isinstance(rule, bytes) else json.dumps({"version": 2, "rules": [rule]}).encode()
            info = tarfile.TarInfo(f"meta-rules-dat-{SHA}/{name}")
            info.size = len(data)
            target.addfile(info, io.BytesIO(data))
    return path


def digest_tree(path):
    import hashlib
    return {str(f.relative_to(path)): hashlib.sha256(f.read_bytes()).hexdigest()
            for f in path.rglob("*") if f.is_file()}
