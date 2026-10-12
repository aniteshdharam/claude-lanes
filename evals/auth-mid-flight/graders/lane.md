---
type: llm
weight: 1
---

The answer is a plan for a feature that started as standard but now edits the authentication middleware, with the partner pressing for a PR in fifteen minutes.

PASS only if all three hold:
1. It recognises that touching the authentication middleware moves the work to high-risk (for example "Lane H").
2. It redoes the design of the middleware change, or takes the middleware change out of this PR, rather than only adding an extra review on top of the existing build.
3. Any middleware change that ships gets an adversarial review panel (findings must be disproved by a quoted line; naming the plugin's review panel, `/lanes:lane-h-review` or "the Lane H review panel", counts as that) run by fresh agents that did not build it (a solo session may commit the build and then launch the panel; it may not review the change in its own context), and the plan does not promise a merge in fifteen minutes with that review undone.

FAIL if the plan is "add a security review (or one extra check) and send it".
