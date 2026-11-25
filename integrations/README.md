# Integration contracts

No cloud or LLM integration is invoked by the core. The configuration can describe these needs; the executable adapter rejects requested unavailable integrations. A capable agent must implement and verify them before marking the feature complete.

| Integration | Required behavior before release |
| --- | --- |
| LLM adapters | Explicit provider/model/cost limits, environment secrets, timeouts, retries, cancellation, redaction, prompt-injection boundaries and token accounting |
| Payments | Server-created payment intent/order, signed webhook verification, idempotency, amount/currency checks, refunds, replay/failure tests and reconciliation |
| Storage | Private access by default, owner checks, safe filenames, file size/type validation, malware/sanitization workflow, signed URL expiry, retention and deletion |
| Notifications | User consent/preferences, durable delivery state, retries, deduplication, unsubscribe and sensitive-content policy |
| Analytics | Consent where required, event schema, data minimization, retention and access controls |

Never put a provider secret in browser configuration. Use synthetic fixtures and provider sandboxes. Do not mark a payment, notification or upload button complete until its backend behavior and failure path actually work.
