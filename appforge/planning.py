import hashlib
import json
from .catalog import ROOT, blueprint
from .config import digest
from .design import contrast_report, css, preview, tokens
from .schema import Invalid
from .state import atomic, now


def source_hash():
    inputs = []
    for folder in ("appforge", "schemas", "templates", "components", "industry-blueprints", "design-engine", "design-library", "wizard", "ai-core"):
        inputs.extend(p for p in (ROOT / folder).rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    inputs.extend(ROOT / filename for filename in ("LICENSE", "GENERATED_APP_LICENSE.txt"))
    return digest({str(p.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(inputs)})


def plan_hash(config):
    return digest({"config": config, "sources": source_hash()})


def specification(config, state):
    bp = blueprint(config["project"]["category"])
    name = config["project"]["name"]
    decisions = "\n".join(f"- `{key}`: {json.dumps(answer['value'], ensure_ascii=False)} ({answer['source']})" for key, answer in state["answers"].items())
    features = "\n".join(f"- {key}: {value}" for key, value in config["features"].items())
    custom_requirements = "\n".join(f"- {group}: {item}" for group, values in config["requirements"].items() for item in values)
    workflows = "\n".join(f"- {flow}" for flow in bp["workflows"])
    criteria = "\n".join(f"- [ ] {item}" for item in bp["acceptanceCriteria"])
    stack = config["stack"]
    requirements = f"""# {name} — requirements

Audience: {config['project']['audience']}

Objective: {config['project']['objective']}

Category: {bp['name']}. Mode: {config['project']['mode']}.

## Sitemap and flows
Pages: {', '.join(bp['pages'])}. Responsive targets: {', '.join(config['project']['devices'])}.

{workflows}

## Requested features
{features}

## Custom requirements and acceptance criteria
{custom_requirements or 'No additional custom requirements recorded. Confirm the starter scope meets the user objective.'}

## Starter scope and domain work
{bp['starterScope']}

{bp['extensions']}

The executable generator produces this register workflow. The other blueprint workflows and proposed domain models are requirements for agent-assisted extension, not automatically implemented capabilities.

## Acceptance criteria
{criteria}
- [ ] Every requested domain feature has an implementation and evidence.
- [ ] Keyboard, mobile/tablet/desktop, accessibility and performance checks executed.
- [ ] Domain-specific privacy, security and deployment requirements reviewed.

## Open assumptions
- Budget {config['constraints']['monthlyBudget']} per month and {config['constraints']['expectedUsers']} expected users are planning inputs, not load-test results.
- Self-registration creates an editor account; operators provision viewer accounts using the administrator CLI.
- Records are private to their creator; administrators do not bypass record ownership.
- English interface copy is provided; other languages require translation work.
- Reference assets require a recorded visual review before reproducing a design.
"""
    architecture = f"""# {name} — architecture

Requested stack: {json.dumps(stack, indent=2)}

## Executable adapter
Vanilla HTML/CSS/JavaScript -> same-origin REST -> Python WSGI -> SQLite.
Production HTTP serving uses pinned Waitress behind HTTPS termination; the standard-library server is local development only.
No LLM provider calls, asset downloads, analytics or telemetry are performed by the core.

SQLite suits a single application instance with modest write traffic. Multiple replicas, significant write contention, SSO, payments and regulated data need a different adapter and reviewed architecture. React, Next.js, Vue, Nuxt, SvelteKit, Angular, Node.js, FastAPI, Django, Spring, Go, .NET, PostgreSQL, MySQL and MongoDB can be specified; only the documented WSGI adapter is executable in this release.

## Storage
Actual starter tables: users, sessions, records, audit_events, auth_attempts, schema_migrations.
Records have title, description, status and validated blueprint fields stored in JSON. SQL parameters are always bound.
Proposed domain-specific models for extension: {', '.join(bp['proposedModels'])}.
Migrations are versioned; back up the database before changes. Do not edit already-applied migrations.

## API
GET /api/health; GET /api/session; POST /api/register, /api/login, /api/logout.
GET/POST /api/records; PUT/DELETE /api/records/{{id}}; GET /api/activity; GET /api/export.
Owner checks apply on every record query. Viewer accounts cannot mutate records.
Session cookies are HttpOnly and SameSite=Strict; authenticated mutations require a session-bound CSRF token. Set secure cookies and the exact public origin for HTTPS deployment.

## Delivery milestones
1. Approve requirements, design concept and architecture hash.
2. Generate or incrementally update managed source files; preserve manual edits.
3. Execute schema, generated integration, UI, migration and security checks.
4. Review the twelve quality gates; deploy only after applicable gates pass.
"""
    decisions_doc = f"""# Decisions and provenance

Configuration is the source of truth. Unanswered fields remain AI-selected defaults, not explicit user approval.
Approval covers the exact configuration plus generator, schema, catalog and instruction content hashes.

{decisions or 'No discovery answers recorded yet. All values are defaults.'}

## Design
Style: {config['design']['style']}; palette: {config['design']['palette']}; theme: {config['design']['theme']}.
Background effects and advanced controls beyond the executable capability matrix remain specifications for agent implementation.
Contrast results in design-system.json measure semantic color pairs only; they do not certify complete WCAG compliance.
"""
    return requirements, architecture, decisions_doc


def create_plan(workspace):
    with workspace.lock():
        config, state = workspace._load()
        bp = blueprint(config["project"]["category"])
        requirements, architecture, decisions = specification(config, state)
        for name, content in [("requirements.md", requirements), ("architecture.md", architecture), ("decisions.md", decisions),
                              ("design-preview.html", preview(config, bp)), ("design-tokens.css", css(config))]:
            atomic(workspace.path / name, content)
        atomic(workspace.path / "design-system.json", {"light": tokens(config, "light"), "dark": tokens(config, "dark"), "contrast": contrast_report(config)})
        state.update(stage="planned", planHash=plan_hash(config), approval=None)
        workspace._commit(config, state, "Created requirements, architecture and design preview")
        return state["planHash"]


def approve(workspace, source="user"):
    def apply(config, state):
        fingerprint = plan_hash(config)
        if not state["planHash"] or state["planHash"] != fingerprint:
            raise Invalid("Plan is missing or stale. Run plan and review its files before approval.")
        state.update(stage="approved", approval={"hash": fingerprint, "at": now(), "source": source})
        return config, state
    return workspace.update(apply, "Approved exact project plan")
