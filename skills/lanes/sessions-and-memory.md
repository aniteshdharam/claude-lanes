# Sessions and memory

## Two roles

- **The base session** is long-lived and never writes slice code, so its context stays clean.
  It owns both ends of every slice:
  - *before*: picks the next slice **riskiest unknown first** (the one that, if it breaks, breaks
    everything downstream, tested as cheaply as possible); locks the consequential design
    decision with the human; names the lane and model; writes a self-contained brief.
  - *after*: drives the review the lane calls for, reads CI, and merges. On T and S it may
    review in its own session while that session's context is still small; on H it dispatches
    the panel (and a security review where one applies) to fresh agents.
- **Build sessions** are fresh and short: one slice (one PR) each, booted from the brief. They do
  not make the load-bearing design call (it was locked before they started), do not review their
  own high-risk work, and end with a hand-off. A build session that lingers fills with context
  and starts making worse decisions.

Working solo, one session can hold both roles: commit the build, then launch the panel from
that session. **One separation never relaxes:** the high-risk review itself runs in fresh agents
with no context from the session that built or coordinated the change; that session launches it
and rules on its record, it does not review. Once a base has coordinated many slices, its own
review of T and S gets stale too: hand that to a fresh agent.

## The tracking issue

One long-lived issue per chunk of work (a feature, a wave of slices). Its body holds four
sections and changes only when the human changes the scope:

```markdown
## Spec (locked)
<the scope, quoted from the plan or spec, so the target cannot drift mid-chunk>

## Done when
<the gate: which checks, which numbers>

## Not in scope
<explicit exclusions>

## Children
- [ ] <slice 1>
- [ ] <slice 2>
```

Every PR names the issue. The issue closes only when the gate passes. GitHub issues are the
default host (`gh`); any tracker with comments works.

## The hand-off: one self-contained record

A session ends by posting **one** comment on the tracking issue that the next session can start
from with nothing else. `/lanes:handoff` drafts it:

```markdown
## Record: <slice>, <date>
**Shipped:** <PR link, final commit, merged or not>
**Verified by:** <CI run id, tests run, the review record: label, agents sent, model>
**Decisions in force:** <locked decisions the next slice must not reopen>
**Open risks:** <what is known wrong or unproven, and where it is tracked>
**Next slice:** <one slice, its lane, its model, the one thing to read first>
```

If the latest record is not self-contained, write a fresh consolidated one. Never ask the next
session to read the thread.

## The boot: latest record only

A fresh session boots the same way every time (`/lanes:slice-boot` does it):

1. The lane's boot reading (T: the task; S: the brief; H: the project docs, meaning the
   agent instructions file and whatever the brief names, nothing wider).
2. The tracking issue's **body** and its **latest record comment only**. On a long-lived issue
   the thread is huge, and every session that re-reads it pays for it again.
3. For H: the slice's design and plan, and the previous slice's PR as precedent.
4. **Live state**: `git pull`, open PRs, CI on the default branch, the issue's real state.
   Parallel sessions may have landed work since the record was written.

## Status is computed live

When anyone asks where things stand, answer from `git` and the tracker at that moment, scoped to
the question. A session's memory records what was true when it was written; a ticked checklist
box is a person's claim, not the issue's state. Use both only as hints for what to query. A
status line you cannot tie to a live result is marked unbacked, never shown as fact. Never read
a previous status report back as a source.
