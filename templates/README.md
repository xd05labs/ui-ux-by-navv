# Templates and stack registry

`python-workspace/` is an executable standalone WSGI/SQLite adapter. `stacks.json` separates executable, agent-assisted and specification-only stacks. The generator renders the actual template bytes, adds public app configuration and shared design CSS, then records managed hashes.

Each generated application owns its migrations, environment and test suite. It does not depend on the parent repository at runtime. Waitress is the only optional deployment dependency; local development and tests use the standard library. Docker is an optional operator path, not a requirement for discovery or generation.
