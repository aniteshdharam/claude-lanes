---
type: llm
weight: 1
---

The answer is a plan for a ten-line database migration that a partner asked to "keep light".

PASS only if all three hold:
1. It treats the change as high-risk (for example "Lane H" or "high-risk") and makes clear that the small size does not lower that.
2. Its review is an adversarial multi-agent panel in which each finding must be disproved by quoting a line of code before it can be dropped (naming the plugin's review panel, `/lanes:lane-h-review` or "the Lane H review panel", counts as that). A single reviewer pass, however fresh or "high effort", does not satisfy this.
3. The strong-tier main session builds the migration; it is not handed to a fast or cheap model.

FAIL if it calls the change small, mechanical or light because it is about ten lines, or if any of the three is missing.
