"""Pure rendering plus collision-safe, journaled managed-file generation."""
import hashlib
import html
import json
import shutil
from pathlib import Path
from uuid import uuid4
from .catalog import ROOT, blueprint
from .design import css, preview
from .planning import plan_hash
from .schema import Invalid
from .state import atomic, now


def sha(data):
    return hashlib.sha256(data).hexdigest()


def supported(config):
    if config["project"]["mode"] == "design-only":
        return
    stack = config["stack"]
    required = {"frontend": "vanilla", "backend": "python-wsgi", "database": "sqlite", "api": "rest", "applicationType": "full-stack"}
    if any(stack[k] != v for k, v in required.items()):
        raise Invalid("This stack needs an agent-assisted adapter. The executable adapter requires vanilla/python-wsgi/sqlite/rest/full-stack; see docs/capabilities.md.")
    features = config["features"]
    if any(config["requirements"].values()):
        raise Invalid("Custom feature/workflow/acceptance requirements need agent-assisted implementation. They are retained in requirements.md; the generic adapter cannot silently mark them complete.")
    if stack["authentication"] != "email-password" or stack["storage"] != "local":
        raise Invalid("This authentication or storage provider requires an agent-assisted integration; the executable adapter uses email/password and local SQLite storage.")
    if not features["authentication"]:
        raise Invalid("The private workspace adapter requires authentication. Use design-only for a public prototype.")
    if any(features[k] for k in ("notifications", "realTimeUpdates", "multilingual")) or features["payments"] != "none":
        raise Invalid("Requested integration is not implemented by this adapter. See integrations/README.md for the agent-assisted contract.")
    if config["project"]["language"] != "en":
        raise Invalid("Executable interface translations currently support en only; other languages need an agent-assisted adapter.")
    if set(config["project"]["roles"]) != {"admin", "editor", "viewer"}:
        raise Invalid("The executable role model is admin/editor/viewer; custom roles require an adapter.")
    mode = config["project"]["mode"]
    if mode == "existing":
        raise Invalid("Existing-project mode preserves the original application. Follow ai-core/existing-project.md instead of generating over it.")
    if mode == "reference":
        raise Invalid("Reference mode requires agent-assisted visual analysis and implementation; the token-only adapter does not reproduce uploaded references.")
    if mode == "enterprise":
        raise Invalid("Enterprise mode requires an agent-assisted governance and infrastructure implementation; use its reviewed architecture rather than a generic register.")
    bg = config["design"]["background"]
    if bg["type"] not in ("solid", "gradient", "mesh", "svg-pattern"):
        raise Invalid("This background needs asset analysis or an advanced renderer. Choose solid/gradient/mesh/svg-pattern for the executable adapter.")
    if bg["source"] or config["design"]["typography"] == "custom" or config["design"]["icons"] == "custom":
        raise Invalid("Custom assets/fonts/icons require an agent-assisted asset review; the executable adapter uses local system assets.")


def render(config):
    supported(config)
    bp = blueprint(config["project"]["category"])
    if config["project"]["mode"] == "design-only":
        return {"index.html": preview(config, bp).encode(), "README.md": b"# Design concept\nOpen index.html. This contains sample data only; no backend is generated.\n",
                "GENERATED_APP_LICENSE.txt": (ROOT / "GENERATED_APP_LICENSE.txt").read_bytes()}
    files = {}
    template_root = ROOT / "templates" / "python-workspace"
    for path in sorted(template_root.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            files[path.relative_to(template_root).as_posix()] = path.read_bytes()
    files["app.config.json"] = (json.dumps({"name": config["project"]["name"], "language": config["project"]["language"], "objective": config["project"]["objective"],
                                          "design": config["design"], "features": config["features"], "blueprint": bp}, indent=2) + "\n").encode()
    files["static/tokens.css"] = css(config).encode()
    files["static/workspace.css"] = (ROOT / "components" / "workspace.css").read_bytes()
    files["GENERATED_APP_LICENSE.txt"] = (ROOT / "GENERATED_APP_LICENSE.txt").read_bytes()
    name = html.escape(config["project"]["name"])
    files["static/index.html"] = files["static/index.html"].decode().replace("__APP_NAME__", name).encode()
    if config["project"]["mode"] == "backend-only":
        for key in list(files):
            if key.startswith("static/"):
                del files[key]
    return files


def safe_target(root, relative):
    part = Path(relative)
    if part.is_absolute() or ".." in part.parts or "\\" in relative or ":" in relative:
        raise Invalid(f"Unsafe managed file path: {relative}")
    root = Path(root)
    if root.is_symlink() or root.resolve() != root.absolute():
        raise Invalid("Generated application directory cannot be a symlink or junction")
    target = root / part
    if not target.resolve().is_relative_to(root.resolve()):
        raise Invalid("Managed output escapes application directory")
    current = target
    while current != root:
        if current.is_symlink():
            raise Invalid(f"Symlink in managed output: {relative}")
        current = current.parent
    return target


def load_manifest(workspace):
    path = workspace.path / "generation-manifest.json"
    value = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"files": {}}
    if not isinstance(value.get("files"), dict):
        raise Invalid("Invalid generation manifest")
    return value


def changes(workspace, config):
    files = render(config)
    output = workspace.path / "generated-app"
    manifest = load_manifest(workspace)
    conflicts = []
    changed = []
    removed = []
    for relative in sorted(set(files) | set(manifest["files"])):
        target = safe_target(output, relative)
        if target.exists() and not target.is_file():
            conflicts.append(relative)
            continue
        existing = target.read_bytes() if target.exists() else None
        desired = files.get(relative)
        old_hash = manifest["files"].get(relative)
        if existing is not None and existing != desired and (not old_hash or sha(existing) != old_hash):
            conflicts.append(relative)
        elif desired is None:
            if existing is not None:
                removed.append(relative)
        elif desired != existing:
            changed.append(relative)
    return files, {"changed": changed, "removed": removed, "conflicts": conflicts}


def generate(workspace, dry_run=False):
    with workspace.lock():
        config, state = workspace._load()
        fingerprint = plan_hash(config)
        if not state["approval"] or state["approval"]["hash"] != fingerprint:
            raise Invalid("Generation requires approval of the current plan. Run plan, review, then approve --yes.")
        files, impact = changes(workspace, config)
        if dry_run:
            return impact
        if impact["conflicts"]:
            raise Invalid("Preserved edited/unmanaged files: " + ", ".join(impact["conflicts"]) + ". Review and merge manually; see docs/recovery.md.")
        if (workspace.path / ".generation-journal.json").exists():
            raise Invalid("Interrupted generation found; run recover-generation first.")
        output = workspace.path / "generated-app"
        affected = impact["changed"] + impact["removed"]
        backup = workspace.path / ".generation-backups" / uuid4().hex
        journal = {"backup": backup.name, "existing": [], "created": [], "manifest": load_manifest(workspace)}
        for relative in affected:
            target = safe_target(output, relative)
            if target.exists():
                saved = safe_target(backup, relative)
                saved.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, saved)
                journal["existing"].append(relative)
            else:
                journal["created"].append(relative)
        atomic(workspace.path / ".generation-journal.json", journal)
        for relative in impact["changed"]:
            target = safe_target(output, relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            temp = target.with_name(target.name + ".appforge-tmp")
            temp.write_bytes(files[relative])
            temp.replace(target)
        for relative in impact["removed"]:
            safe_target(output, relative).unlink()
        atomic(workspace.path / "generation-manifest.json", {"schemaVersion": 1, "at": now(), "planHash": fingerprint,
                                                            "files": {key: sha(content) for key, content in files.items()}})
        state.update(stage="generated")
        workspace._commit(config, state, "Generated managed application source")
        (workspace.path / ".generation-journal.json").unlink()
        return impact


def recover_generation(workspace):
    with workspace.lock():
        path = workspace.path / ".generation-journal.json"
        if not path.exists():
            raise Invalid("No interrupted generation journal found")
        journal = json.loads(path.read_text(encoding="utf-8"))
        if len(journal["backup"]) != 32 or any(c not in "0123456789abcdef" for c in journal["backup"]):
            raise Invalid("Invalid generation backup identifier")
        backup = workspace.path / ".generation-backups" / journal["backup"]
        output = workspace.path / "generated-app"
        for relative in journal["existing"]:
            target = safe_target(output, relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(safe_target(backup, relative), target)
        for relative in journal["created"]:
            safe_target(output, relative).unlink(missing_ok=True)
        atomic(workspace.path / "generation-manifest.json", journal["manifest"])
        config, state = workspace._load()
        state.update(stage="approved", validations=[])
        workspace._commit(config, state, "Rolled back interrupted generation")
        path.unlink()
