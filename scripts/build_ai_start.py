"""Refresh/check the short UI/UX entry and full context from reviewed sources."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from appforge.ai_entry import build_ai_documents, entry_config, repository_url
from appforge.state import atomic


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Fail if the committed entry is missing or stale; never rewrite it")
    parser.add_argument("--repo-url", help="Owner-authorized repository URL; saved in ai-core/entry-config.json")
    parser.add_argument("--ref", help="Owner-authorized simple branch/tag; saved in ai-core/entry-config.json")
    args = parser.parse_args()
    documents = build_ai_documents(repository=args.repo_url, ref=args.ref)
    if args.check:
        stale = [name for name, content in documents.items() if not (ROOT / name).exists() or (ROOT / name).read_text(encoding="utf-8") != content]
        if stale:
            print(", ".join(stale) + " is stale or missing. Run python scripts/build_ai_start.py", file=sys.stderr)
            return 1
        print("AI_START.md and AI_CONTEXT.md match the current UI/UX flow, central instructions and catalogs.")
    else:
        if args.repo_url is not None or args.ref is not None:
            configured = entry_config()
            configured["repository"] = repository_url(args.repo_url) if args.repo_url is not None else configured["repository"]
            configured["ref"] = args.ref if args.ref is not None else configured["ref"]
            # The render above validated the proposed values before this write.
            atomic(ROOT / "ai-core/entry-config.json", configured)
            documents = build_ai_documents()
        for name, content in documents.items():
            path = ROOT / name
            atomic(path, content)
            print(f"Wrote {path} ({len(content.encode('utf-8')):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
