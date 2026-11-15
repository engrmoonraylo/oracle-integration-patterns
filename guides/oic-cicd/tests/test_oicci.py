"""Regression tests built from real exports captured during the OIC CI/CD POC.

Rev 1.0  2026-11-15  Initial version.

Fixtures (tests/fixtures):
  dev_nochange1/2.car            two DEV project exports with no change between them
  dev_int1_edit_same_version.car DEV export after editing INT1 01.00.0000 in place
  dev_full_project.car           DEV full project export (deployment left blank)
  release_REL_R1.car             DEV deployment: INT1 01.00.0001 (same-version edit) + INT2 01.00.0001 (new)
  release_HOTFIX_INT1_101.car    DEV deployment whose identifier already exists in PROD
  prod_before_R1.car             PROD export before importing REL_R1
  prod_after_R1.car              PROD export after importing REL_R1 (INT1 01.00.0001 was silently skipped)
"""
import contextlib
import io
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
import oiccar  # noqa: E402
import oicci   # noqa: E402

F = lambda name: os.path.join(HERE, "fixtures", name)  # noqa: E731

# Keep fixture findings out of the GitHub job summary: reviewers must only see
# findings for the release under review.
os.environ.pop("GITHUB_STEP_SUMMARY", None)


def run(*argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = oicci.main(list(argv))
    return code, out.getvalue()


def tree(path):
    result = {}
    for root, _, files in os.walk(path):
        for name in files:
            full = os.path.join(root, name)
            with open(full, "rb") as fh:
                result[os.path.relpath(full, path)] = fh.read()
    return result


class Normalization(unittest.TestCase):
    def test_no_change_exports_are_identical(self):
        with tempfile.TemporaryDirectory() as tmp:
            oiccar.expand(F("dev_nochange1.car"), os.path.join(tmp, "a"))
            oiccar.expand(F("dev_nochange2.car"), os.path.join(tmp, "b"))
            self.assertEqual(tree(os.path.join(tmp, "a")), tree(os.path.join(tmp, "b")))

    def test_edit_is_isolated_to_one_integration(self):
        before = oiccar.load(F("dev_nochange2.car"))["integrations"]
        after = oiccar.load(F("dev_int1_edit_same_version.car"))["integrations"]
        changed = sorted(k for k in after if after[k]["review_fp"] != before[k]["review_fp"])
        self.assertEqual(changed, ["XXMRL_DEMO_INT1_SCHEDB_INT|01.00.0000"])

    def test_content_survives_instance_move(self):
        # INT2 01.00.0001 was imported into PROD unchanged: content must match.
        rel = oiccar.load(F("release_REL_R1.car"))["integrations"]
        prod = oiccar.load(F("prod_after_R1.car"))["integrations"]
        key = "XXMRL_DEMO_INT2_SCHEDB_INT|01.00.0001"
        self.assertEqual(rel[key]["content_fp"], prod[key]["content_fp"])


class Classification(unittest.TestCase):
    def test_deployment_vs_full_project(self):
        self.assertEqual(oiccar.deployment_id(oiccar.load(F("release_REL_R1.car"))), "REL_R1")
        self.assertIsNone(oiccar.deployment_id(oiccar.load(F("dev_full_project.car"))))

    def test_dependencies_are_declared(self):
        integ = oiccar.load(F("release_REL_R1.car"))["integrations"]
        deps = integ["XXMRL_DEMO_INT2_SCHEDB_INT|01.00.0001"]["dependencies"]["lookups"]
        self.assertEqual(sorted(deps), ["XXMRL_DEMO_CUSTOM_LKP", "XXMRL_DEMO_NEW_LKP"])


class Guard(unittest.TestCase):
    def test_blocks_same_version_change(self):
        code, out = run("check", F("release_REL_R1.car"), "--prod", F("prod_before_R1.car"))
        self.assertEqual(code, 1)
        self.assertIn("silently skip", out)
        self.assertIn("will NOT be applied", out)            # CUSTOM_LKP
        self.assertIn("will be created", out)                # NEW_LKP

    def test_blocks_reused_deployment_identifier(self):
        code, out = run("check", F("release_HOTFIX_INT1_101.car"), "--prod", F("prod_before_R1.car"))
        self.assertEqual(code, 1)
        self.assertIn("already exists in PROD", out)

    def test_blocks_full_project_archive(self):
        code, out = run("check", F("dev_full_project.car"), "--prod", F("prod_before_R1.car"))
        self.assertEqual(code, 1)
        self.assertIn("Not a deployment export", out)

    def test_first_install_passes(self):
        code, _ = run("check", F("dev_full_project.car"))
        self.assertEqual(code, 0)


class Verify(unittest.TestCase):
    def test_detects_silent_skip(self):
        code, out = run("verify", F("release_REL_R1.car"), "--prod", F("prod_after_R1.car"))
        self.assertEqual(code, 1)
        self.assertIn("content differs from the release", out)
        self.assertIn("kept its PROD values", out)


if __name__ == "__main__":
    unittest.main()
