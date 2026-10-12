# Lane checklists

Copy the lane's block into the session's first message or the brief, and tick it as you go.
Placeholders in angle brackets are yours to fill.

## Lane T, mechanical

```text
Lane T:  [ ] the task, nothing wider          [ ] tests for the touched area only (CI runs the rest)
         [ ] review: one strong-tier pass on the diff
             docs-only or test-only? one strong-tier reader of the WHOLE changed files instead,
             posted verbatim; an empty result is recorded as empty, never as coverage
         [ ] CI green                          [ ] 3-line PR body, "Lane: T" (pr-body.md)
         [ ] review record on the PR           [ ] merge
         Batch more T items into this session. Builder: fast tier.
```

## Lane S, standard

```text
Lane S:  [ ] boot: the brief + tracking issue body + its latest record comment only
         [ ] verify live state: git pull, open PRs, CI on main (other sessions may have landed work)
         [ ] the locked decision is in the brief (if not, stop and get it locked)
         [ ] isolated workspace (a worktree or branch nobody else is on)
         [ ] build test-first; targeted + directly affected suites locally
         [ ] review: one strong-tier pass on the delta, not by the builder (the base may run
             it in its own session while that session's context is still small)
         [ ] CI green + correctness gate green (the gate map names it)
         [ ] PR: the template, lean, "Lane: S" (pr-body.md); review record on the PR
         [ ] merge (under a base: stop at a draft; the base reviews and merges)
         [ ] /lanes:handoff: record what shipped and name the next slice
         One slice per session. Builder: a fast-tier build agent with a written brief, or you.
```

## Lane H, high-risk

```text
Lane H:  Slice: ______  Tracking issue: ______  Model: ______

[ ] Boot      project docs + tracking issue body + LATEST record comment + design/plan
              + the previous slice's PR; then git pull and live state
[ ] Gate      the issue's done-when quoted; not-in-scope noted
[ ] Design    a short design spec, approved before any code
[ ] Claims    the claims table (before-building.md): every claim about existing code
              at path:line at a named commit, or UNVERIFIED; unverified blocks the build
[ ] Plan      bite-sized steps
[ ] Isolate   a worktree; never switch branches in a checkout another session uses
[ ] Build     test-first, by the strong-tier main session; current library docs, not memory
[ ] Fixtures  for each guard test, one line on what would make it meaningless; show it isn't
[ ] Local     the full local gate, including correctness tests
[ ] Review    the panel (/lanes:lane-h-review) on the delta, launched by the coordinating
              session (solo: by you, once the build is committed), never by a build session
              on its own change; security review (/security-review or your own) if auth,
              secrets or the public surface moved; read `complete` and `counts`; every
              over-cap or unverified candidate gets a written disposition before merge
[ ] Gate      CI green + correctness gate green (the gate map names it)
[ ] PR        full template (pr-body.md), "Lane: H", the review record (label, agents sent,
              model, where the text lives) and the verdicts
[ ] Write set first write to live data that serves answers? Read the full planned write set
              first (before-building.md)
[ ] Merge     under a base: the base merges after its verdict on the panel's record (complete,
              counts, a disposition for every finding) at the final commit
[ ] Hand off  /lanes:handoff: record what shipped, name the next slice
```

## Why the lanes are shaped this way

- The review panel is priced for risk, not for comfort. It runs on H only; T and S are not
  given it "to be safe". Its value comes from the second stage that tries to kill each finding,
  and that is worth paying for where a silent wrong answer is expensive.
- Mechanical work pays almost no fixed cost because its failures are loud: CI or a reader
  catches them. Batch it so the boot is paid once.
- One slice per session on S and H, because a long session drifts as its context fills. The
  memory lives on the tracking issue, so a fresh session loses nothing.
- Escalation is one-way. A slice that turns out riskier moves up and re-runs the new lane's
  front end; a slice never moves down mid-flight to save time.
- When a fix round comes back, review the delta from the last reviewed commit. Re-reviewing the
  whole PR each round is the most common way review spend runs away.
