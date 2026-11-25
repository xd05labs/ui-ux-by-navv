# Benchmark protocol

These are proposed release targets, **not achieved results**:

| Metric | Target |
| --- | --- |
| First-generation build success | At least 95% across a defined run set |
| Required feature completion | 100% of the run's agreed acceptance criteria |
| Known critical vulnerabilities | Zero after documented scan/review |
| Lighthouse performance / accessibility | At least 90 / 95 on defined reference pages |
| Broken navigation | Zero on the defined route set |
| Defined viewport coverage | 100% of mobile/tablet/desktop cases |
| Persisted decision recovery | 100% of the recorded decisions |
| Configuration schema validity | 100% |
| Cross-LLM compatibility | Verified separately per named host/version |

Use `examples/saas/project.config.json` as a common reference. Fix repository revision, prompt, config, host/model version, tool capabilities and clean-environment conditions. Run multiple independent trials per provider, keeping first-attempt success separate from repaired success. Record failures; never remove failed runs from the denominator.

For each run retain source/config hashes, elapsed time, token usage if actually exposed by the host, commands, logs, browser evidence, feature acceptance results, security/dependency scans and performance data. Unknown token usage remains null; do not estimate it as measured usage. Generated app checks do not measure an LLM's code generation quality by themselves.

```sh
python benchmarks/record_run.py --workspace workspace --provider "host/model-version" --elapsed-seconds 300
```

The recorder reruns available workspace validation and stores a measurement record; it does not claim cross-provider comparison or full quality targets. Provide optional --tokens only from actual host accounting. No provider calls or paid evaluations run automatically. There is no verified cross-LLM result set in this release.
