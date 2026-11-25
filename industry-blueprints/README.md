# Industry blueprints

`catalog.json` indexes 19 blueprint files. Each blueprint provides its page structure, audience/objective, navigation recommendation, style/palette, workflow list, proposed domain models, a real starter entity with field definitions/statuses, acceptance criteria and explicit extension limits.

The executable adapter generates a private operational register from that entity. It does not synthesize the complete proposed data model or all industry business rules. For example, restaurant records include date and party size, but capacity and time-slot conflict rules require an agent-assisted domain implementation. Finance records are a review queue, not a double-entry ledger. Food delivery records are dispatch administration, not real-time courier tracking.

Blueprints are customizable starting points. Add domain fields by reviewing a blueprint or a new adapter, validating the schema and executing its generated test suite. Do not use a generic register as a substitute for regulated/safety-critical workflows or specialist review. Healthcare, finance, defence and aerospace extensions are explicitly constrained in their own files.
