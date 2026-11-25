# Start here

For users pasting a link into an AI assistant, start with [AI_START.md](AI_START.md). It contains the shared instructions, description-first entry behavior and catalog summaries in one file, and can also be attached or pasted when URL access is unavailable. Use the user's software description and known choices before asking any discovery questions. The full local workflow below applies when repository/terminal tools are available.

If you are maintaining this framework, follow the user's requested change and run the relevant repository checks. The discovery workflow below is for building an application with AppForge.

1. Read [master instructions](ai-core/master-instructions.md), [execution protocol](ai-core/execution-protocol.md) and [capabilities](docs/capabilities.md).
2. Determine the host's actual read/write/terminal/image/browser/network tools. `python -m appforge doctor` probes local file and terminal access, not an LLM's tools.
3. Look for `workspace/project.config.json` and `wizard-state.json`, or the user's selected workspace. Resume saved decisions. Never initialize over an existing project.
4. For a new project, offer quick, advanced, autonomous, reference, existing, design-only, backend-only or enterprise mode. Ask the first small set of discovery questions with recommended, automatic and custom choices.
5. Save answers immediately with provenance. Resolve enough requirements before writing application code. Generate a plan and design preview; honor approval already granted in the conversation.
6. Implement the approved scope, execute available checks, record evidence and report remaining gates honestly.

For a terminal-only start, follow the commands in [README.md](README.md). For a text-only host, copy [master-instructions.md](ai-core/master-instructions.md) into the conversation and provide the relevant catalogs and saved state. Emit complete file contents or patches and a compact checkpoint for the user to save; mark every unexecuted check as pending.
