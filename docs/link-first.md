# Share one link with a software description

The entry point is `AI_START.md`. Users can write their software requirements first, then paste its link and ask the assistant to use AppForge. They can also put their description after the link. The assistant is instructed to extract the supplied structure, features, roles, pages, workflows, design and stack choices, summarize what is known and ask only missing questions in groups of at most three.

## Link to share after publishing this update

Human-readable entry:

https://github.com/xd05labs/ui-ux-by-navv/blob/main/AI_START.md

Plain-text entry for an assistant:

https://raw.githubusercontent.com/xd05labs/ui-ux-by-navv/main/AI_START.md

Ready-to-copy message:

> Use AppForge from https://raw.githubusercontent.com/xd05labs/ui-ux-by-navv/main/AI_START.md. My software description is above. Use those requirements, ask only missing questions, and show the proposed design and architecture before implementation.

The existing repository root can also be shared once the updated README points to this entry. The direct entry avoids relying on an assistant to navigate a repository tree. It is a document, not an inference API or hosted builder service.

## User experience

1. The user describes their software in ordinary language, optionally including a file tree, screenshot or preferred stack.
2. They paste the entry link and ask the assistant to use it. If the model cannot fetch links, they attach/paste `AI_START.md` instead.
3. The assistant summarizes known requirements and asks only unanswered decisions, with recommended/automatic/custom choices.
4. It proposes requirements, sitemap/flows, a design concept, architecture and acceptance criteria for review.
5. With authorized file/terminal tools it implements and tests the application. Otherwise it supplies specifications, code/patches, commands and a resumable checkpoint in chat; execution remains pending.

The conversation can begin without cloning the repository or installing Python. Tools or a local environment are needed when actual files, previews and test results are required. A link cannot give a model capabilities or access it does not have. A model that has not read the guide must not claim it has loaded AppForge.

The narrow executable generator still produces a vanilla/Python/SQLite private register. Extra business rules, other frameworks, payments and similar requirements must be implemented by a capable agent in the generated app; they must not be dropped to force the starter generator to succeed. Cross-LLM behavior has not been certified by this document change.

## Keep one central protocol

`AI_START.md` is generated from the central AI protocol, declared capability matrix, wizard rules and catalogs. It embeds those shared instructions and concise catalog summaries so text-only users need only one attachment. It excludes workspace state, user briefs, environment files, credentials and generated application data. Do not hand-edit the generated file or maintain a second competing master prompt.

```sh
python scripts/build_ai_start.py
python scripts/build_ai_start.py --check
python scripts/check_repository.py
```

The consistency check fails on a missing/stale entry. A 65,000-byte size ceiling keeps accidental growth visible; it is not a guarantee that every model's context window can fit the file. Capability checks and clear partial-content handling still apply.

## Owner publication

The new link becomes usable only after the entry and related source updates are published. Use `Publish-Clean.bat`, select menu 4, and supply `https://github.com/xd05labs/ui-ux-by-navv`. Review the public target and confirm the filtered update. Publish the full coherent change: the generated entry, its generator/tests, central instruction updates, README and documentation. Do not claim that an unpublished URL is already live.

For an owner-authorized alternative repository or simple branch/tag, regenerate with `--repo-url https://github.com/OWNER/REPOSITORY --ref BRANCH`. Those values are saved in `ai-core/entry-config.json`; subsequent refresh and integrity checks use them automatically. Update the owner-maintained README/docs links to match before publication. Never embed access tokens in URLs. Private repositories require host-specific authorized access or a user-supplied attachment.

No repository visibility change, external account setup, deployment or model-provider call is performed by the entry builder. The existing Builder license and generated-app exception remain unchanged.
