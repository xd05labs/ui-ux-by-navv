import json
from pathlib import Path
import shutil
import tempfile
import unittest

from appforge.ai_entry import ROOT, build_ai_start
from appforge.config import defaults, set_value
from appforge.uiux import (load_uiux_flow, next_uiux_step, question_choices,
                          render_uiux_question)


class UIUXTests(unittest.TestCase):
    def test_first_screen_asks_style_before_context_or_implementation(self):
        content = build_ai_start()
        question = content.index("Which UI style would you like?")
        self.assertLess(question, 1200)
        self.assertLess(question, content.index("## Full implementation context"))
        opening = content[:content.index("## Copy this with the link")]
        for choice in ("A. Minimal", "B. Bento", "C. Matte glass", "D. Apple inspired",
                       "E. Material design", "F. Corporate", "G. Futuristic", "H. Luxury",
                       "Show all 20 styles", "**Auto**", "**Custom**"):
            self.assertIn(choice, opening)
        self.assertIn("**STOP after asking this question", opening)
        self.assertNotIn("movement-history", opening)

    def test_config_defaults_do_not_count_as_design_answers(self):
        self.assertEqual(next_uiux_step({})["id"], "style")
        self.assertEqual(next_uiux_step(defaults())["id"], "style")

    def test_known_style_and_theme_skip_only_answered_questions(self):
        stage = next_uiux_step({"design.style": "minimal", "design.theme": "dark"})
        self.assertEqual(stage["id"], "colors")
        self.assertEqual([q["path"] for q in stage["questions"]], ["design.palette"])

    def test_one_automatic_answer_does_not_choose_the_entire_design(self):
        first = next_uiux_step({})["questions"][0]
        answers = {first["path"]: {"value": first["default"], "source": "automatic"}}
        following = next_uiux_step(answers)
        self.assertEqual(following["id"], "colors")
        self.assertEqual(len(following["questions"]), 2)

    def test_complete_answers_require_review_until_approved(self):
        answers = {q["path"]: q["default"] for stage in load_uiux_flow()["steps"] for q in stage["questions"]}
        review = next_uiux_step(answers)
        self.assertEqual(review["id"], "design-review")
        self.assertIn("Approve design", review["actions"])
        self.assertIsNone(next_uiux_step(answers, approved=True))
        self.assertEqual(next_uiux_step({}, approved=True)["id"], "style")
        self.assertIsNone(next_uiux_step({}, mode="backend-only"))

    def test_every_design_choice_maps_to_an_existing_typed_config_field(self):
        for stage in load_uiux_flow()["steps"]:
            self.assertLessEqual(len(stage["questions"]), 3)
            for question in stage["questions"]:
                for choice in question_choices(question, all_choices=True):
                    with self.subTest(path=question["path"], choice=choice["value"]):
                        set_value(defaults(), question["path"], choice["value"])
                menu = render_uiux_question(question)
                self.assertIn("(Recommended)", menu)
                self.assertIn("**Auto**", menu)
                self.assertIn("**Custom**", menu)

    def test_expanded_style_menu_preserves_all_catalog_styles(self):
        question = load_uiux_flow()["steps"][0]["questions"][0]
        choices = question_choices(question, all_choices=True)
        styles = json.loads((ROOT / "design-library/catalog.json").read_text(encoding="utf-8"))
        self.assertEqual({choice["value"] for choice in choices}, set(styles))
        expanded = render_uiux_question(question, all_choices=True)
        self.assertIn("**20.", expanded)
        self.assertIn("option number", expanded)
        self.assertNotIn("Show all 20 styles", expanded)

    def test_invalid_style_choices_or_a_nonvisual_first_question_are_rejected(self):
        with tempfile.TemporaryDirectory(prefix="appforge-uiux-") as temporary:
            root = Path(temporary)
            for relative in ("wizard/uiux-flow.json", "design-library/catalog.json", "design-engine/palettes/catalog.json"):
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / relative, target)
            path = root / "wizard/uiux-flow.json"
            original = json.loads(path.read_text(encoding="utf-8"))
            invalid = json.loads(json.dumps(original))
            invalid["steps"][0]["questions"][0]["primary"].append("missing-style")
            path.write_text(json.dumps(invalid), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_uiux_flow(root)
            invalid = json.loads(json.dumps(original))
            invalid["steps"][0]["questions"][0]["path"] = "design.theme"
            path.write_text(json.dumps(invalid), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_uiux_flow(root)


if __name__ == "__main__":
    unittest.main()
