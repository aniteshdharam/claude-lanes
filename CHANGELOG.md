# Changelog

## 0.2.0

- The review panel gets a third stage: one checker per dismissal re-reads the quoted line at the
  head commit with `git show`, and a quote that is not there turns the dismissal into `stands`.
  A quote with an absolute path, or one that climbs out of the checkout, never counts, so a
  verifier cannot dismiss a finding by quoting its own edited copy. The label is now `v2` and
  names the model.
- The panel no longer drops a finder's findings past its fourth: the first four compete for
  verifiers, the rest are returned as `over_cap`, unverified. Ties within a severity go
  round-robin across finders, so the data-safety angle is no longer always the first cut. The
  checker is not told what the verifier quoted, and a quote must be the line or at least half
  of it.
- The checkout path is shell-quoted in every command the agents are given; a fast-tier model
  running the panel is warned about in the log.
- A project's `High-risk paths` section now adds to the default categories instead of replacing
  them.
- New reference page `pr-body.md`, the PR body for each lane that the checklists cited and
  nothing shipped; `examples/CLAUDE.md`, a filled high-risk list and gate map; the correctness
  gate and the security review are defined where they are first required.
- `/lanes:slice-boot` reads `.claude/handoff.md` when there is no tracking issue, which is where
  `/lanes:handoff` writes in that case.
- A fourth eval scenario, `expected-value-tweak`: re-pinning three money figures in a test to
  make CI green, which looks mechanical and is high-risk. The auth scenario's rubric accepts a
  solo session that commits, then launches the panel.
- Tests for each panel rule above and for the eval cases' shape; CI runs with read-only
  permissions.

## 0.1.0

- First public release: the lanes skill and its reference pages, `/lanes:slice-boot` and `/lanes:handoff`,
  the high-risk review panel as a workflow, the lane-choice eval suite, and tests.
