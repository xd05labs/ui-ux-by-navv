"""Validate catalogs, schemas, references and examples; optionally use jsonschema."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from appforge.catalog import catalogs
from appforge.ai_entry import build_ai_documents
from appforge.uiux_samples import check_samples
from appforge.config import check, defaults
from appforge.design import contrast_report
from appforge.schema import validate_file


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--jsonschema", action="store_true", help="Also validate with the independent Draft 2020-12 implementation")
    args = parser.parse_args()
    data = catalogs()
    schemas = {p.name: json.loads(p.read_text(encoding="utf-8")) for p in (ROOT / "schemas").glob("*.schema.json")}
    configs = [defaults(category=category) for category in data["blueprints"]]
    configs.extend(json.loads(path.read_text(encoding="utf-8")) for path in (ROOT / "examples").glob("*/project.config.json"))
    for config in configs:
        check(config)
        assert all(pair["passed"] for pairs in contrast_report(config).values() for pair in pairs)
    for key, bp in data["blueprints"].items():
        assert key == bp["id"] and bp["style"] in data["styles"] and bp["palette"] in data["palettes"]
        assert bp["pages"] and bp["workflows"] and bp["extensions"] and bp["acceptanceCriteria"]
        for field in bp["fields"]:
            assert field["type"] in ("text", "number", "date", "url")
            assert field["name"].replace("_", "").isalnum()
    for question in json.loads((ROOT / "wizard" / "questions.json").read_text()):
        assert question["label"] and question["help"]
        value = defaults()
        for part in question["path"].split("."):
            value = value[part]
    for entry in ("AGENTS.md", "CLAUDE.md", "GEMINI.md", ".github/copilot-instructions.md", ".cursor/rules/appforge.mdc", ".windsurf/rules/appforge.md"):
        assert "ai-core/master-instructions.md" in (ROOT / entry).read_text(encoding="utf-8")
    for name, content in build_ai_documents(ROOT).items():
        path = ROOT / name
        if not path.exists() or path.read_text(encoding="utf-8") != content:
            raise ValueError(name + " is missing or stale. Run python scripts/build_ai_start.py")
    visual_samples = check_samples(ROOT)
    independent = "not requested"
    if args.jsonschema:
        from jsonschema import Draft202012Validator
        from referencing import Registry, Resource
        registry = Registry().with_resources((name, Resource.from_contents(schema)) for name, schema in schemas.items())
        for schema in schemas.values():
            Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schemas["project.schema.json"], registry=registry)
        for config in configs:
            validator.validate(config)
        independent = "passed"
    print(json.dumps({"passed": True, "blueprints": len(data["blueprints"]), "styles": len(data["styles"]),
                      "palettes": len(data["palettes"]), "configsValidated": len(configs), "schemas": len(schemas),
                      "independentJsonSchema": independent, "aiEntry": "current", "visualSamples": visual_samples}, indent=2))


if __name__ == "__main__":
    main()
