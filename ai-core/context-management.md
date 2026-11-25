# Context and handoff

Before a model/context handoff, save typed config and wizard state, update decisions and acceptance criteria, and retain exact command outputs in the quality report or a linked evidence file. Do not copy secrets into handoffs.

Resume by reading, in order: project config, wizard state, requirements, architecture, decisions, generation manifest, latest quality report, then only the relevant source. Summarize approved decisions, unresolved assumptions, modified files, executed checks and the next concrete step. Reference catalogs by path and identifier instead of copying their entire contents.

Never reinterpret unanswered defaults as explicit user requirements. If saved approval is stale, preserve the user's preferences and renew only the affected plan. Configuration version 1 is implemented; unsupported versions fail closed and require an explicit backed-up migration. No automatic v0/v2 conversion is claimed.
