"""Strict conversion of the subset of sing-box rules QuanX can express."""

from dataclasses import dataclass
import ipaddress
import re


class ConversionError(ValueError):
    """The input cannot be converted without changing its meaning."""


@dataclass
class Conversion:
    lines: list[str]
    unsupported: list[dict]
    source_entries: int


def _values(value: object) -> list[str]:
    values = [value] if isinstance(value, str) else value
    if not isinstance(values, list) or any(not isinstance(v, str) for v in values):
        raise ConversionError("match values must be strings or arrays of strings")
    for item in values:
        if not item or item != item.strip() or "," in item or any(ord(c) < 32 or ord(c) == 127 for c in item):
            raise ConversionError(f"unsafe or empty match value: {item!r}")
    return values


def _domain(value: str) -> str:
    try:
        result = value.encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise ConversionError(f"invalid domain: {value!r}") from exc
    if not re.fullmatch(r"[a-z0-9_-]+(?:\.[a-z0-9_-]+)*\.?", result) or len(result) > 254:
        raise ConversionError(f"invalid domain: {value!r}")
    return result


def convert_document(document: dict) -> Conversion:
    """Return deterministic filters and explicit omissions; reject unknown constraints.

    All currently supported fields belong to the same OR match group in a
    sing-box default rule. Additional constraints must never be flattened.
    """
    if (not isinstance(document, dict) or set(document) != {"version", "rules"}
            or type(document["version"]) is not int or document["version"] != 2
            or not isinstance(document["rules"], list)):
        raise ConversionError("expected a version 2 rule-set with a rules array")
    lines: set[str] = set()
    unsupported: list[dict] = []
    count = 0
    allowed = {"domain", "domain_suffix", "domain_keyword", "domain_regex", "ip_cidr"}
    for rule in document["rules"]:
        if not isinstance(rule, dict) or set(rule) - allowed:
            raise ConversionError(f"unsupported rule structure or constraints: {rule!r}")
        for field, raw in rule.items():
            for value in _values(raw):
                count += 1
                if field == "domain_regex":
                    unsupported.append({"field": field, "value": value,
                                        "reason": "QuanX has no equivalent domain-regex routing filter"})
                    continue
                if field == "ip_cidr":
                    try:
                        network = ipaddress.ip_network(value, strict=False)
                    except ValueError as exc:
                        raise ConversionError(f"invalid CIDR: {value!r}") from exc
                    kind = "ip-cidr" if network.version == 4 else "ip6-cidr"
                    match = str(network)
                elif field == "domain_keyword":
                    kind, match = "host-keyword", value
                elif field == "domain":
                    kind, match = "host", _domain(value)
                elif value.startswith("."):
                    kind, match = "host-wildcard", "*." + _domain(value[1:])
                else:
                    kind, match = "host-suffix", _domain(value)
                lines.add(f"{kind},{match},proxy")
    return Conversion(sorted(lines), sorted(unsupported, key=lambda x: (x["field"], x["value"])), count)
