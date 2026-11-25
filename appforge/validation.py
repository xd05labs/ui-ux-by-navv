import json
import re
import subprocess
import sys
import time
from pathlib import Path
from .config import check
from .design import contrast_report
from .generator import changes, load_manifest, sha
from .planning import plan_hash
from .schema import Invalid
from .state import atomic, now

GATES = ["Required features implemented", "Navigation and controls", "Application builds", "Responsive viewports",
         "Accessibility and keyboard", "Frontend/backend integration", "Database migrations", "Authentication and authorization",
         "Secrets excluded", "Dependency and security review", "Performance benchmarks", "Installation and deployment docs"]


def run_command(command, cwd):
    started = time.monotonic()
    try:
        result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=120)
        return {"command": command, "exitCode": result.returncode, "durationSeconds": round(time.monotonic() - started, 3),
                "output": (result.stdout + result.stderr)[-30000:], "passed": result.returncode == 0}
    except subprocess.TimeoutExpired:
        return {"command": command, "exitCode": None, "durationSeconds": 120, "output": "Timed out", "passed": False}


def validate_project(workspace):
    with workspace.lock():
        config, state = workspace._load()
        check(config)
        output = workspace.path / "generated-app"
        manifest = load_manifest(workspace)
        if not manifest["files"]:
            raise Invalid("No generated application to validate")
        commands = []
        design_only = config["project"]["mode"] == "design-only"
        if not design_only:
            commands.append(run_command([sys.executable, "-m", "compileall", "-q", "."], output))
            commands.append(run_command([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], output))
            match = re.search(r"Ran (\d+) tests?", commands[-1]["output"])
            commands[-1]["testsRun"] = int(match[1]) if match else 0
            commands[-1]["passed"] = commands[-1]["passed"] and commands[-1]["testsRun"] >= 14
        pairs = contrast_report(config)
        contrast_passed = all(item["passed"] for mode in pairs.values() for item in mode)
        # Never let a passing test run bless a stale or manually changed generated app.
        from .generator import safe_target
        files_match = all(safe_target(output, key).is_file() and sha(safe_target(output, key).read_bytes()) == value for key, value in manifest["files"].items())
        current = manifest.get("planHash") == plan_hash(config)
        passed = all(command["passed"] for command in commands) and contrast_passed and files_match and current
        gates = [{"name": gate, "status": "pending", "evidence": "Requires project-specific executed evidence."} for gate in GATES]
        if commands:
            gates[2].update(status="passed" if commands[0]["passed"] else "failed", evidence="Python compilation command in this report.")
            for i in (6, 7):
                gates[i].update(status="passed" if commands[1]["passed"] else "failed", evidence="Generated WSGI integration suite in this report; applies only to the starter scope.")
        gates[11].update(status="pending", evidence="Setup, API and deployment instructions generated; operator must execute deployment and restore drills.")
        report = {"schemaVersion": 1, "at": now(), "checksPassed": passed, "productionReady": False,
                  "configSchema": "passed", "currentPlan": current, "managedFilesMatch": files_match,
                  "contrast": pairs, "commands": commands, "gates": gates,
                  "notes": ["Semantic color contrast checks do not certify WCAG compliance.", "WSGI integration tests do not replace browser or network end-to-end tests.",
                            "No security audit, Lighthouse score, Docker build or load-test claim is implied."]}
        atomic(workspace.path / "quality-report.json", report)
        state["validations"].append({"at": report["at"], "report": "quality-report.json", "passed": passed})
        state["stage"] = "validated" if passed else "generated"
        workspace._commit(config, state, "Executed validation checks: " + ("passed" if passed else "failed"))
        return report
