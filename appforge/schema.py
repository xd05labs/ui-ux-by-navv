"""Dependency-free validation of the JSON Schema subset used by this repository.

External tools can use any Draft 2020-12 validator. Unknown assertion keywords
fail closed here, so extending schemas also requires extending this validator.
"""
import json
import re
from .catalog import ROOT


class Invalid(ValueError):
    pass


ANNOTATIONS = {"$schema", "$id", "title", "description", "default", "examples"}
KEYWORDS = {"$ref", "type", "enum", "required", "properties", "additionalProperties",
            "items", "minimum", "maximum", "minLength", "maxLength", "pattern",
            "minItems", "maxItems", "uniqueItems"} | ANNOTATIONS


def validate(value, schema, path="$", depth=0):
    if depth > 50:
        raise Invalid(f"{path}: schema recursion limit")
    unknown = set(schema) - KEYWORDS
    if unknown:
        raise Invalid(f"{path}: unsupported schema keywords: {sorted(unknown)}")
    if "$ref" in schema:
        ref = (ROOT / "schemas" / schema["$ref"]).resolve()
        if ref.parent != (ROOT / "schemas").resolve():
            raise Invalid("Only sibling schema references are supported")
        validate(value, json.loads(ref.read_text(encoding="utf-8")), path, depth + 1)
    types = {"object": lambda x: isinstance(x, dict), "array": lambda x: isinstance(x, list),
             "string": lambda x: isinstance(x, str), "boolean": lambda x: type(x) is bool,
             "integer": lambda x: type(x) is int,
             "number": lambda x: type(x) in (int, float), "null": lambda x: x is None}
    if "type" in schema:
        allowed = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(types[t](value) for t in allowed):
            raise Invalid(f"{path}: expected {' or '.join(allowed)}")
    if "enum" in schema and value not in schema["enum"]:
        raise Invalid(f"{path}: choose one of {schema['enum']}")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                raise Invalid(f"{path}.{key}: required")
        props = schema.get("properties", {})
        for key, item in value.items():
            if key in props:
                validate(item, props[key], f"{path}.{key}", depth + 1)
            elif schema.get("additionalProperties") is False:
                raise Invalid(f"{path}.{key}: unknown property")
            elif isinstance(schema.get("additionalProperties"), dict):
                validate(item, schema["additionalProperties"], f"{path}.{key}", depth + 1)
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0) or len(value) > schema.get("maxItems", float("inf")):
            raise Invalid(f"{path}: incorrect array length")
        if schema.get("uniqueItems") and len({json.dumps(v, sort_keys=True) for v in value}) != len(value):
            raise Invalid(f"{path}: duplicate items")
        for i, item in enumerate(value):
            if "items" in schema:
                validate(item, schema["items"], f"{path}[{i}]", depth + 1)
    if isinstance(value, str):
        if not schema.get("minLength", 0) <= len(value) <= schema.get("maxLength", float("inf")):
            raise Invalid(f"{path}: incorrect string length")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            raise Invalid(f"{path}: invalid format")
    if type(value) in (int, float):
        import math
        if not math.isfinite(value):
            raise Invalid(f"{path}: must be finite")
        if value < schema.get("minimum", -float("inf")) or value > schema.get("maximum", float("inf")):
            raise Invalid(f"{path}: outside permitted range")


def validate_file(value, filename="project.schema.json"):
    validate(value, json.loads((ROOT / "schemas" / filename).read_text(encoding="utf-8")))
