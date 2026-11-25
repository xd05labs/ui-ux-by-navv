# Start here

For users pasting a link into an AI assistant, start with the short [AI_START.md](AI_START.md) UI/UX wizard. Ask the first unanswered visual question; by default show the lettered style choices and wait for a selection. Preserve preferences already given. Do not summarize the repository or jump to architecture. The file can be attached/pasted when URL access is unavailable. Full shared instructions/catalogs are in [AI_CONTEXT.md](AI_CONTEXT.md), to read when needed without bypassing design review.

If you are maintaining this framework, follow the user's requested change and run the relevant repository checks. The discovery workflow below is for building an application with AppForge.

1. Read [master instructions](ai-core/master-instructions.md), [execution protocol](ai-core/execution-protocol.md) and [capabilities](docs/capabilities.md).
2. Determine the host's actual read/write/terminal/image/browser/network tools. `python -m appforge doctor` probes local file and terminal access, not an LLM's tools.
3. Look for `workspace/project.config.json` and `wizard-state.json`, or the user's selected workspace. Resume saved decisions. Never initialize over an existing project.
4. For a new application-design conversation, show the first unanswered UI/UX menu with its labeled visual comparison image, direct preview link and concrete recommended, automatic and custom choices. If images cannot render in the host, say so and retain the clickable preview. Offer operating modes when relevant, without requiring mode selection before visual discovery. Respect explicit backend-only scope.
5. Save answers immediately with provenance. Resolve enough requirements before writing application code. Generate a plan and design preview; honor approval already granted in the conversation.
6. Implement the approved scope, execute available checks, record evidence and report remaining gates honestly.

For a terminal-only start, follow the commands in [README.md](README.md). For a text-only host, copy [master-instructions.md](ai-core/master-instructions.md) into the conversation and provide the relevant catalogs and saved state. Emit complete file contents or patches and a compact checkpoint for the user to save; mark every unexecuted check as pending.
