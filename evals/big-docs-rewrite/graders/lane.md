---
type: llm
weight: 1
---

The answer is a plan for a 400-line rewrite of documentation files only, where the partner asked for "the full treatment".

PASS only if all three hold:
1. It treats the change as mechanical or low-risk (for example "Lane T") despite its size, and says so to the partner in a sentence.
2. It does not run an adversarial multi-agent review panel or a security review on it.
3. Its review is one strong-tier reader who reads the whole changed documents (not only a diff skim, and not a review level that skips documentation files).

FAIL if it buys a heavyweight multi-agent review because the change is large, or if its only review is a fast-tier or diff-only pass.
