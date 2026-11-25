"""Declarative UI/UX menus shared by the concise AI entry and its full context."""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOGS = {"styles": "design-library/catalog.json", "palettes": "design-engine/palettes/catalog.json"}


def read_json(root, relative):
    return json.loads((Path(root) / relative).read_text(encoding="utf-8"))


def load_uiux_flow(root=ROOT):
    flow = read_json(root, "wizard/uiux-flow.json")
    if flow.get("schemaVersion") != 1 or not flow.get("steps"):
        raise ValueError("Unsupported or empty UI/UX flow")
    ids, paths = set(), set()
    for step in flow["steps"]:
        if step["id"] in ids or not 1 <= len(step["questions"]) <= 3:
            raise ValueError("UI/UX stages must be unique and contain one to three questions")
        ids.add(step["id"])
        for question in step["questions"]:
            if question["path"] in paths or not question["path"].startswith("design."):
                raise ValueError("UI/UX question paths must be unique design fields")
            paths.add(question["path"])
            if "catalog" in question:
                if question["catalog"] not in CATALOGS:
                    raise ValueError("Unknown UI/UX catalog")
                values = read_json(root, CATALOGS[question["catalog"]])
                primary = question.get("primary", list(values))
                if not primary or len(primary) != len(set(primary)) or any(value not in values for value in primary):
                    raise ValueError("UI/UX menu contains an unknown or duplicate catalog choice")
                if len(primary) > 24:
                    raise ValueError("Curated menus support at most 24 choices")
            else:
                choices = question.get("choices", [])
                values = [choice["value"] for choice in choices]
                if not choices or len(choices) > 24 or len({json.dumps(v, sort_keys=True) for v in values}) != len(values):
                    raise ValueError("UI/UX choices must be concrete and unique")
            if question["default"] not in values:
                raise ValueError("UI/UX recommendation must be an available choice")
    if flow["steps"][0]["questions"][0]["path"] != "design.style":
        raise ValueError("The first UI/UX question must choose a visual style")
    return flow


def next_uiux_step(answers, root=ROOT, mode="quick", approved=False):
    """Use explicit answer keys, never implicit configuration defaults."""
    flow = load_uiux_flow(root)
    if mode in flow.get("excludeModes", []):
        return None
    for stage in flow["steps"]:
        pending = [question for question in stage["questions"] if question["path"] not in answers]
        if pending:
            return {"id": stage["id"], "title": stage["title"], "questions": copy.deepcopy(pending)}
    return None if approved else {**copy.deepcopy(flow["review"]), "questions": []}


def question_choices(question, root=ROOT, all_choices=False):
    if "catalog" not in question:
        return copy.deepcopy(question["choices"])
    values = read_json(root, CATALOGS[question["catalog"]])
    keys = list(values) if all_choices else question.get("primary", list(values))
    result = []
    for key in keys:
        label = key.replace("-", " ").capitalize()
        if question["catalog"] == "styles":
            detail = values[key]["description"]
        else:
            detail = " / ".join(values[key])
        result.append({"value": key, "label": label, "detail": detail})
    return result


def render_uiux_question(question, root=ROOT, all_choices=False):
    choices = question_choices(question, root, all_choices)
    lines = [f"**{question['label']}**", ""]
    for index, choice in enumerate(choices):
        code = str(index + 1) if all_choices else chr(65 + index)
        recommended = " (Recommended)" if choice["value"] == question["default"] else ""
        detail = " — " + choice["detail"] if choice.get("detail") else ""
        lines.append(f"- **{code}. {choice['label']}{recommended}**{detail}")
    if question.get("primary") and not all_choices:
        total = len(read_json(root, CATALOGS[question["catalog"]]))
        lines.append(f"- **{chr(65 + len(choices))}. Show all {total} styles** — expand the list, then wait for a choice.")
    label = next(choice["label"] for choice in question_choices(question, root, True) if choice["value"] == question["default"])
    lines.extend([
        f"- **Auto** — choose {label.lower()} for this question only.",
        "- **Custom** — describe your own preference or a combination.",
        "", f"Why this recommendation: {question['recommendationReason']}",
        f"Reply with the option {'number' if all_choices else 'letter'}, Auto, or Custom: your preference. Then wait for the next question.",
    ])
    return "\n".join(lines)


def render_remaining_uiux_steps(root=ROOT):
    sections = ["## Later design stages — reference only\n\nAsk one stage per reply. Do not send these stages before the user answers the current question. Skip only explicitly answered fields; keep recommendations separate from approvals."]
    for stage in load_uiux_flow(root)["steps"][1:]:
        sections.append(f"### {stage['title']}\n")
        for question in stage["questions"]:
            sections.append(render_uiux_question(question, root) + f"\n\nSave as `{question['path']}`.")
    return "\n\n".join(sections)
