import argparse
import json
from pathlib import Path
import platform
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from appforge.config import digest
from appforge.planning import source_hash
from appforge.state import Workspace, atomic, now
from appforge.validation import validate_project


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=ROOT / "workspace")
    parser.add_argument("--provider", required=True)
    parser.add_argument("--elapsed-seconds", type=float, required=True)
    parser.add_argument("--tokens", type=int)
    args = parser.parse_args()
    if args.elapsed_seconds < 0 or (args.tokens is not None and args.tokens < 0):
        parser.error("Measurements must be nonnegative")
    workspace = Workspace(args.workspace)
    config, _ = workspace.load()
    report = validate_project(workspace)
    result = {"at": now(), "providerLabel": args.provider, "providerVerified": False,
              "reportedElapsedSeconds": args.elapsed_seconds, "reportedTokens": args.tokens,
              "measurementSource": "caller-supplied host accounting; not independently verified",
              "environment": {"python": platform.python_version(), "os": platform.platform()},
              "configHash": digest(config), "sourceHash": source_hash(), "validation": report,
              "firstGenerationBuildSuccess": None, "featureCompletion": None, "lighthouse": None}
    output = ROOT / "artifacts" / "benchmarks" / (uuid4().hex + ".json")
    atomic(output, result)
    print(json.dumps({"record": str(output), "checksPassed": report["checksPassed"]}, indent=2))
    return 0 if report["checksPassed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
