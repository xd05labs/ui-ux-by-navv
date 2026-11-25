# Capability matrix — v0.1

“Executable” means the shipped code performs the behavior. “Agent-assisted” means the repository provides guidance and configuration, but a capable agent must implement and test it. A specification is not an implementation. No automatic calls to model providers are shipped.

| Area | Executable | Agent-assisted or future |
| --- | --- | --- |
| Discovery | 39 adaptive questions; recommended/automatic/custom values; conditions; provenance; resume; custom requirements retained | Rich graphical wizard; arbitrarily generated follow-up questions |
| Modes | Quick/advanced/autonomous share discovery; design-only static concept; backend-only API | Reference asset analysis; existing-project editing; enterprise-specific infrastructure |
| Catalogs | 19 blueprint field/workflow definitions; 20 token recipes; eight palettes | Complete domain applications, marketplace catalogs |
| Design | Radius, density, typography families, semantic colors, light/dark/system, RTL, background patterns | Hybrid style editor, logo placement, custom fonts/SVG icons, faithful OS-specific widgets |
| Navigation | Left/right/top/bottom/floating/centered/Bento arrangements; sidebar collapse; command palette; mobile wrapping | True dual-sidebar workspace, nested menus, drag resizing, floating toolbars, multi-panel workspaces |
| Backgrounds | Solid, gradient, mesh and CSS-rendered dot-pattern recipes | Image/video upload, SVG asset sanitization, particles, 3D, procedural textures, asset blur/overlay/brightness/saturation/speed controls |
| Components | Shared buttons, inputs, selects, textareas, cards, tables, badges, meters, dialogs, toasts, loading/empty/error/offline/auth states | Full component gallery, calendars, Kanban, drag-and-drop, advanced charts/date pickers |
| Frontend/backend | Vanilla JS + Python WSGI + SQLite + REST | React/Next/Vue/Nuxt/SvelteKit/Angular, Node/FastAPI/Django/Spring/Go/.NET, GraphQL/WebSocket, PostgreSQL/MySQL/MongoDB |
| Accounts | Email/password, scrypt, session expiry/revocation, CSRF, same-origin checks, registration switch, operator provisioning | Email verification, recovery, OTP, OAuth, SSO, passkeys, organizational membership |
| Records | Owner-scoped CRUD, blueprint fields, 500-result search/filter, full CSV export, audit history, role write checks | Domain transactions, shared organizations, arbitrary user-defined entities |
| Integrations | Contracts and explicit generation rejection for requested unavailable features | Payments, cloud storage, uploads, notifications, analytics, realtime collaboration, LLM APIs |
| Delivery | Dockerfile, Compose, pinned Waitress, migration runner, environment examples, docs | Automated deployment, cloud provisioning, distributed database management |
| State | Journaled config/state, snapshots, source/config approval hash, managed collision checks, interrupted generation rollback | Automatic schema upgrades, code undo, automatic three-way merge |
| Quality | Unit and WSGI integration tests; browser smoke harness; semantic contrast; current-plan/hash checks; twelve gates | Complete WCAG audit, Lighthouse baseline, penetration testing, image/asset optimization, multi-provider measured benchmarks |

Some config fields intentionally describe agent-assisted design choices. The renderer applies only the executable controls above. The dual-sidebar choice currently uses the main sidebar arrangement with additional spacing; it is a layout specification, not a second functional panel. Media/integrations and unsupported technology choices cause the full-stack generator to fail with an explanation rather than silently pretending they work. Reference mode's asset list is not proof of analysis; the agent must record actual visual review.

Autonomous mode still needs bounded authorization and an exact plan. Enterprise mode does not add SSO, compliance or infrastructure by changing a label. Blueprints produce an operational register; read each blueprint's extension notes before describing its domain completeness.

`quality-report.json` always starts with productionReady=false. Passing checks certify only their stated scope. Full release sign-off remains a project-specific review of all applicable gates.
