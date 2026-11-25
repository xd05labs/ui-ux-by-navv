"""Read declarative catalogs; importing a catalog never executes plugin code."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def catalogs():
    return {
        "blueprints": {key: read(path) for key, path in read("industry-blueprints/catalog.json").items()},
        "styles": read("design-library/catalog.json"),
        "palettes": read("design-engine/palettes/catalog.json"),
        "stacks": read("templates/stacks.json"),
    }


def blueprint(category):
    return catalogs()["blueprints"][category]
