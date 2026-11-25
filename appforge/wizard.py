"""Adaptive questions with immediate checkpointing and explicit provenance."""
import json
from .catalog import ROOT, catalogs
from .config import defaults, set_value
from .state import now


def get(config, path):
    value = config
    for part in path.split("."):
        value = value[part]
    return value


def questions(config):
    spec = json.loads((ROOT / "wizard" / "questions.json").read_text(encoding="utf-8"))
    for question in spec:
        mode = config["project"]["mode"]
        if question.get("modes") and mode not in question["modes"]:
            continue
        if mode in question.get("excludeModes", []):
            continue
        if any(get(config, key) != value for key, value in question.get("when", {}).items()):
            continue
        yield question


def run(workspace, accept_defaults=False, input_fn=input, output=print):
    output("AppForge discovery · recommended / auto / custom · Ctrl+C saves your place")
    while True:
        config, state = workspace.load()
        pending = [q for q in questions(config) if q["path"] not in state["answers"]]
        if not pending:
            output("Discovery saved. Next: python -m appforge plan")
            return
        q = pending[0]
        path = q["path"]
        recommended = get(config, path)
        choices = q.get("choices", [])
        if q.get("catalog"):
            choices = list(catalogs()[q["catalog"]])
        output(f"\n{q['label']}\n  Recommended: {json.dumps(recommended)}\n  {q['help']}")
        if choices:
            output("  Choices: " + ", ".join(str(c) for c in choices))
        raw = "auto" if accept_defaults else input_fn("  [Enter] recommended · auto · custom value (JSON for lists/bools): ").strip()
        source = "recommended" if not raw else "automatic" if raw.lower() == "auto" else "user"
        try:
            value = recommended if source != "user" else json.loads(raw)
        except json.JSONDecodeError:
            value = raw
        try:
            def answer(current, current_state):
                updated = set_value(current, path, value)
                if path == "project.category" and value != current["project"]["category"]:
                    recommended_config = defaults(current["project"]["name"], value, current["project"]["mode"])
                    for key in ("audience", "objective"):
                        if f"project.{key}" not in current_state["answers"]:
                            updated["project"][key] = recommended_config["project"][key]
                    for key in ("style", "palette", "primaryColor"):
                        if f"design.{key}" not in current_state["answers"]:
                            updated["design"][key] = recommended_config["design"][key]
                if path == "design.palette" and "design.primaryColor" not in current_state["answers"]:
                    updated["design"]["primaryColor"] = catalogs()["palettes"][value][2]
                current_state["answers"][path] = {"value": value, "source": source, "at": now()}
                current_state.update(approval=None, planHash=None, stage="discovery")
                return updated, current_state
            workspace.update(answer, "Answered " + path)
        except ValueError as error:
            output(str(error))
            if accept_defaults:
                raise
