# Generator architecture and extension workflow

The executable implementation is `appforge/generator.py`, using `templates/python-workspace/`. Requirements, architecture and design generation live in `appforge/planning.py` and `appforge/design.py`; they do not depend on a model API.

To add an executable adapter:

1. Define its exact supported stack, feature subset and input schema. Reject unsupported combinations clearly.
2. Implement pure rendering as a map of relative filenames to bytes. Escape configuration according to HTML/JSON/source context; never interpolate secrets.
3. Include frontend/backend/API contracts, database migrations, auth boundaries, dependency pins, environment examples, tests and delivery docs.
4. Pass generated files through the existing safe-target, change-impact and collision workflow. Never overwrite manually edited source.
5. Execute generated tests against a clean workspace and include meaningful security, migration and UI cases.
6. Update the stack registry and capability matrix only after behavior is implemented and verified.

For an agent-assisted stack, first generate the specification and architecture, inspect current official dependency documentation, implement modular source, run its real framework checks and persist evidence. Do not label a stack executable based only on a plan or empty template directory.
