import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from . import __version__
from .catalog import ROOT, catalogs
from .config import MODES, check, defaults, recommend_stack, set_value
from .generator import generate, recover_generation
from .planning import approve, create_plan, plan_hash
from .schema import Invalid
from .state import Workspace, atomic, now
from .validation import validate_project
from .wizard import run as run_wizard


def parse_value(value):
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def flatten(value, prefix=""):
    for key, item in value.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(item, dict):
            yield from flatten(item, path)
        else:
            yield path, item


def doctor(path):
    capabilities = {"fileRead": ROOT.is_dir(), "fileWrite": False, "terminal": False,
                    "imageAnalysis": None, "browserPreview": None, "networkAccess": None,
                    "testing": True, "python": sys.version.split()[0], "git": bool(shutil.which("git")),
                    "notes": "null means not probed. LLM tool capabilities must be declared by the current agent; no outbound probes are performed."}
    try:
        with tempfile.TemporaryDirectory(prefix="appforge-doctor-", dir=path) as temporary:
            (Path(temporary) / "probe").write_text("probe", encoding="utf-8")
            capabilities["fileWrite"] = True
    except OSError:
        pass
    result = subprocess.run([sys.executable, "-c", "pass"], capture_output=True, timeout=10)
    capabilities["terminal"] = result.returncode == 0
    return capabilities


def serve_preview(path, port):
    from http.server import BaseHTTPRequestHandler, HTTPServer
    if not path.exists():
        raise Invalid("No preview found. Run plan first.")
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path not in ("/", "/design-preview.html"):
                self.send_error(404)
                return
            body = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
    with HTTPServer(("127.0.0.1", port), Handler) as server:
        print(f"Design preview: http://127.0.0.1:{port} (Ctrl+C to stop)", flush=True)
        server.serve_forever()


def parser():
    p = argparse.ArgumentParser(prog="appforge", description="Ask. Design. Generate. Validate. Deploy.")
    p.add_argument("--version", action="version", version=__version__)
    p.add_argument("--workspace", type=Path, default=ROOT / "workspace", help="Saved project directory; put before the command")
    sub = p.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="Create a new project without generating application code")
    init.add_argument("--name", default="My Application")
    init.add_argument("--category", choices=list(catalogs()["blueprints"]), default="saas")
    init.add_argument("--mode", choices=MODES, default="quick")
    init.add_argument("--defaults", action="store_true", help="Record recommended discovery defaults")
    wizard = sub.add_parser("wizard", help="Resume only unanswered relevant discovery questions")
    wizard.add_argument("--defaults", action="store_true")
    setting = sub.add_parser("set", help="Update a typed configuration value and invalidate approval")
    setting.add_argument("path")
    setting.add_argument("value")
    importing = sub.add_parser("import", help="Import a complete schema-valid configuration, including preview JSON")
    importing.add_argument("file", type=Path)
    sub.add_parser("plan", help="Write requirements, architecture, tokens and interactive preview")
    approval = sub.add_parser("approve", help="Approve the reviewed current plan")
    approval.add_argument("--yes", action="store_true", required=True, help="Explicitly acknowledge review of requirements, architecture and design preview")
    generation = sub.add_parser("generate", help="Generate approved managed source without overwriting manual edits")
    generation.add_argument("--dry-run", action="store_true")
    sub.add_parser("validate", help="Execute available checks and write honest quality-gate evidence")
    sub.add_parser("undo", help="Restore previous configuration checkpoint; generated code is preserved")
    sub.add_parser("recover-generation", help="Roll back an interrupted generation from its journal")
    sub.add_parser("status")
    sub.add_parser("recommend", help="Explain a stack recommendation without changing configuration")
    sub.add_parser("doctor")
    catalog = sub.add_parser("catalog")
    catalog.add_argument("kind", choices=["blueprints", "styles", "palettes", "stacks"])
    preview = sub.add_parser("preview")
    preview.add_argument("--serve", action="store_true")
    preview.add_argument("--port", type=int, default=4173)
    return p


def execute(args):
    workspace = Workspace(args.workspace)
    command = args.command
    if command == "doctor":
        return doctor(ROOT)
    if command == "catalog":
        return catalogs()[args.kind]
    if command == "init":
        workspace.initialize(defaults(args.name, args.category, args.mode))
        if args.defaults:
            run_wizard(workspace, accept_defaults=True)
        return {"workspace": str(workspace.path), "next": "wizard, then plan; no application code has been generated"}
    if command == "wizard":
        run_wizard(workspace, accept_defaults=args.defaults)
    elif command == "set":
        def update(config, state):
            value = parse_value(args.value)
            config = set_value(config, args.path, value)
            state["answers"][args.path] = {"value": value, "source": "user", "at": now()}
            state.update(approval=None, planHash=None, stage="discovery")
            return config, state
        workspace.update(update, "Changed " + args.path)
        return {"updated": args.path, "next": "plan"}
    elif command == "import":
        incoming = check(json.loads(args.file.read_text(encoding="utf-8")))
        def update(config, state):
            state["answers"] = {path: {"value": value, "source": "imported", "at": now()} for path, value in flatten(incoming)}
            state.update(approval=None, planHash=None, stage="discovery")
            return incoming, state
        workspace.update(update, "Imported schema-valid configuration")
        return {"imported": str(args.file), "next": "plan"}
    elif command == "plan":
        return {"planHash": create_plan(workspace), "review": [str(workspace.path / file) for file in ("requirements.md", "architecture.md", "decisions.md", "design-preview.html")], "next": "approve --yes"}
    elif command == "approve":
        approve(workspace)
        return {"approved": True, "next": "generate --dry-run, then generate"}
    elif command == "generate":
        return generate(workspace, dry_run=args.dry_run)
    elif command == "validate":
        report = validate_project(workspace)
        print(json.dumps({"checksPassed": report["checksPassed"], "productionReady": report["productionReady"], "report": str(workspace.path / "quality-report.json"), "gates": report["gates"]}, indent=2))
        return 0 if report["checksPassed"] else 1
    elif command == "undo":
        workspace.undo()
        return {"restored": True, "next": "plan; existing generated code is preserved"}
    elif command == "recover-generation":
        recover_generation(workspace)
        return {"recovered": True}
    elif command == "status":
        config, state = workspace.load()
        return {"project": config["project"], "stage": state["stage"], "answered": len(state["answers"]),
                "approvalCurrent": bool(state["approval"] and state["approval"]["hash"] == plan_hash(config)),
                "updatedAt": state["updatedAt"], "validations": state["validations"][-3:]}
    elif command == "recommend":
        return recommend_stack(workspace.load()[0])
    elif command == "preview":
        path = workspace.path / "design-preview.html"
        if args.serve:
            serve_preview(path, args.port)
        elif path.exists():
            return {"preview": str(path), "serve": "python -m appforge preview --serve"}
        else:
            raise Invalid("No preview found. Run plan first.")


def main(argv=None):
    try:
        result = execute(parser().parse_args(argv))
        if isinstance(result, int):
            return result
        if result is not None:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except KeyboardInterrupt:
        print("\nStopped. Completed discovery answers are saved; resume with wizard.", file=sys.stderr)
        return 130
    except (Invalid, OSError, json.JSONDecodeError) as error:
        print(f"AppForge: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
