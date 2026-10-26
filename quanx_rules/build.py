"""Build and validate complete, deterministic subscription trees."""

from collections import Counter, defaultdict
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tarfile
import tempfile
from urllib.parse import quote

from .convert import ConversionError, convert_document
from .upstream import SHA_PATTERN

FAMILIES = {"asn", "geo/geosite", "geo/geoip", "geo-lite/geosite", "geo-lite/geoip"}
PAGE_SIZE = 1000
STATUSES = ("supported", "partial", "unsupported-only", "empty")


def _json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def check_removal(previous: dict, current: dict, allow_large_removal=False):
    if not allow_large_removal and current["categories"] < previous["categories"] * 0.8:
        raise ConversionError("category count dropped by more than 20%; inspect upstream, then explicitly allow large removal")


def _category(member: tarfile.TarInfo, root: str) -> str | None:
    path = PurePosixPath(member.name)
    if path.is_absolute() or ".." in path.parts or not path.parts or path.parts[0] != root:
        raise ConversionError(f"unexpected archive path: {member.name!r}")
    if not member.name.endswith(".json"):
        return None
    if not member.isfile():
        raise ConversionError(f"JSON member is not a regular file: {member.name}")
    relative = "/".join(path.parts[1:])
    if not re.fullmatch(r"[A-Za-z0-9_.@!+/-]+\.json", relative) or len(path.parts) < 3:
        raise ConversionError(f"invalid category path: {relative}")
    if member.size > 64 * 1024 * 1024:
        raise ConversionError(f"category exceeds 64 MiB: {relative}")
    return relative


def _scan(archive: Path, target: Path, sha: str):
    records = defaultdict(list)
    seen = set()
    source_bytes = 0
    # Use the seekable reader so the exact TAR end-marker position can be
    # checked; tarfile alone tolerates a missing or incomplete terminator.
    with gzip.open(archive, "rb") as compressed:
        with tarfile.open(fileobj=compressed, mode="r:") as source:
            for member in source:
                name = _category(member, f"meta-rules-dat-{sha}")
                if name is None:
                    continue
                if name in seen:
                    raise ConversionError(f"duplicate category: {name}")
                seen.add(name)
                source_bytes += member.size
                if len(seen) > 250_000 or source_bytes > 1024 * 1024 * 1024:
                    raise ConversionError("upstream category count or size exceeds the documented resource limit")
                try:
                    raw = source.extractfile(member).read()
                    conversion = convert_document(json.loads(raw))
                except (ValueError, UnicodeError) as exc:
                    raise ConversionError(f"{name}: {exc}") from exc
                count, skipped = len(conversion.lines), len(conversion.unsupported)
                status = ("partial" if skipped else "supported") if count else ("unsupported-only" if skipped else "empty")
                output_path = "rules/" + name[:-5] + ".list" if count else None
                record = {"source": name, "source_sha256": hashlib.sha256(raw).hexdigest(),
                          "path": output_path, "status": status, "rules": count,
                          "source_entries": conversion.source_entries, "unsupported": conversion.unsupported}
                if output_path:
                    data = (f"# Source: MetaCubeX/meta-rules-dat/sing/{name}\n"
                            f"# Unsupported entries: {skipped}; see reports/\n" + "\n".join(conversion.lines) + "\n").encode()
                    path = target / output_path
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(data)
                    record["sha256"] = hashlib.sha256(data).hexdigest()
                records[name.rsplit("/", 1)[0]].append(record)
                if len(seen) % 20_000 == 0:
                    print(f"Converted {len(seen):,} categories", flush=True)
            compressed.seek(source.offset)
            if compressed.read(1024) != bytes(1024):
                raise ConversionError("missing TAR completion marker; archive may be truncated")
        # Drain to EOF to verify the gzip CRC and reject hidden data after TAR.
        while trailing := compressed.read(1024 * 1024):
            if trailing.strip(b"\0"):
                raise ConversionError("unexpected content after TAR completion marker")
    if not FAMILIES <= set(records):
        raise ConversionError(f"incomplete snapshot; missing families: {sorted(FAMILIES - set(records))}")
    return records


def _catalog(target, records, sha, repository):
    statuses = Counter({status: 0 for status in STATUSES})
    manifests = []
    groups = {}
    rules = skipped = entries = 0
    rows = ["# QuanX 全量分类目录", "", f"上游快照：`{sha}`", "",
            "所有文件默认策略为 `proxy`；订阅时用 `force-policy` 指定自己的策略组。",
            "partial 表示含无法转换的域名正则；unsupported-only 和 empty 不提供空订阅。", "",
            "| 分类组 | 分类数 | 目录 |", "| --- | ---: | --- |"]
    for group, items in sorted(records.items()):
        items.sort(key=lambda x: x["source"])
        groups[group] = len(items)
        links = []
        for offset in range(0, len(items), PAGE_SIZE):
            number = offset // PAGE_SIZE + 1
            report_path = f"reports/{group}/{number:04}.json"
            index_path = f"indexes/{group}/{number:04}.md"
            page = items[offset:offset + PAGE_SIZE]
            _json(target / report_path, page)
            manifests.append(report_path)
            text = [f"# {group} / {number}", "", "| 分类 | 规则数 | 状态 | 订阅 |", "| --- | ---: | --- | --- |"]
            for item in page:
                statuses[item["status"]] += 1
                rules += item["rules"]
                skipped += len(item["unsupported"])
                entries += item["source_entries"]
                url = f"https://raw.githubusercontent.com/{repository}/quanx/{quote(item['path'])}" if item["path"] else None
                label = item["source"].rsplit("/", 1)[-1][:-5]
                link = f"[订阅]({url})" if url else "无可转换规则"
                text.append(f"| {label} | {item['rules']} | {item['status']} | {link} |")
            path = target / index_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("\n".join(text) + "\n", encoding="utf-8")
            links.append(f"[{number}]({quote(index_path)})")
        rows.append(f"| {group} | {len(items):,} | {' · '.join(links)} |")
    summary = {"schema_version": 1, "upstream_repository": "MetaCubeX/meta-rules-dat", "source_sha": sha,
               "repository": repository, "categories": sum(groups.values()), "groups": groups,
               "statuses": dict(statuses), "output_files": statuses["supported"] + statuses["partial"],
               "output_rules": rules, "unsupported_entries": skipped, "source_entries": entries,
               "deduplicated_entries": entries - skipped - rules, "manifests": manifests}
    _json(target / "reports/summary.json", summary)
    (target / "index.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    (target / "README.md").write_text(
        f"# QuanX 自动更新规则\n\n[全部分类](index.md) · [同步报告](reports/summary.json) · "
        f"[使用说明](https://github.com/{repository})\n\n"
        f"分类：{summary['categories']:,}；订阅文件：{summary['output_files']:,}；"
        f"规则：{rules:,}；无法转换的域名正则：{skipped:,}。\n\n"
        "每天北京时间 08:30 自动更新，GitHub 调度可能延迟。所有文件默认策略为 `proxy`。\n\n"
        "```ini\n[filter_remote]\n"
        f"https://raw.githubusercontent.com/{repository}/quanx/rules/geo/geosite/google.list, tag=Google, force-policy=proxy, enabled=true\n"
        "```\n\n使用时将 `proxy` 换成自己已有的策略组名称。partial 分类仅含可转换部分，详见 reports 对应分页中的 unsupported 字段。\n\n"
        "来源：[MetaCubeX/meta-rules-dat](https://github.com/MetaCubeX/meta-rules-dat)。"
        "来源声明与许可证见 THIRD_PARTY.md 和 LICENSE。\n", encoding="utf-8")
    project = Path(__file__).resolve().parent.parent
    for filename in ("LICENSE", "THIRD_PARTY.md"):
        if (project / filename).is_file():
            shutil.copyfile(project / filename, target / filename)
    return summary


def validate_output(output: Path) -> dict:
    output = Path(output)
    summary = json.loads((output / "reports/summary.json").read_text(encoding="utf-8"))
    if summary["output_files"] <= 0 or summary["output_rules"] <= 0:
        raise ConversionError("refusing to publish a globally empty ruleset")
    seen = set()
    paths = set()
    statuses = Counter({status: 0 for status in STATUSES})
    groups = Counter()
    rules = skipped = entries = 0
    for page in summary["manifests"]:
        for item in json.loads((output / page).read_text(encoding="utf-8")):
            name = item["source"]
            if name in seen or item["status"] not in STATUSES:
                raise ConversionError("duplicate category or invalid status in manifest")
            seen.add(name)
            groups[name.rsplit("/", 1)[0]] += 1
            statuses[item["status"]] += 1
            rules += item["rules"]
            skipped += len(item["unsupported"])
            entries += item["source_entries"]
            if not item["path"]:
                if item["rules"] or item["status"] not in {"empty", "unsupported-only"}:
                    raise ConversionError("missing rules for a supported category")
                continue
            paths.add(item["path"])
            data = (output / item["path"]).read_bytes()
            lines = [line for line in data.decode("utf-8").splitlines() if not line.startswith("#")]
            if (hashlib.sha256(data).hexdigest() != item["sha256"] or not lines or len(lines) != item["rules"]):
                raise ConversionError(f"rule file failed integrity validation: {item['path']}")
            for line in lines:
                fields = line.split(",")
                if len(fields) != 3 or fields[2] != "proxy" or fields[0] not in {
                    "host", "host-suffix", "host-keyword", "host-wildcard", "ip-cidr", "ip6-cidr"
                }:
                    raise ConversionError(f"invalid QuanX rule: {line!r}")
    actual_paths = {str(p.relative_to(output)) for p in (output / "rules").rglob("*.list")}
    if (len(seen) != summary["categories"] or len(paths) != summary["output_files"] or actual_paths != paths
            or dict(statuses) != summary["statuses"] or dict(groups) != summary["groups"]
            or rules != summary["output_rules"] or skipped != summary["unsupported_entries"]
            or entries != summary["source_entries"] or entries - skipped - rules != summary["deduplicated_entries"]):
        raise ConversionError("incomplete or inconsistent output catalog")
    return summary


def build_archive(archive: Path, output: Path, sha: str, repository: str, *, allow_large_removal=False) -> dict:
    if not SHA_PATTERN.fullmatch(sha) or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ConversionError("invalid snapshot SHA or repository name")
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() and (output.is_symlink() or not (output / "reports/summary.json").is_file()):
        raise ConversionError("refusing to replace a directory not created by quanx-rules")
    previous = json.loads((output / "reports/summary.json").read_text()) if output.exists() else None
    stage = Path(tempfile.mkdtemp(prefix=".quanx-stage-", dir=output.parent))
    try:
        try:
            records = _scan(Path(archive), stage, sha)
            summary = _catalog(stage, records, sha, repository)
            validate_output(stage)
        except (OSError, EOFError, tarfile.TarError, ValueError) as exc:
            raise ConversionError(f"snapshot build failed: {exc}") from exc
        if previous:
            check_removal(previous, summary, allow_large_removal)
        with tempfile.TemporaryDirectory(prefix=".quanx-old-", dir=output.parent) as backup:
            old = Path(backup) / "previous"
            if output.exists():
                output.rename(old)
            try:
                os.replace(stage, output)
            except OSError:
                if old.exists():
                    old.rename(output)
                raise
        return summary
    finally:
        if stage.exists():
            shutil.rmtree(stage)
