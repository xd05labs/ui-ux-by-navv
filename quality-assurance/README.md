# Quality assurance

The release has twelve gates in `release-gates.json`. Automated checks never convert missing evidence into a passing gate. `appforge validate` records exact commands, duration, status and output, plus schema, source/config currency, managed-file consistency and measured semantic contrast.

Repository tests cover closed schemas, all blueprint renders, all palettes, adaptive resume, provenance, journals, locks, undo, approval invalidation, idempotence, conflicts, traversal and generation recovery. Every generated full-stack app includes a separate WSGI/SQLite integration suite for migrations, sessions, auth limits, ownership, roles, CSRF, input bounds, CRUD, search, export and static-file security.

`scripts/browser_smoke.py` provides actual Chromium registration/login, CRUD, search, export, audit history, theme controls, keyboard dialog checks and 1440/768/390 viewport overflow checks. Screenshots need visual inspection. This is not a complete WCAG audit, visual regression baseline, penetration test, load test or Lighthouse measurement.

For release, add project-specific feature acceptance, keyboard/screen-reader/zoom/contrast checks, frontend/backend network tests, migration/restore drills, secret/dependency scans and reproducible performance measurements. Record unavailable tools and pending checks. Never infer a test ran from a checklist item.
