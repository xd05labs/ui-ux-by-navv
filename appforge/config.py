import copy
import hashlib
import json
from .catalog import catalogs
from .schema import Invalid, validate_file

MODES = ["quick", "advanced", "autonomous", "reference", "existing", "design-only", "backend-only", "enterprise"]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def defaults(name="My Application", category="saas", mode="quick"):
    data = catalogs()
    if category not in data["blueprints"]:
        raise Invalid(f"Unknown category: {category}")
    bp = data["blueprints"][category]
    return {
        "schemaVersion": 1,
        "project": {"name": name, "category": category, "mode": mode, "language": "en",
                    "audience": bp["audience"], "objective": bp["objective"],
                    "roles": ["admin", "editor", "viewer"], "devices": ["mobile", "tablet", "desktop"]},
        "design": {"style": bp["style"], "theme": "system", "palette": bp["palette"],
                   "primaryColor": data["palettes"][bp["palette"]][2], "borderRadius": 14,
                   "density": "comfortable", "typography": "modern", "icons": "outline",
                   "motion": "smooth", "direction": "ltr", "logoPosition": "top-left",
                   "background": {"type": "gradient", "source": "", "blur": 0, "opacity": 1,
                                  "overlay": "#080E1C", "brightness": 1, "saturation": 1,
                                  "animationSpeed": 1, "position": "center"},
                   "navigation": {"type": "left-sidebar", "collapsible": True}},
        "stack": {"frontend": "vanilla", "backend": "python-wsgi", "database": "sqlite",
                  "api": "rest", "applicationType": "full-stack", "deployment": "docker",
                  "authentication": "email-password", "storage": "local"},
        "requirements": {"features": [], "workflows": [], "acceptanceCriteria": []},
        "features": {"authentication": True, "roleBasedAccess": True, "auditLog": True,
                     "search": True, "export": True, "notifications": False,
                     "realTimeUpdates": False, "multilingual": False, "payments": "none"},
        "constraints": {"privacyFirst": True, "monthlyBudget": 0, "expectedUsers": 100,
                        "experience": "beginner", "referenceAssets": [], "existingPath": ""},
        "quality": {"responsive": True, "accessibility": "WCAG 2.2 AA", "unitTesting": True,
                    "endToEndTesting": True, "securityChecks": True},
    }


def check(config):
    validate_file(config)
    data = catalogs()
    for field, choices in [("category", data["blueprints"]), ("mode", MODES)]:
        if config["project"][field] not in choices:
            raise Invalid(f"Unknown project {field}")
    for field, choices in [("style", data["styles"]), ("palette", data["palettes"])]:
        if config["design"][field] not in choices:
            raise Invalid(f"Unknown design {field}")
    if config["features"]["roleBasedAccess"] and not config["features"]["authentication"]:
        raise Invalid("Role based access requires authentication")
    if config["features"]["authentication"] and config["stack"]["authentication"] == "none":
        raise Invalid("Authentication needs an authentication method")
    return config


def set_value(config, dotted, value):
    updated = copy.deepcopy(config)
    parts = dotted.split(".")
    target = updated
    for part in parts[:-1]:
        if part not in target or not isinstance(target[part], dict):
            raise Invalid(f"Unknown configuration path: {dotted}")
        target = target[part]
    if parts[-1] not in target:
        raise Invalid(f"Unknown configuration path: {dotted}")
    target[parts[-1]] = value
    return check(updated)


def recommend_stack(config):
    """Transparent advisory rules, never a capacity guarantee or silent mutation."""
    if config["project"]["mode"] == "existing":
        return {"recommendation": "preserve-existing", "status": "agent-assisted", "reason": "Inspect the existing architecture and checks before choosing dependencies."}
    large = config["constraints"]["expectedUsers"] > 5000 or config["project"]["mode"] == "enterprise"
    ssr = config["stack"]["applicationType"] == "ssr"
    if large or ssr:
        return {"recommendation": "nextjs-postgres", "status": "agent-assisted",
                "reason": "Server rendering or larger deployment constraints warrant a reviewed PostgreSQL architecture; verify concurrency, write traffic, budget and hosting before committing."}
    return {"recommendation": "python-workspace", "status": "executable",
            "reason": "The local-first single-instance register minimizes dependencies and cost. Validate write traffic and domain requirements before deployment."}
