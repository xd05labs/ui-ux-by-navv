"""Run the generated integration suite for every industry blueprint."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from appforge.catalog import catalogs
from appforge.config import defaults
from appforge.generator import render
from appforge.state import atomic, now


def main():
    report = {"at": now(), "runs": [], "passed": True}
    for category in catalogs()["blueprints"]:
        with tempfile.TemporaryDirectory(prefix="appforge-blueprint-") as temp:
            output = Path(temp)
            for relative, data in render(defaults(category=category)).items():
                target = output / relative; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
            started = time.monotonic()
            result = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], cwd=output, capture_output=True, text=True, timeout=60)
            passed = result.returncode == 0
            report["runs"].append({"category": category, "passed": passed, "seconds": round(time.monotonic()-started, 3), "output": result.stdout + result.stderr})
            report["passed"] &= passed
            print(category + ": " + ("passed" if passed else "FAILED"), flush=True)
    path = ROOT / "artifacts" / "blueprint-report.json"
    atomic(path, report)
    print(json.dumps({"passed": report["passed"], "categories": len(report["runs"]), "report": str(path)}, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
