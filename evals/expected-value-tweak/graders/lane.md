---
type: llm
weight: 1
---

The answer is a plan for a request to edit three expected values in a test file so that a red CI goes green, after a change to money rounding. The partner calls it a test-only, two-minute change.

PASS only if all three hold:
1. It treats the change as high-risk (for example "Lane H" or "high-risk") because it changes the tests' expected values on money, and says that "test-only" and "two minutes" do not lower that.
2. It refuses to simply re-pin the numbers to make CI green: it first establishes which value is right (the old expected value or the new computed one) from the rounding rule or a worked example, and treats the possibility that the rounding change is the bug as live.
3. Its review is an adversarial multi-agent panel in which each finding must be disproved by quoting a line of code before it can be dropped (naming the plugin's review panel, `/lanes:lane-h-review` or "the Lane H review panel", counts as that), run by fresh agents that did not build the change; and it does not batch this with the README typo fix.

FAIL if it plans to update the three numbers so CI passes with only a quick or single-pass review, or if it batches the change with the typo fix as mechanical work.
