import gzip
import json
from pathlib import Path
import tempfile
import unittest

from quanx_rules.build import build_archive, validate_output
from quanx_rules.convert import ConversionError
from tests.helpers import BASE, SHA, archive, digest_tree


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = self.root / "dist"

    def build(self, path, **kwargs):
        return build_archive(path, self.output, SHA, "test/rules", **kwargs)

    def test_all_categories_statuses_and_new_directories_are_discovered(self):
        src = archive(self.root / "src.tgz", {
            "geo/geosite/partial@cn.json": {"domain": "ok.test", "domain_regex": "a+"},
            "geo/geosite/regex.json": {"domain_regex": "r+"},
            "future/group/empty.json": {},
        })
        summary = self.build(src)
        self.assertEqual(summary["categories"], 8)
        self.assertEqual(summary["statuses"], {"supported": 5, "partial": 1, "unsupported-only": 1, "empty": 1})
        self.assertEqual(summary["output_files"], 6)
        self.assertEqual(summary["unsupported_entries"], 2)
        self.assertFalse((self.output / "rules/geo/geosite/regex.list").exists())
        manifest = json.loads((self.output / "reports/geo/geosite/0001.json").read_text())
        omitted = next(x for x in manifest if x["source"].endswith("regex.json"))
        self.assertEqual(omitted["unsupported"][0]["value"], "r+")
        index = (self.output / "indexes/geo/geosite/0001.md").read_text()
        self.assertIn("partial%40cn.list", index)
        self.assertEqual(validate_output(self.output), summary)

    def test_identical_inputs_produce_identical_outputs_and_removed_files_disappear(self):
        src = archive(self.root / "src.tgz", {"geo/geosite/old.json": {"domain": "old.test"}})
        self.build(src)
        before = digest_tree(self.output)
        self.build(src)
        self.assertEqual(digest_tree(self.output), before)
        self.build(archive(src))
        self.assertFalse((self.output / "rules/geo/geosite/old.list").exists())

    def test_invalid_late_json_does_not_replace_existing_output(self):
        src = archive(self.root / "src.tgz")
        self.build(src)
        before = digest_tree(self.output)
        archive(src, {"geo/geosite/zbad.json": {"port": 443}})
        with self.assertRaises(ConversionError):
            self.build(src)
        self.assertEqual(digest_tree(self.output), before)

    def test_traversal_duplicate_members_and_incomplete_archives_fail(self):
        for members in [
            list(BASE.items()) + [("../escape.json", {"domain": "x.test"})],
            list(BASE.items()) + [("asn/AS1.json", {"domain": "x.test"})],
        ]:
            with self.subTest(members=members[-1][0]), self.assertRaises(ConversionError):
                self.build(archive(self.root / "bad.tgz", members=members))
        src = archive(self.root / "truncated.tgz")
        src.write_bytes(src.read_bytes()[:-12])
        with self.assertRaises(ConversionError):
            self.build(src)
        self.assertFalse(self.output.exists())

    def test_missing_source_family_or_wrong_snapshot_is_rejected(self):
        src = archive(self.root / "src.tgz", remove=["asn/AS1.json"])
        with self.assertRaises(ConversionError):
            self.build(src)
        src = archive(src)
        with self.assertRaises(ConversionError):
            build_archive(src, self.output, "b" * 40, "test/rules")

    def test_large_removal_requires_explicit_override(self):
        extra = {f"asn/AS{n}.json": {"ip_cidr": "192.0.2.0/24"} for n in range(10, 20)}
        src = archive(self.root / "src.tgz", extra)
        self.build(src)
        before = digest_tree(self.output)
        archive(src)
        with self.assertRaises(ConversionError):
            self.build(src)
        self.assertEqual(digest_tree(self.output), before)
        self.assertEqual(self.build(src, allow_large_removal=True)["categories"], 5)

    def test_validation_detects_a_tampered_rule(self):
        self.build(archive(self.root / "src.tgz"))
        (self.output / "rules/asn/AS1.list").write_text("final,direct\n")
        with self.assertRaises(ConversionError):
            validate_output(self.output)

    def test_globally_empty_result_preserves_previous_subscriptions(self):
        src = archive(self.root / "src.tgz")
        self.build(src)
        before = digest_tree(self.output)
        archive(src, members=[(name, {}) for name in BASE])
        with self.assertRaises(ConversionError):
            self.build(src)
        self.assertEqual(digest_tree(self.output), before)
        with self.assertRaises(ConversionError):
            build_archive(src, self.root / "first-run", SHA, "test/rules")

    def test_valid_gzip_with_truncated_tar_preserves_previous_output(self):
        src = archive(self.root / "src.tgz", {"geo/geosite/last.json": {"domain": "last.test"}})
        self.build(src)
        before = digest_tree(self.output)
        data = gzip.decompress(src.read_bytes())
        # Five complete members remain, including all required directory families,
        # but the final category and the TAR end markers are absent.
        src.write_bytes(gzip.compress(data[:5 * 1024]))
        with self.assertRaises(ConversionError):
            self.build(src)
        self.assertEqual(digest_tree(self.output), before)
