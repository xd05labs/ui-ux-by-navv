import json
from pathlib import Path
import re
import shutil
import tempfile
import unittest

from appforge.ai_entry import ROOT, build_ai_start
from appforge.uiux import load_uiux_flow, question_choices, render_uiux_question, sample_path
from appforge.uiux_samples import build_sample_documents, check_samples


class VisualSampleTests(unittest.TestCase):
    def fixture(self):
        temporary = tempfile.TemporaryDirectory(prefix="appforge-visuals-")
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        for folder in ("wizard", "design-library", "design-engine/palettes", "assets/uiux"):
            shutil.copytree(ROOT / folder, root / folder)
        return root

    def test_every_question_and_the_expansion_have_checked_images(self):
        documents = build_sample_documents()
        questions = [q for step in load_uiux_flow()["steps"] for q in step["questions"]]
        self.assertEqual(len(documents), len(questions) + 1)
        self.assertEqual(check_samples(), len(documents))
        manifest = json.loads((ROOT / "assets/uiux/manifest.json").read_text())
        for question in questions:
            for expanded in ([False, True] if question.get("primary") else [False]):
                relative = sample_path(question, expanded)
                record = manifest["samples"][relative]
                choices = question_choices(question, all_choices=expanded)
                self.assertEqual([c["value"] for c in record["options"]], [c["value"] for c in choices])
                menu = render_uiux_question(question, all_choices=expanded)
                self.assertIn(f"]({relative})", menu)
                for option in record["options"]:
                    self.assertIn(f"**{option['code']}. {option['label']}", menu)
                self.assertIn("[Open visual samples]", menu)

    def test_entry_embeds_real_absolute_images_for_all_questions_and_forks(self):
        content = build_ai_start(repository="https://github.com/example-owner/example-repo", ref="release")
        images = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", content)
        self.assertEqual(len(images), 12)
        for url in images:
            self.assertTrue(url.startswith("https://raw.githubusercontent.com/example-owner/example-repo/release/assets/uiux/"))
            relative = "assets/uiux/" + url.split("/assets/uiux/")[1].split("?")[0]
            self.assertTrue((ROOT / relative).is_file(), relative)
            self.assertRegex(url, r"\.png\?v=[a-f0-9]{12}$")
        self.assertIn("With EVERY design question", content)
        self.assertIn("If images cannot render", content)
        self.assertIn("Static storyboard", (ROOT / "assets/uiux/motion.html").read_text(encoding="utf-8"))

    def test_catalog_changes_require_visual_regeneration(self):
        root = self.fixture()
        path = root / "design-engine/palettes/catalog.json"
        palettes = json.loads(path.read_text())
        palettes["ocean-blue"][0] = "#010203"
        path.write_text(json.dumps(palettes), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "stale"):
            check_samples(root)

    def test_changed_images_and_mismatched_labels_fail_integrity_check(self):
        root = self.fixture()
        image = root / "assets/uiux/style.png"
        original = image.read_bytes()
        image.write_bytes(original[:-10])
        with self.assertRaisesRegex(ValueError, "changed visual sample"):
            check_samples(root)
        image.write_bytes(original)
        path = root / "assets/uiux/manifest.json"
        manifest = json.loads(path.read_text())
        manifest["samples"]["assets/uiux/style.png"]["options"][0]["code"] = "Z"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "labels do not match"):
            check_samples(root)

    def test_path_safety_and_nonexpanded_menu_codes(self):
        with self.assertRaises(ValueError):
            sample_path({"path":"design.../private"})
        question = load_uiux_flow()["steps"][1]["questions"][0]
        menu = render_uiux_question(question, all_choices=True)
        self.assertIn("**A. Light", menu)
        self.assertIn("option letter", menu)
        self.assertIn("theme.png", menu)


if __name__ == "__main__":
    unittest.main()
