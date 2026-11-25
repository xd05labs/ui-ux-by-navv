# Contributing

The Builder uses the restricted license in LICENSE. External modifications or distribution of Builder patches require the rights holder's prior written permission; bug reports and feature suggestions are welcome. Repository-owner-authorized maintenance remains permitted. Generated applications have their own explicit customization/redistribution grant. Third-party contributions must have documented rights and permissions before acceptance; this file does not assign ownership or override other licenses.

Use Python 3.11+ from the repository checkout. No core dependencies are required. Optional browser/standards tools are pinned in requirements-dev.txt. See README for verification commands.

Keep catalogs declarative and central instructions shared across host entry files. Extend closed schemas before adding fields; extend the dependency-free validator if you introduce an unsupported assertion keyword. Preserve unknown-version rejection. Add an executable adapter only when it includes source, migration behavior, environment examples, documentation and meaningful tests.

Changes to generator behavior need regression coverage for real failure modes, not snapshots that merely copy the implementation. Verify generated applications, ownership, role boundaries, malformed input and preservation of manual edits. UI behavior changes need the optional browser smoke check and visual inspection. Never mark a release gate passed solely because a template file exists.

Do not commit workspaces, test databases, credentials, downloaded media or virtual environments. State limitations in capabilities.md and CHANGELOG.md. Keep future features out of executable support claims. Use the pull request template to state the concrete behavior and actual validation.
