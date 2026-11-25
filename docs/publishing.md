# Reusable Windows GitHub publisher

Copy **[Publish-Clean.bat](../Publish-Clean.bat)** into a project's root and double-click it. This single file needs no companion script, Python or AppForge installation. It runs in Windows PowerShell 5.1. Its setup menu detects missing Git and [GitHub CLI](https://cli.github.com/) and downloads/installs them in the terminal; no manual installer download is required. The script uses normal CLI authentication, not a hardcoded token.

## Numbered menu

| Option | Action |
| --- | --- |
| 1 | Check, download and install missing requirements |
| 2 | Preview clean project files without uploading |
| 3 | Create/find a repository on your account and publish |
| 4 | Publish to an existing GitHub repository link |
| 5 | GitHub sign-in and account status |
| 6 | View the last file-selection report |
| 7 | Help |
| 0 | Exit |

Actions return to the menu. Invalid selections and action failures leave the menu usable. Choose setup first on a new machine, then preview, then create/publish. Repository names and URLs remain text inputs; action, visibility, installation and final-publish choices use numbered menus.

## Terminal downloads

Missing dependencies are shown by name before installation. Select 1 at the installation menu to accept package/source agreements and download only the missing tools from WinGet's explicit package IDs Git.Git and GitHub.cli. Progress stays in the terminal; executable discovery and PATH are refreshed so you can continue in the same session. Installation failures or tools that remain unavailable stop the action and return to the menu. Already-detected tools are not reinstalled.

If WinGet itself is missing, a separate numbered choice offers Microsoft's terminal bootstrap: install the current-user Microsoft.WinGet.Client module from PowerShell Gallery and run Repair-WinGetPackageManager. Windows/package-management policy may block installation, and some installers require an OS elevation prompt or restart. The script displays those failures rather than continuing as if setup succeeded. GitHub sign-in may still require GitHub's browser/device verification; software downloads are handled through the terminal.

The implementation follows Microsoft's documented [WinGet install options](https://learn.microsoft.com/en-us/windows/package-manager/winget/install) and [WinGet bootstrap guidance](https://learn.microsoft.com/en-us/windows/package-manager/winget/#install-winget). Use a Windows version supported by WinGet; a broken or restricted package-management environment may require administrator assistance.

First preview locally:

```bat
Publish-Clean.bat --dry-run
```

This command-line dry run is strictly offline: it never installs packages, authenticates or uploads. If Git is missing, use menu option 1 first. Normal menu use always targets the folder containing the BAT, returns after actions, and closes when you select 0. `--help` prints usage. There is no unattended confirmation-bypass flag.

## Create or connect

1. Prepare an isolated snapshot, apply ignores and filtering, scan selected text for potential secrets, and write `.clean-publish-report.json`. The report contains paths, sizes and hashes, never detected secret values.
2. Check GitHub CLI authentication and offer its browser/device login if necessary. Display the signed-in account.
3. Main menu option 3 asks for a repository name; option 4 asks for an existing GitHub HTTPS/SSH link. A named repository already on the account is updated; otherwise creation is prepared. Existing-link mode requires an accessible repository. Targets must belong to the signed-in personal account; organizations are outside this version's scope.
4. New repositories default to visibility option 1, Private. Option 2 selects Public and 0 cancels. Existing visibility is preserved.
5. Review the full report, staged summary and proposed removals. The final numbered menu shows the target and visibility: choose 1 to create/commit/push or 0 to cancel. Cancellation is the default. A public target is explicitly identified as public before confirmation.

Missing repositories are created with the documented [gh repo create](https://cli.github.com/manual/gh_repo_create) command. Existing repositories use their default branch; new/empty repositories use main. Protected branches, permission errors and non-fast-forward changes fail without force pushing. If creation succeeds but push fails, an empty repository may remain; fix the error and rerun using its existing link. It is never automatically deleted.

## Clean file selection

Source, documentation, manifests, lockfiles, tests, ordinary assets, licenses and sanitized environment examples are retained when allowed by your ignores. An empty temporary index evaluates ignores, so even an already-tracked local file is omitted when ignored. Source `.gitignore` files, standard/global excludes and a source repository's info/exclude are applied. Add a Git-style `.publishignore` for extra local exclusions:

```gitignore
private-notes/
customer-exports/
local-only.json
```

Hard exclusions cannot be undone with ignore negations. Defaults omit Git internals, dependency folders, environments, caches, build outputs, logs, archives/compiled binaries, local databases, environment secrets, credential files, private keys, IDE state, symlinks/junctions and files over 25 MiB. `.env.example`, `.env.sample` and `.env.template` are allowed but still scanned. Known token/key formats, credential-bearing URLs and some suspicious secret assignments block publishing instead of silently dropping source files. Sanitize synthetic fixtures that trigger false positives.

This is conservative filtering, not a build or complete secret audit. Binary contents are not comprehensively scanned. Projects requiring checked-in build outputs, binary dependencies, symlinks or submodules need a reviewed publishing workflow. GitHub's normal per-file limit is 100 MiB; this tool deliberately uses 25 MiB. Review large assets and [Git LFS](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github) separately.

## Preservation and limits

The source project's Git index, history, branches, remotes and working files are not staged/reset/rewritten. Only the local report is added/updated. The script builds an isolated Git object store and hashes scanned snapshot bytes without clean filters. It runs no project build/install scripts or Git hooks. Local history, tags and ignored historical objects are not transferred.

Existing remote history is retained, and the new commit is a child of the fetched default-branch tip. Remote-only clean files are preserved. Remote files matching hard exclusions are proposed for removal from the new tip, and those paths are shown before confirmation. Local deletion of a clean file does not delete its remote counterpart. `.publishignore` controls local selection, not remote-only files. Existing remote-only content and history are not comprehensively scanned. Existing executable modes are retained; new .sh files are executable.

Deleting from a tip does not erase history. Previously published secrets require revocation/rotation and separate reviewed cleanup. Public source remains copyable regardless of license wording.

## Verification

Windows tests use real snapshots and a local bare Git remote with offline GitHub account/API fixtures. They exercise ignored tracked files, source index/history preservation, secret blocking without disclosure, native quoting, link validation, tree updates/removals, cancellation and create/update flows. Additional tests cover the actual BAT menu entry, numeric dispatch, invalid input, recovery after errors, missing-tool install orchestration, WinGet bootstrap selection, PATH refresh, installer failures, terminal output/exit status and offline mode. Package downloads/installations are mocked in these tests; no real software was installed. Run:

```sh
python -m unittest discover -s tests -p test_publisher.py -v
```

No real GitHub authentication, repository creation or upload was performed while preparing this feature. GitHub CLI is not installed in this environment; the offline dry run works with Git alone.
