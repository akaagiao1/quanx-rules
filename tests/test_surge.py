import hashlib
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from quanx_rules.build import build_archive, validate_output
from quanx_rules.convert import FORMATS, ConversionError, convert_document
from quanx_rules.publish import publish
from tests.helpers import SHA, archive, digest_tree


class SurgeTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def build(self, output_format="surge", output=None):
        src = archive(self.root / "source.tgz", {
            "geo/geosite/partial@cn.json": {"domain": "ok.test", "domain_regex": "^a{1,3}$"},
            "geo/geosite/sub.json": {"domain_suffix": ".example.com"},
        })
        return build_archive(src, output or self.root / "surge", SHA, "test/rules", output_format=output_format)

    def test_native_surge_rule_names_have_no_policy_and_keep_subdomain_boundary(self):
        result = convert_document({"version": 2, "rules": [{
            "domain": "EXAMPLE.com", "domain_suffix": ["example.net", ".sub.example.net"],
            "domain_keyword": "ads-", "ip_cidr": ["192.0.2.9/24", "2001:0db8::1/32"],
        }]}, output_format="surge")
        self.assertEqual(result.lines, [
            "DOMAIN,example.com", "DOMAIN-KEYWORD,ads-", "DOMAIN-SUFFIX,example.net",
            "DOMAIN-WILDCARD,*.sub.example.net", "IP-CIDR,192.0.2.0/24", "IP-CIDR6,2001:db8::/32",
        ])
        self.assertEqual(result.source_entries, 6)

    def test_regex_report_identifies_surge_without_approximation(self):
        result = convert_document({"version": 2, "rules": [{"domain_regex": "^a{1,3}$"}]}, output_format="surge")
        self.assertEqual(result.lines, [])
        self.assertEqual(result.unsupported[0]["value"], "^a{1,3}$")
        self.assertIn("Surge", result.unsupported[0]["reason"])

    def test_surge_catalog_and_readme_use_surge_urls_and_ruleset_syntax(self):
        summary = self.build()
        output = self.root / "surge"
        self.assertEqual(summary["format"], "surge")
        self.assertEqual(validate_output(output), summary)
        index = (output / "indexes/geo/geosite/0001.md").read_text()
        self.assertIn("test/rules/surge/rules/geo/geosite/partial%40cn.list", index)
        self.assertNotIn("test/rules/quanx/", index)
        readme = (output / "README.md").read_text()
        self.assertIn("[Rule]", readme)
        self.assertIn("RULE-SET,https://raw.githubusercontent.com/test/rules/surge/", readme)
        self.assertNotIn("force-policy", readme)
        self.assertEqual((output / "rules/geo/geosite/sub.list").read_text().splitlines()[-1],
                         "DOMAIN-WILDCARD,*.example.com")

    def test_output_validator_rejects_quanx_rule_in_surge_manifest(self):
        self.build()
        output = self.root / "surge"
        rule = output / "rules/asn/AS1.list"
        rule.write_text("ip-cidr,192.0.2.0/24,proxy\n")
        page = output / "reports/asn/0001.json"
        records = json.loads(page.read_text())
        records[0]["sha256"] = hashlib.sha256(rule.read_bytes()).hexdigest()
        page.write_text(json.dumps(records))
        with self.assertRaises(ConversionError):
            validate_output(output)

    def test_surge_publication_selects_surge_branch_and_rejects_quanx_branch(self):
        self.build()
        remote = self.root / "remote.git"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        with self.assertRaises(ConversionError):
            publish(self.root / "surge", str(remote), branch="quanx")
        self.assertTrue(publish(self.root / "surge", str(remote)))
        data = subprocess.check_output(["git", "--git-dir", str(remote), "show", "surge:rules/asn/AS1.list"], text=True)
        self.assertIn("IP-CIDR,192.0.2.0/24", data)
        self.assertFalse(publish(self.root / "surge", str(remote)))

    def test_existing_output_cannot_be_overwritten_with_a_different_format(self):
        output = self.root / "same"
        self.build(output_format="quanx", output=output)
        before = digest_tree(output)
        with self.assertRaises(ConversionError):
            self.build(output_format="surge", output=output)
        self.assertEqual(digest_tree(output), before)

    def test_all_formats_cli_uses_one_snapshot_and_creates_separate_outputs(self):
        src = archive(self.root / "source.tgz")
        output = self.root / "all"
        result = subprocess.run([
            sys.executable, "-m", "quanx_rules", "--format", "all", "--archive", str(src),
            "--sha", SHA, "--repository", "test/rules", "--output", str(output),
        ], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        for name in ("quanx", "surge"):
            summary = validate_output(output / name)
            self.assertEqual(summary["source_sha"], SHA)
            self.assertEqual(summary["format"], name)
        self.assertEqual((output / "quanx/rules/asn/AS1.list").read_text().splitlines()[-1], "ip-cidr,192.0.2.0/24,proxy")
        self.assertEqual((output / "surge/rules/asn/AS1.list").read_text().splitlines()[-1], "IP-CIDR,192.0.2.0/24")

    def test_unknown_output_format_is_rejected(self):
        with self.assertRaises(ConversionError):
            convert_document({"version": 2, "rules": []}, output_format="unknown")

    def test_surge_entry_limit_rejects_oversized_set_before_replacement(self):
        self.build()
        output = self.root / "surge"
        before = digest_tree(output)
        src = archive(self.root / "big.tgz", {
            "geo/geosite/large.json": {"domain": ["a.test", "b.test", "c.test"]},
        })
        # Exercise the real build/limit failure using a small boundary so the
        # test does not need to manufacture a million-entry upstream document.
        with patch.dict(FORMATS, {"surge": replace(FORMATS["surge"], max_entries=2)}):
            with self.assertRaises(ConversionError):
                build_archive(src, output, SHA, "test/rules", output_format="surge")
        self.assertEqual(digest_tree(output), before)

    def test_legacy_report_without_format_remains_quanx(self):
        output = self.root / "legacy"
        self.build(output_format="quanx", output=output)
        report = output / "reports/summary.json"
        summary = json.loads(report.read_text())
        summary.pop("format")
        report.write_text(json.dumps(summary))
        self.assertEqual(validate_output(output), summary)
        self.build(output_format="quanx", output=output)
        self.assertEqual(validate_output(output)["format"], "quanx")


if __name__ == "__main__":
    unittest.main()
