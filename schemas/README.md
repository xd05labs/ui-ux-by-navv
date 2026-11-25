# Configuration contracts

All five schemas use JSON Schema Draft 2020-12 and local sibling references. Project, theme, layout, features and wizard-state schemas reject unknown configuration keys. schemaVersion 1 is required. `appforge/config.py` additionally enforces catalog membership and cross-field auth rules.

The dependency-free validator supports: $ref (sibling files only), type, enum, required, properties, additionalProperties, items, minimum, maximum, minLength, maxLength, pattern, minItems, maxItems and uniqueItems. Annotation keywords are allowed; unknown assertion keywords fail closed. It is not a general-purpose implementation of every Draft 2020-12 keyword.

`python scripts/check_repository.py --jsonschema` optionally validates the same schemas/examples using the independent jsonschema package. Keep references local to avoid network resolution. New schema versions require explicit migration design; never silently discard unknown fields.
