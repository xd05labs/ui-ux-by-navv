# Share one link with a software description

The entry point is the short `AI_START.md` UI/UX wizard. Users paste its link, optionally with a software brief, and the assistant should ask the first unanswered visual question. With no prior design answers, it asks “Which UI style would you like?” with lettered choices and waits. It must not lead with a repository summary, installation instructions, business workflow questions or a completed architecture. Explicit maintenance/explanation/backend-only requests keep their own scope.

## Link to share after publishing this update

Human-readable entry:

https://github.com/xd05labs/ui-ux-by-navv/blob/main/AI_START.md

Plain-text entry for an assistant:

https://raw.githubusercontent.com/xd05labs/ui-ux-by-navv/main/AI_START.md

Ready-to-copy message:

> Start the interactive UI/UX wizard from https://raw.githubusercontent.com/xd05labs/ui-ux-by-navv/main/AI_START.md. Ask me to choose a UI style first with lettered options, Auto and Custom, then wait for my answer. Keep the software description and preferences I already gave. Continue through visual choices before reviewing the design or generating code.

The existing repository root can also be shared once the updated README points to this entry. The direct entry avoids relying on an assistant to navigate a repository tree. It is a document, not an inference API or hosted builder service.

## User experience

1. The user pastes the entry link, with a software description before/after it if available. If the model cannot fetch links, they attach/paste `AI_START.md` instead. Use a fresh chat or explicitly request the updated UI/UX wizard if the assistant is carrying forward an old repository-summary response.
2. The first unanswered question is the visual style menu: Minimal, Bento, Matte glass, Apple-inspired, Material, Corporate, Futuristic, Luxury, all styles, Auto or Custom. A supplied style is retained and skipped.
3. The assistant proceeds one stage per reply: theme/palette, navigation/layout, spacing/corners, typography/icons, background, motion and branding. Auto selects only the current question; only an explicit “choose everything” request permits automatic selection of the rest. Blueprint defaults alone are not answers.
4. It shows the design summary and offers Approve, Change, or Two variations. Then it resolves remaining functional questions and proposes the architecture/implementation plan. A complete business brief does not skip unanswered visual choices.
5. When needed, it reads `AI_CONTEXT.md` for the full shared instructions, industry catalog and capability matrix. With authorized file/terminal tools it implements/tests; otherwise it emits specifications, source/patches, commands and a checkpoint, with execution pending.

The conversation can begin without cloning the repository or installing Python. Tools or a local environment are needed when actual files, previews and test results are required. A link cannot give a model capabilities or access it does not have. A model that has not read the guide must not claim it has loaded AppForge.

The narrow executable generator still produces a vanilla/Python/SQLite private register. Extra business rules, other frameworks, payments and similar requirements must be implemented by a capable agent in the generated app; they must not be dropped to force the starter generator to succeed. Cross-LLM behavior has not been certified by this document change.

## Keep one central protocol

`AI_START.md` is generated from `ai-core/uiux-discovery.md`, `wizard/uiux-flow.json` and the visual catalogs. The full shared protocol, requirements catalog and capability matrix are generated separately into `AI_CONTEXT.md`. Initial design discovery needs only the short entry; the larger file is an optional implementation reference. Neither file includes private workspace state, user briefs, environments or application data. Do not hand-edit either generated file or maintain competing instructions.

```sh
python scripts/build_ai_start.py
python scripts/build_ai_start.py --check
python scripts/check_repository.py
```

The consistency check fails if either file is missing/stale. The short entry has an 18,000-byte ceiling and full context has a 65,000-byte ceiling. These are growth guards, not a certification for every model/context window. The generated copy message includes an input-digest query parameter to request the updated entry after source changes. A link cannot force an assistant to fetch or follow a document; the explicit “start the UI/UX wizard” cue makes the requested behavior clear.

## Owner publication

Guide changes become live after publication. Use `Publish-Clean.bat`, select menu 4, and supply `https://github.com/xd05labs/ui-ux-by-navv`. Review the public target and confirm the filtered update. Publish both generated documents together with their generator/tests, UI/UX flow/protocol and updated documentation. Do not claim that an unpublished update is live.

For an owner-authorized alternative repository or simple branch/tag, regenerate with `--repo-url https://github.com/OWNER/REPOSITORY --ref BRANCH`. Those values are saved in `ai-core/entry-config.json`; subsequent refresh and integrity checks use them automatically. Update the owner-maintained README/docs links to match before publication. Never embed access tokens in URLs. Private repositories require host-specific authorized access or a user-supplied attachment.

No repository visibility change, external account setup, deployment or model-provider call is performed by the entry builder. The existing Builder license and generated-app exception remain unchanged.
