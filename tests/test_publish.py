from pathlib import Path
import subprocess
import tempfile
import unittest

from quanx_rules.build import build_archive
from quanx_rules.publish import publish
from tests.helpers import SHA, archive


def git(*args):
    return subprocess.check_output(["git", *map(str, args)], text=True, stderr=subprocess.PIPE).strip()


class PublishTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.remote = self.root / "remote.git"
        git("init", "--bare", self.remote)
        self.output = self.root / "dist"
        self.build()

    def build(self, extra=None):
        src = archive(self.root / "source.tgz", extra)
        return build_archive(src, self.output, SHA, "test/rules", allow_large_removal=True)

    def test_initial_publication_and_identical_rerun(self):
        self.assertTrue(publish(self.output, str(self.remote)))
        head = git("--git-dir", self.remote, "rev-parse", "quanx")
        self.assertIn("host-suffix,google.com,proxy", git("--git-dir", self.remote, "show", "quanx:rules/geo/geosite/google.list"))
        self.assertFalse(publish(self.output, str(self.remote)))
        self.assertEqual(git("--git-dir", self.remote, "rev-parse", "quanx"), head)

    def test_changes_and_removals_are_normal_descendant_commits(self):
        self.build({"geo/geosite/old.json": {"domain": "old.test"}})
        publish(self.output, str(self.remote))
        old = git("--git-dir", self.remote, "rev-parse", "quanx")
        self.build()
        self.assertTrue(publish(self.output, str(self.remote)))
        self.assertEqual(git("--git-dir", self.remote, "rev-parse", "quanx^"), old)
        self.assertNotIn("old.list", git("--git-dir", self.remote, "ls-tree", "-r", "--name-only", "quanx"))

    def test_large_remote_removal_is_rejected_unless_explicitly_allowed(self):
        self.build({f"asn/AS{n}.json": {"ip_cidr": "192.0.2.0/24"} for n in range(10, 20)})
        publish(self.output, str(self.remote))
        head = git("--git-dir", self.remote, "rev-parse", "quanx")
        self.build()
        with self.assertRaises(ValueError):
            publish(self.output, str(self.remote))
        self.assertEqual(git("--git-dir", self.remote, "rev-parse", "quanx"), head)
        self.assertTrue(publish(self.output, str(self.remote), allow_large_removal=True))

    def test_rejected_push_is_a_failure(self):
        hook = self.remote / "hooks/pre-receive"
        hook.write_text("#!/bin/sh\nexit 1\n")
        hook.chmod(0o755)
        with self.assertRaises(RuntimeError):
            publish(self.output, str(self.remote))

    def test_unreachable_remote_is_not_treated_as_an_empty_branch(self):
        with self.assertRaises(RuntimeError):
            publish(self.output, str(self.root / "missing.git"))
