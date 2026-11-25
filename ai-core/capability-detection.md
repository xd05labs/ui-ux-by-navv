# Capability detection and fallback

Declare file read/write, terminal, test runner, image analysis, browser, network and multi-agent availability from the actual host tools. Unknown is not false or true. `doctor` performs only local read/write/subprocess probes and reports Python/Git availability; it never sends a network probe.

| Missing capability | Fallback |
| --- | --- |
| File read | Ask for selected instructions, config and relevant source text |
| File write | Emit complete files or unified patches with save instructions |
| Terminal/testing | Provide exact commands and mark execution pending |
| Image analysis | Ask for a visual description; mark extraction and optimization pending |
| Browser preview | Emit local preview HTML and a manual review checklist |
| Network | Use existing compatible dependencies and report unverified currency |
| Multiple agents | Perform logical reviews sequentially within one LLM |

Never infer permissions or execution from an adapter filename. Cross-LLM entry files are routing aids, not a guarantee that a host loads them automatically.
