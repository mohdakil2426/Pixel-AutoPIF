from pathlib import Path
import re
import unittest


class WorkflowPolicyTests(unittest.TestCase):
    def test_validate_runs_for_pull_requests_main_and_manual_dispatch(self):
        workflow = Path(".github/workflows/validate.yml").read_text()
        self.assertIn("pull_request:", workflow)
        self.assertIn("push:", workflow)
        self.assertIn("- main", workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("producer:", workflow)
        self.assertIn("validate_coverage.py", workflow)

    def test_update_is_daily_review_only(self):
        workflow = Path(".github/workflows/update-catalog.yml").read_text()
        self.assertIn('cron: "17 3 * * *"', workflow)
        self.assertIn("pull-requests: write", workflow)
        self.assertNotIn("CATALOG_SIGNING_KEY_PKCS8_BASE64", workflow)
        self.assertNotIn("gh release create", workflow)

    def test_release_is_manual_protected_and_main_only(self):
        workflow = Path(".github/workflows/release-catalog.yml").read_text()
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("github.ref == 'refs/heads/main'", workflow)
        self.assertIn("environment: catalog-production", workflow)
        self.assertIn("CATALOG_SIGNING_KEY_PKCS8_BASE64", workflow)
        self.assertIn("validate_coverage.py", workflow)
        self.assertIn("gh release view", workflow)

    def test_all_external_actions_are_full_sha_pinned(self):
        for path in Path(".github/workflows").glob("*.yml"):
            text = path.read_text()
            for match in re.findall(r"uses:\s*([^\s]+)", text):
                owner_action, ref = match.split("@", 1)
                self.assertRegex(ref, r"^[0-9a-f]{40}$", owner_action)
