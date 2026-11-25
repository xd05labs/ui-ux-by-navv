import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from appforge.ai_entry import (DEFAULT_REPOSITORY, MAX_BYTES, MAX_ENTRY_BYTES, ROOT,
                              build_ai_context, build_ai_documents, build_ai_start,
                              repository_url, source_files)


class AIEntryTests(unittest.TestCase):
    def fixture(self):
        temporary = tempfile.TemporaryDirectory(prefix="appforge-ai-entry-")
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        for relative in source_files():
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)
        return root

    def test_generated_entry_is_current_and_embeds_the_central_protocol(self):
        content = build_ai_start()
        self.assertEqual(content, (ROOT / "AI_START.md").read_text(encoding="utf-8"))
        master = (ROOT / "ai-core/master-instructions.md").read_text(encoding="utf-8").strip()
        self.assertIn(master, build_ai_context())
        self.assertEqual(build_ai_context(), (ROOT / "AI_CONTEXT.md").read_text(encoding="utf-8"))
        self.assertLessEqual(len(content.encode("utf-8")), MAX_ENTRY_BYTES)
        self.assertIn("## Shared UI/UX protocol", content)
        self.assertIn("A URL alone cannot give a model", content)

    def test_catalog_counts_and_question_paths_are_present_in_one_file(self):
        content = build_ai_context()
        for name in ("industry-blueprints/catalog.json", "design-library/catalog.json", "design-engine/palettes/catalog.json"):
            for key in json.loads((ROOT / name).read_text(encoding="utf-8")):
                self.assertIn(f"`{key}`", content)
        for question in json.loads((ROOT / "wizard/questions.json").read_text(encoding="utf-8")):
            self.assertIn(f"`{question['path']}`", content)
        self.assertIn('"status": "agent-assisted"', content)
        self.assertIn("Extra features/other stacks need an agent-assisted implementation", content)

    def test_workspace_and_environment_data_are_never_loaded(self):
        root = self.fixture()
        sentinel = "PRIVATE_WORKSPACE_SENTINEL_NEVER_EXPORT"
        (root / "workspace").mkdir()
        (root / "workspace/project.config.json").write_text(sentinel, encoding="utf-8")
        (root / "workspace/brief.md").write_text(sentinel, encoding="utf-8")
        (root / ".env").write_text(sentinel, encoding="utf-8")
        for name, content in build_ai_documents(root).items():
            self.assertNotIn(sentinel, content)
            self.assertEqual(content, build_ai_documents()[name])

    def test_protocol_change_changes_the_entry_and_its_fingerprint(self):
        root = self.fixture()
        previous = build_ai_start(root)
        path = root / "ai-core/master-instructions.md"
        path.write_text(path.read_text(encoding="utf-8") + "\nReviewed extra requirement.\n", encoding="utf-8")
        updated = build_ai_start(root)
        self.assertNotEqual(previous, updated)
        self.assertIn("Reviewed extra requirement.", build_ai_context(root))

    def test_output_is_stable_across_lf_and_crlf_checkouts(self):
        root = self.fixture()
        before = build_ai_documents(root)
        for relative in source_files(root):
            path = root / relative
            path.write_bytes(path.read_text(encoding="utf-8").replace("\n", "\r\n").encode("utf-8"))
        self.assertEqual(build_ai_documents(root), before)

    def test_catalog_cannot_read_outside_its_declared_source_tree(self):
        root = self.fixture()
        path = root / "industry-blueprints/catalog.json"
        for value in ("../.env", "workspace/brief.md", "industry-blueprints/../.env", "C:/private.json"):
            path.write_text(json.dumps({"unsafe": value}), encoding="utf-8")
            with self.subTest(path=value), self.assertRaises(ValueError):
                build_ai_start(root)

    def test_repository_addresses_are_credential_free_and_refs_are_validated(self):
        self.assertEqual(repository_url(DEFAULT_REPOSITORY + ".git"), DEFAULT_REPOSITORY)
        for url in ("https://example.com/owner/repo", "https://token@github.com/owner/repo",
                    DEFAULT_REPOSITORY + "?token=example", DEFAULT_REPOSITORY + "/blob/main/README.md"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                repository_url(url)
        with self.assertRaises(ValueError):
            build_ai_start(ref="../private")
        custom = build_ai_start(repository="https://github.com/example-owner/example-repo", ref="release")
        self.assertIn("https://raw.githubusercontent.com/example-owner/example-repo/release/AI_START.md", custom)
        self.assertNotIn(DEFAULT_REPOSITORY, custom)
        root = self.fixture()
        (root / "ai-core/entry-config.json").write_text(json.dumps({
            "repository": "https://github.com/example-owner/example-repo", "ref": "release"
        }), encoding="utf-8")
        self.assertIn("https://raw.githubusercontent.com/example-owner/example-repo/release/AI_START.md", build_ai_start(root))

    def test_portable_size_guard_rejects_unbounded_instruction_growth(self):
        root = self.fixture()
        path = root / "ai-core/master-instructions.md"
        path.write_text("x" * MAX_BYTES, encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "context budget"):
            build_ai_context(root)
        (root / "ai-core/uiux-discovery.md").write_text("x" * MAX_ENTRY_BYTES, encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "context budget"):
            build_ai_start(root)

    def test_check_command_is_read_only(self):
        before = {name: (ROOT / name).read_bytes() for name in build_ai_documents()}
        result = subprocess.run([sys.executable, "scripts/build_ai_start.py", "--check"],
                                cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual({name: (ROOT / name).read_bytes() for name in before}, before)


if __name__ == "__main__":
    unittest.main()
