"""Refresh/check the shareable AI entry. Reads public instructions/catalogs only."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from appforge.ai_entry import build_ai_start, entry_config, repository_url
from appforge.state import atomic


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Fail if the committed entry is missing or stale; never rewrite it")
    parser.add_argument("--repo-url", help="Owner-authorized repository URL; saved in ai-core/entry-config.json")
    parser.add_argument("--ref", help="Owner-authorized simple branch/tag; saved in ai-core/entry-config.json")
    args = parser.parse_args()
    content = build_ai_start(repository=args.repo_url, ref=args.ref)
    path = ROOT / "AI_START.md"
    if args.check:
        if not path.exists() or path.read_text(encoding="utf-8") != content:
            print("AI_START.md is stale or missing. Run python scripts/build_ai_start.py", file=sys.stderr)
            return 1
        print("AI_START.md matches the current central instructions and catalogs.")
    else:
        if args.repo_url is not None or args.ref is not None:
            configured = entry_config()
            configured["repository"] = repository_url(args.repo_url) if args.repo_url is not None else configured["repository"]
            configured["ref"] = args.ref if args.ref is not None else configured["ref"]
            # The render above validated the proposed values before this write.
            atomic(ROOT / "ai-core/entry-config.json", configured)
            content = build_ai_start()
        atomic(path, content)
        print(f"Wrote {path} ({len(content.encode('utf-8')):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
