# Repository agent entry point

For application-building tasks, read `START_HERE.md`, then `ai-core/master-instructions.md` and `ai-core/execution-protocol.md`. Those central files are authoritative repository guidance; do not maintain a second prompt here.

For maintenance of AppForge itself, implement the user's requested framework work directly. Do not start a new application wizard. Preserve existing source and user workspaces. Use the Python standard library for the core unless a dependency has a concrete benefit. Keep executable capabilities distinct from specifications and future roadmap items.

Run `python -m unittest discover -s tests -v` and `python scripts/check_repository.py` for core or catalog changes. For generated UI behavior changes, run `python scripts/browser_smoke.py` with the optional development dependencies installed. Never report an unexecuted check as passing.

Do not deploy, publish, send messages, spend money or upload private assets unless authorized by the user. Existing explicit authorization remains valid; avoid repeating approval requests. Multiple logical review roles can be performed by one agent. Separate agents are optional and are not required by this repository.
