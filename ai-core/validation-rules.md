# Validation rules

Use `quality-assurance/release-gates.json`. For each gate record passed/failed/pending/not-applicable, command/tool, timestamp, exit status or observed result, scope and evidence path. Only use not-applicable with a reason tied to this application.

`appforge validate` checks schemas, current plan, managed hashes, semantic contrast, Python compilation and the generated WSGI integration suite. It leaves browser, complete feature acceptance, security audit, deployment drill and performance gates pending. Read command output; do not rely on an exit code alone when a tool skipped tests.

Self-correction cycle: reproduce -> identify cause -> apply smallest sound correction -> rerun affected checks -> update evidence. Do not loop forever on missing external credentials or fabricate success. Explain the exact remaining dependency.
