# Resume, undo and recovery

## Resume ordinary work

Run `python -m appforge status`, then `wizard` to ask only unanswered relevant questions. The workspace contains typed configuration, provenance, approvals, event history and validation references. Switching LLMs requires reading these files, not copying an entire conversation.

## Configuration undo

`python -m appforge undo` restores the previous configuration/state snapshot and invalidates approval. Repeated undo walks the prior snapshot chain. Generated source and runtime data remain untouched. Run plan, review, approve and generate --dry-run before reconciling source with restored preferences. History contains project decisions; protect it with the workspace.

## Interrupted configuration transaction

The next locked read validates and replays `.transaction.json`. If the journal is damaged, preserve the directory, compare the latest `.history/` entries and restore a known valid config/state pair. Do not blindly discard one half of a transaction.

## Interrupted generation

If `.generation-journal.json` exists, inspect it and `.generation-backups/`. Stop any still-running writer. Run `python -m appforge recover-generation` to restore backed-up files, remove files created by that interrupted operation and restore the prior manifest. This recovery deliberately restores pre-operation source; preserve any edits made after the interruption in a separate location first.

## Stale workspace lock

The `.appforge.lock` file records a PID. Verify that process is no longer running and that another shell/agent is not operating on the workspace. Only then remove that exact lock file with the platform's native filesystem command. The CLI never steals a lock based on its age.

## Manual edit conflict

Generation refuses to overwrite edited or unmanaged files, even if the proposed result is small. Keep the edited application; create a separate workspace, import the revised config, plan/approve/generate there, and compare the fresh output against the old managed version and your edits. Merge deliberately. There is no --force overwrite shortcut. Reconciled source can be maintained by an agent with explicit reviewed scope; do not forge manifest hashes just to suppress conflicts.

## Configuration migration

Only schemaVersion 1 is currently supported. Unknown versions fail before writes. A migration must be an explicit reviewed conversion that retains a backup, maps every field, reports loss/incompatibility, validates the new schema and invalidates approval. No automatic version conversion is shipped in v0.1.
