import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from appforge.catalog import ROOT, catalogs
from appforge.config import check, defaults, recommend_stack, set_value
from appforge.design import contrast_report, preview
from appforge.generator import generate, recover_generation, render, safe_target
from appforge.planning import approve, create_plan
from appforge.schema import Invalid, validate
from appforge.state import Workspace, atomic
from appforge.validation import validate_project
from appforge.wizard import questions, run


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Workspace(Path(self.temp.name) / "workspace")
        self.workspace.initialize(defaults())

    def ready(self):
        create_plan(self.workspace)
        approve(self.workspace)

    def test_all_blueprints_have_valid_defaults_and_render(self):
        for category, bp in catalogs()["blueprints"].items():
            with self.subTest(category=category):
                config = check(defaults(category=category))
                self.assertIn("app.py", render(config))
                self.assertGreater(len(bp["acceptanceCriteria"]), 0)
                self.assertEqual(len({f["name"] for f in bp["fields"]}), len(bp["fields"]))

    def test_all_palettes_meet_semantic_contrast_targets(self):
        for palette, values in catalogs()["palettes"].items():
            config = defaults()
            config["design"].update(palette=palette, primaryColor=values[2])
            for mode, pairs in contrast_report(config).items():
                self.assertTrue(all(pair["passed"] for pair in pairs), (palette, mode, pairs))

    def test_closed_schema_rejects_unknown_and_wrong_types(self):
        for path, value in [("design.borderRadius", True), ("design.primaryColor", "red"), ("design.background.opacity", 9), ("project.devices", ["watch"]), ("schemaVersion", 2)]:
            with self.subTest(path=path), self.assertRaises(Invalid):
                set_value(defaults(), path, value)
        config = defaults(); config["unknown"] = True
        with self.assertRaises(Invalid):
            check(config)

    def test_schema_unknown_keywords_and_external_refs_fail_closed(self):
        with self.assertRaises(Invalid):
            validate(5, {"multipleOf": 2})
        with self.assertRaises(Invalid):
            validate(5, {"$ref": "../pyproject.toml"})

    def test_cross_field_auth_rule(self):
        config = defaults(); config["features"]["authentication"] = False
        with self.assertRaises(Invalid):
            check(config)

    def test_recommendations_are_advisory_and_explain_scale_tradeoffs(self):
        config = defaults()
        self.assertEqual(recommend_stack(config)["status"], "executable")
        config["constraints"]["expectedUsers"] = 10000
        self.assertEqual(recommend_stack(config)["status"], "agent-assisted")
        self.assertEqual(config["stack"]["database"], "sqlite")

    def test_custom_requirements_are_saved_but_never_silently_ignored(self):
        config = set_value(defaults(), "requirements.features", ["Signed payment webhooks"])
        with self.assertRaises(Invalid):
            render(config)

    def test_dotted_updates_do_not_mutate_input(self):
        before = defaults(); after = set_value(before, "design.borderRadius", 20)
        self.assertEqual(before["design"]["borderRadius"], 14)
        self.assertEqual(after["design"]["borderRadius"], 20)

    def test_wizard_skips_conditional_and_existing_design(self):
        config = defaults(mode="existing")
        paths = [q["path"] for q in questions(config)]
        self.assertIn("constraints.existingPath", paths)
        self.assertNotIn("design.style", paths)
        self.assertNotIn("constraints.referenceAssets", paths)

    def test_wizard_resumes_without_reasking_and_records_sources(self):
        run(self.workspace, accept_defaults=True, output=lambda _: None)
        first = self.workspace.load()[1]
        self.assertTrue(first["answers"])
        self.assertTrue(all(v["source"] == "automatic" for v in first["answers"].values()))
        run(self.workspace, input_fn=lambda _: self.fail("Asked a saved question"), output=lambda _: None)
        self.assertEqual(first["answers"], self.workspace.load()[1]["answers"])

    def test_atomic_journal_recovery(self):
        config, state = self.workspace.load()
        config["project"]["name"] = "Recovered"
        atomic(self.workspace.path / ".transaction.json", {"config": config, "state": state})
        self.assertEqual(self.workspace.load()[0]["project"]["name"], "Recovered")
        self.assertFalse((self.workspace.path / ".transaction.json").exists())

    def test_concurrent_writer_lock(self):
        with self.workspace.lock(), self.assertRaises(Invalid):
            self.workspace.load()

    def test_undo_restores_config_and_invalidates_approval(self):
        def update(config, state):
            config["project"]["name"] = "Changed"
            return config, state
        self.workspace.update(update, "Changed name")
        self.workspace.undo()
        config, state = self.workspace.load()
        self.assertEqual(config["project"]["name"], "My Application")
        self.assertIsNone(state["approval"])

    def test_approval_required_and_stale_config_is_rejected(self):
        with self.assertRaises(Invalid):
            generate(self.workspace)
        self.ready()
        config, state = self.workspace.load()
        config["project"]["name"] = "Unreviewed change"
        atomic(self.workspace.config_path, config)
        with self.assertRaises(Invalid):
            generate(self.workspace)

    def test_source_changes_invalidate_approval(self):
        self.ready()
        with patch("appforge.planning.source_hash", return_value="changed"):
            with self.assertRaises(Invalid):
                generate(self.workspace)

    def test_dry_run_does_not_write_output(self):
        self.ready()
        impact = generate(self.workspace, dry_run=True)
        self.assertIn("app.py", impact["changed"])
        self.assertFalse((self.workspace.path / "generated-app").exists())

    def test_generation_is_idempotent(self):
        self.ready(); generate(self.workspace)
        self.assertEqual(generate(self.workspace), {"changed": [], "removed": [], "conflicts": []})

    def test_manual_edits_and_unmanaged_files_are_preserved(self):
        self.ready(); generate(self.workspace)
        path = self.workspace.path / "generated-app" / "app.py"
        path.write_text("# User implementation\n", encoding="utf-8")
        with self.assertRaises(Invalid):
            generate(self.workspace)
        self.assertEqual(path.read_text(), "# User implementation\n")

    def test_unmanaged_collision_causes_no_partial_writes(self):
        self.ready()
        path = self.workspace.path / "generated-app" / "app.py"
        path.parent.mkdir(); path.write_text("# Existing source", encoding="utf-8")
        with self.assertRaises(Invalid):
            generate(self.workspace)
        self.assertFalse((path.parent / "app.config.json").exists())

    def test_path_traversal_is_rejected(self):
        for relative in ("../outside.py", "/outside.py", "C:/outside.py", "x\\outside.py"):
            with self.subTest(path=relative), self.assertRaises(Invalid):
                safe_target(self.workspace.path, relative)

    def test_interrupted_generation_can_be_rolled_back(self):
        self.ready(); generate(self.workspace)
        path = self.workspace.path / "generated-app" / "app.py"
        original = path.read_bytes()
        backup_id = "a" * 32
        backup = self.workspace.path / ".generation-backups" / backup_id / "app.py"
        backup.parent.mkdir(parents=True); backup.write_bytes(original)
        path.write_text("# interrupted", encoding="utf-8")
        manifest = json.loads((self.workspace.path / "generation-manifest.json").read_text())
        atomic(self.workspace.path / ".generation-journal.json", {"backup": backup_id, "existing": ["app.py"], "created": [], "manifest": manifest})
        recover_generation(self.workspace)
        self.assertEqual(path.read_bytes(), original)

    def test_design_only_and_backend_only_outputs(self):
        config = defaults(mode="design-only")
        self.assertEqual(set(render(config)), {"index.html", "README.md", "GENERATED_APP_LICENSE.txt"})
        config = defaults(mode="backend-only")
        self.assertIn("app.py", render(config))
        self.assertFalse(any(key.startswith("static/") for key in render(config)))

    def test_generated_apps_keep_their_explicit_customization_permission(self):
        for mode in ("quick", "design-only", "backend-only"):
            with self.subTest(mode=mode):
                files = render(defaults(mode=mode))
                self.assertIn(b"use, copy, modify, merge", files["GENERATED_APP_LICENSE.txt"])
                self.assertNotIn("LICENSE", files)

    def test_unsupported_features_and_existing_mode_do_not_silently_generate(self):
        for config in [set_value(defaults(), "features.payments", "stripe"), set_value(defaults(), "stack.frontend", "react"), defaults(mode="existing"), defaults(mode="reference"), defaults(mode="enterprise")]:
            with self.assertRaises(Invalid):
                render(config)

    def test_preview_escapes_user_content(self):
        config = defaults(name='</script><script>alert("x")</script>')
        content = preview(config, catalogs()["blueprints"]["saas"])
        self.assertNotIn(config["project"]["name"], content)
        self.assertIn("&lt;/script&gt;", content)

    def test_generated_integration_suite_and_honest_gates(self):
        self.ready(); generate(self.workspace)
        report = validate_project(self.workspace)
        self.assertTrue(report["checksPassed"], report["commands"])
        self.assertFalse(report["productionReady"])
        self.assertIn("pending", [gate["status"] for gate in report["gates"]])

    def test_cli_rejects_invalid_configuration(self):
        result = subprocess.run([sys.executable, "-m", "appforge", "--workspace", str(self.workspace.path), "set", "design.borderRadius", "99"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("outside permitted range", result.stderr)


if __name__ == "__main__":
    unittest.main()
