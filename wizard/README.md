# Adaptive wizard

`questions.json` is the declarative source. A question has path, label, help and optionally choices/catalog, modes, excludeModes and equality conditions under when. Paths refer to typed project configuration. Relevance is recomputed after every answer; answered paths are skipped on resume. Each answer is committed immediately with value, provenance and timestamp.

Every CLI question accepts Enter for the recommendation, auto for automatic selection, or custom input. Lists, numbers and booleans use JSON; strings may be entered directly. An agent may improve recommendations based on context but must save its choice and reason. Quick mode asks essentials; advanced modes expose more choices. Unsupported requested functionality remains in the specification and causes a clear generation rejection.

Discovery covers category/name/objective/audience/devices, design, branding/reference assets, backgrounds, colors, typography, navigation/components, motion, features, database, authentication and deployment. The master protocol adds conversational questions only when the user's requirements need them. The CLI is a deterministic baseline, not a claim to dynamically infer every possible business question.
