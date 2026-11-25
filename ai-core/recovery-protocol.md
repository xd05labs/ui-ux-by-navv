# Recovery protocol

Read [docs/recovery.md](../docs/recovery.md). Resume saved discovery automatically. Configuration transactions replay from a validated journal; interrupted generation rolls back through `recover-generation`. Do not clear a workspace lock without verifying its process is no longer running. Do not delete data or edited source to make a retry pass.

After recovery, inspect config, state, manifest and generated files; re-plan if inputs changed, then rerun affected checks. Human edits require manual merge from a fresh separately generated workspace. Keep backups until the result has been reviewed.
