# CLI reference

Run from the checkout: `python -m appforge [--workspace PATH] COMMAND`. Python 3.11+ is required. The optional `pip install -e .` console entry point also expects this checkout's data files. Source-checkout execution is the supported path.

| Command | Effect |
| --- | --- |
| doctor | Local capability probes, Python/Git information, unknown host-tool flags |
| catalog blueprints/styles/palettes/stacks | Print declarative catalog JSON |
| init --name NAME --category CATEGORY --mode MODE | Create unapproved config/state; refuses existing projects |
| init ... --defaults | Initialize and record recommended discovery values |
| wizard [--defaults] | Resume unanswered relevant questions; save after each |
| set DOTTED.PATH VALUE | Set a schema-valid value and invalidate approval |
| import FILE | Replace config with complete valid JSON and mark values imported |
| plan | Write requirements, architecture, decisions, tokens and preview; record hash |
| preview [--serve --port 4173] | Print preview path or serve just the preview on loopback |
| approve --yes | Record exact-plan review approval |
| generate --dry-run | Report changed/removed/conflicting managed paths |
| generate | Generate approved files; refuse edited/unmanaged collisions |
| validate | Execute checks and persist quality-report.json; nonzero if checks fail |
| status | Print stage, answered count, approval currency and recent validation refs |
| recommend | Explain a stack recommendation without changing the selected configuration |
| undo | Restore prior config checkpoint; preserve generated source/data |
| recover-generation | Roll back a verified interrupted generation journal |

Values are parsed as JSON when possible; otherwise they are strings. Booleans use true/false. Quote JSON arrays correctly for your shell. A category or palette change through `set` changes only that field; set related style/primary values deliberately or use the discovery wizard's recommendations.

Examples:

```sh
python -m appforge --workspace projects/shop init --name Shop --category ecommerce
python -m appforge --workspace projects/shop wizard
python -m appforge --workspace projects/shop set design.theme dark
python -m appforge --workspace projects/shop set design.borderRadius 12
python -m appforge --workspace projects/shop plan
```

Exit codes: 0 success, 1 executed validation failure, 2 invalid command/configuration or filesystem error, 130 interrupted. Ctrl+C retains completed discovery answers. Preview servers stay local and do not expose other workspace files.
