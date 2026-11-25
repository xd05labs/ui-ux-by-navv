# Executed verification — 2026-11-25

## Link-first AI entry

The single-file entry update passed `python -m unittest discover -s tests -v`: **49 tests**, including nine entry-pack tests. Repository integrity, generated-entry consistency, local Markdown links and the offline publisher preview passed. The preview selected 129 files and included AI_START.md and its supporting code/configuration.

Entry tests cover embedded central instructions, current catalog/question coverage, exclusion of private workspace/environment content, source changes, LF/CRLF stability, source-path restrictions, credential-free URL configuration, context-size limits and read-only checks. These are document/generator checks; they do not certify behavior across arbitrary LLMs. No generated application UI changed, and the prior browser run was not repeated for this entry update.

## Numbered publisher menu and terminal setup

The menu/setup update passed `python -m unittest discover -s tests -v`: **40 tests** (27 core and 13 Windows publisher tests). Repository integrity checks and the checkout's offline BAT dry run also passed. The actual BAT entry was exercised with menu input, including help and exit. Tests covered menu routing, invalid options, error recovery, installation cancellation, strict offline behavior, WinGet bootstrap selection, installation failures, same-session discovery/PATH refresh and terminal process output/exit codes. Existing filtered-snapshot and local-remote publish tests continued to pass.

Installer/package-manager calls were simulated for setup tests; no real package download/installation or live GitHub publishing was performed. Actual terminal process streaming was verified with a local Python subprocess. Scoped evidence is in `artifacts/menu-publisher-verification.json`. No generated application UI changed, so browser checks were not repeated for this update.

## Licensing and publisher update

After the initial foundation run below, the licensing/publisher change passed `python -m unittest discover -s tests -v`: **33 tests** (27 core and six Windows publisher tests), including the generated WSGI suite exercised by the core tests. `python scripts/check_repository.py` passed. `Publish-Clean.bat --dry-run` passed on this checkout and selected 123 files without authentication, repository creation or push.

Publisher tests used real Git operations with local bare remotes and offline account/API fixtures. They verified new-repository preparation, existing-repository updates, cancellation, source history/index preservation, tracked-ignore filtering, credential blocking, link validation, native quoting and remote-tip artifact removal. No live GitHub action was tested; GitHub CLI is not installed here. Generated UI behavior was not changed, so the prior browser run was not repeated for this licensing/script change. Scoped evidence is recorded in `artifacts/licensing-publisher-verification.json`; the initial consolidated report below predates this change and its source hash describes that earlier revision.

## Initial foundation run

The consolidated local run completed successfully on Windows with Python 3.11.6. These are observed results for this implementation, separate from the proposed release benchmarks.

| Check | Actual result |
| --- | --- |
| Framework regression suite | 26 tests passed |
| Generated application integration suites | 14 tests × 19 industry blueprints = 266 passing test executions |
| Repository integrity | 19 blueprints, 20 styles, eight palettes, five schemas and 23 configurations checked |
| Independent JSON Schema validation | Draft 2020-12 schemas and configurations passed with jsonschema 4.26.0 |
| Chromium browser suite | 12 scenarios passed using Playwright 1.65.2 |
| Defined viewport overflow | No page-level horizontal overflow at 1440×1000, 768×1024 and 390×844 |
| Generated JavaScript syntax | `node --check templates/python-workspace/static/app.js` passed |
| Local Markdown links | No missing local link targets in the checked documentation |

The Chromium suite executed real local HTTP requests for registration, sessions, creation, editing, search/empty state, CSV download, keyboard command palette, responsive layouts, theme changes, activity history, deletion, logout/login and offline design configuration controls. Desktop/mobile screenshots were inspected visually. Token contrast checks covered the measured semantic pairs; they do not certify complete WCAG compliance.

The test cycle caught and repaired Windows database connection cleanup, form label ambiguity, a registration-mode state leak after logout and a CSS background override. The final consolidated run passed after these corrections.

Reproduce from the checkout after installing requirements-dev.txt and Chromium:

```sh
python scripts/verify.py --full
```

Machine-readable command output, exit codes, timings, environment and generator-source hash are in `artifacts/verification-report.json`. Per-blueprint results are in `artifacts/blueprint-report.json`; the consolidated report names the browser artifact directory. All test data is synthetic. Test servers stop at the end of the harness.

Not executed here: Docker/Compose builds, public deployment, backup/restore drills, Lighthouse, load tests, a complete accessibility audit, dependency/penetration audits, other operating systems/Python versions, or cross-LLM compatibility trials. Docker is unavailable in this environment. CI workflows are configured but have not been run on a hosted runner. No production-readiness or proposed benchmark-target claim is made.

Tooling references consulted: [Python development HTTP server limitations](https://docs.python.org/3.11/library/http.server.html), [Waitress deployment/proxy documentation](https://docs.pylonsproject.org/projects/waitress/en/latest/reverse-proxy.html), [Waitress 3.0.2 package](https://pypi.org/project/waitress/3.0.2/), and official [checkout](https://github.com/actions/checkout), [setup-python](https://github.com/actions/setup-python) and [artifact upload](https://github.com/actions/upload-artifact) documentation. The workflow uses the documented v7 action entry points; hosted execution remains pending.
