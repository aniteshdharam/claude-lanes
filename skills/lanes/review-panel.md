# The high-risk review panel

## What it is

Two stages, every agent fresh, none of them the session that built the change.

1. **Find.** Three finders read the delta in parallel, each from one named angle, and report at
   most four findings each, tied to a file and line:
   - *Guards and their consumers*: every condition, filter, default and return shape the change
     adds, and every consumer of what it changed. A guard narrowed for one caller moves the
     defect to the next.
   - *Tests that cannot fail*: would each new or changed test go red if the code it protects
     were broken? Passing by sort order, by a fixture that never reaches the path, by a skip, by
     asserting its own mock.
   - *What leaves the building*: silent deletes, overwrites and skips; served values the data
     does not support; widened access to personal data, credentials or an authenticated surface.
2. **Verify.** Findings are pooled by `file:line`, ranked by severity, and capped (six by
   default). Each candidate gets one verifier whose job is to kill it. **It may dismiss a
   candidate only by quoting the line (`path:LINE` and its exact text) that makes the failure
   impossible.** Unconvinced, unlikely, or "no test for it" is not a dismissal. A verifier that
   shows the failure with a command marks it confirmed.
3. **Check.** Every dismissal rests on one quoted line, so a checker re-reads it: one agent per
   dismissal runs `git show <head>:<path> | sed -n '<line>p'` in the shared checkout and reports
   what it printed, nothing more. The workflow compares. A quote that is not there at the head
   commit (a line the verifier edited in its own copy, a path that does not exist, a wrong line
   number) turns the dismissal into `stands`. A quote with an absolute path, or one that climbs
   out of the checkout, is never a quote.

The inverted burden of proof is the point. A single reviewer, however fresh, decides whether it
is convinced; a reviewer who is merely unconvinced drops real bugs. On our own repository, this
second stage caught defects on four of four high-risk slices that green CI and an independent
fresh reviewer had both passed; that is our experience, not a measurement you can rerun.

## Run it

```bash
git -C <repo> worktree add --detach <scratch>/lhr-tree <head sha>
```

Then run the workflow. Typed, `/lanes:lane-h-review` with the arguments after it (below). From
a session, the Workflow tool with the name `/workflows` lists for the plugin's workflow (on our
install, `lanes:lane-h-review`) and `args` as an object:

```js
{ tree: "/abs/scratch/lhr-tree", head: "<40-char sha>", base: "<40-char sha>",
  brief: "what the change claims to do; spec at docs/spec.md" }
```

Or type it: `/lanes:lane-h-review` followed by the same object as JSON, or as key=value pairs
(`tree=/abs/scratch/lhr-tree head=<sha> base=<sha> brief="..."`; `files` comma-separated;
`angles` only as JSON). The arguments:

| arg | |
|---|---|
| `tree` | absolute path of that throwaway checkout |
| `head` | the full 40-character sha it is at |
| `base` | the full sha the delta starts from (the panel reads `base...head`); on a fix round, the last reviewed commit |
| `files` | optional paths to scope to; with no `base`, those files read whole at `head` |
| `brief` | optional: what the change claims to do, and where its spec lives |
| `angles` | optional: replace the three angles, `[{key, title, ask}]`, one to five |
| `max_candidates` | optional, 1 to 10, default 6 |
| `model` | optional, default `opus`: the strong tier, never the fast one |

Afterwards remove the checkout and any `<tree>.<role>` checkouts agents left:
`git -C <repo> worktree remove --force <path>`.

Cost: finders + `max_candidates` verifiers + one checker per dismissal (at most fifteen by
default, nine when nothing is dismissed). The lever is slice size: a sprawling slice finds more
than one run can verify.

## Read the result

- `complete: false` means something did not run or was not checked: a finder returned nothing
  or read no file, a verifier or checker returned nothing, or candidates went over the cap.
  **An empty report from an incomplete run is not a clean bill.** Re-run only when the counts
  show a pass never actually ran; an over-cap run is completed by you, not by a re-run.
- `over_cap` candidates are **unverified, not cleared**. Read each one yourself and write its
  disposition (fixed, filed, or why it cannot happen, with the quoted line) before merging. A
  run with over-cap candidates and a written disposition for each is mergeable; one without is
  not.
- `confirmed`: fix it. `stands`: fix it, or show the quoted line the verifier could not find
  (a `stands` whose reason says the quoted line is not at head means the verifier quoted
  something the reviewed commit does not contain). `dismissed`: carries its quote and
  `line_at_head`, what git printed for it; spot-check one.
- **Record it** on the PR or tracking issue: the `label` line, `counts.agents_sent`, the model,
  and the findings with their verdicts. A merge with no review record is a stop.

## Without the Workflow tool

Workflows run on every paid plan (on Pro, switch them on in `/config`). If they are off, run the
same panel with plain subagents:

1. Dispatch three subagents in parallel on the strong tier, one per angle above. Give each the
   checkout path, the scope command (`git -C <tree> diff <base>...HEAD`), the angle's question,
   the four-finding limit, and the rules: never edit the shared checkout (make its own worktree to
   run anything), run nothing against production or shared services, and report `head_seen`,
   `files_read` and findings as file, line, severity, failure and evidence.
2. Pool each finder's first four findings by `file:line` and rank by severity; within a
   severity, take every finder's first finding before any finder's second, so no angle is
   always the first cut. Keep six. Write down the rest, and anything a finder returned past its
   fourth, as unverified.
3. Dispatch one strong-tier subagent per candidate with the verifier instruction above, word for
   word on the burden: the candidate stands unless it quotes the line that makes it impossible,
   relative to the checkout root, as it stands at HEAD in the shared checkout.
4. Reject any dismissal without a `path:line` quote and any confirmation without a command.
5. For each dismissal, run `git -C <tree> show <head>:<path> | sed -n '<line>p'` yourself and
   compare with the quote. The quote is there when it is that line or at least half of it; a
   lone bracket or a bare `return` is not a quote of the line. A quote that is not there turns
   the dismissal into `stands`. Then read and record the result as above.

## Not this

- Not for T or S. Buying the panel "to be safe" on low-risk work spends the most expensive review
  where it catches least.
- Not a review of the whole PR on every fix round: the delta from the last reviewed commit.
- Not launched by a build session on its own change. The coordinating session launches it
  (working solo: you, once the build is committed) and rules on its record; its agents start
  fresh, so they do not inherit the build's framing.
