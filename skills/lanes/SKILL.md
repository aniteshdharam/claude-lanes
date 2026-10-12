---
name: lanes
description: Use when deciding how much design, testing and review a code change needs; when a change touches schema or migrations, stored data, money, auth, personal data, what users are served, tests' expected values, a public API, or deploy config; when a change grows or changes risk mid-build; before reviewing or merging; and when starting or ending a session that continues earlier work.
---

# Lanes

**Size the ceremony to the risk of the change, never to its size.** Every change gets a lane
before work starts, and the lane sets everything it pays: boot reading, design, local checks,
review, PR body, model tier. The review that catches real bugs is never cut on risky work; what
gets cut is fixed-cost ceremony on work where it catches nothing.

## 1. Pick the lane before any code

| Lane | Qualifies |
|---|---|
| **T, mechanical** | Docs, comments, config (not deploy, CI or infrastructure), one env var, test-only tweaks. No product-logic change; roughly under 30 lines of code. |
| **S, standard** | A bounded feature or fix that touches nothing on the high-risk list. |
| **H, high-risk** | Anything that touches the high-risk list, **at any size**. |

**The high-risk list.** If the project's `CLAUDE.md` has a `High-risk paths` section, use it.
Otherwise: schema and migrations; deleting or overwriting stored data; money, units and rounding;
auth, sessions, permissions, secrets, personal data; what users are served (API responses,
public pages, exports); the tests' expected values and the checks that read them; a public API or
contract; infrastructure, deploy and CI config.

Rules for choosing:

1. **Size never lowers a lane.** A ten-line migration is H. A 400-line docs rewrite is T.
2. **In doubt, go up. Never go down mid-flight.**
3. **Going up re-runs the new lane's front end on the existing diff** (design lock, claims
   table), and that decides whether the diff survives. Adding a review on top of a build scoped
   in the wrong lane is not going up. Splitting is also going up: ship the part that stays in
   its lane, and take the risky part out into its own H slice.
4. **"Keep it light" and "give it the works" do not set the lane.** The list does. Say in one
   line which lane it is and what that lane needs.
5. **State the lane** in the brief or your first message, and in the PR body: `Lane: H`.

## 2. What each lane pays

| | T, mechanical | S, standard | H, high-risk |
|---|---|---|---|
| Boot | the task | the brief + tracking issue body + its latest record | the project docs + issue + design and plan + the previous slice's PR |
| Design | none | the locked decision rides in the brief | design spec + plan + **claims table**, locked before building |
| Local checks | tests for the touched area; CI runs the rest | targeted + directly affected suites | the full local gate, including correctness tests |
| Review | one strong-tier pass; docs-only or test-only: one strong-tier **reader of the whole files** | one strong-tier pass, not by the builder; the base may run it in its own session while that context is still small | the **review panel** on the delta, run by fresh agents, never in the context that built or coordinated it; plus a security review when auth, secrets or the public surface move |
| PR body | three lines | the template, lean | full template + the review record |
| Sessions | batch several T items | one slice per session | one slice per session |
| Who builds | fast tier | a fast-tier build agent with a written brief, or the main session | the strong-tier main session itself, never handed down |

Per-lane checklists: [lanes-reference.md](lanes-reference.md).

## 3. Rules in every lane

- **CI green before merge.** Your correctness gate runs wherever product code changes.
- **A merge with no review record is a stop.** The record names what ran, on which model, how
  many agents it sent, and where its text lives. An unrun review prints nothing, so no other
  check shows it missing.
- **An empty review and a clean review look the same.** Before citing a review as coverage,
  check what it read. Some review levels skip test and docs files by design; a test-only or
  docs-only change gets one strong-tier reader of the whole files, posted verbatim. An empty
  result is recorded as empty.
- **A review level's name is not its depth.** Count the agents it sends and look for a verify
  stage before trusting "high effort".
- **Fresh eyes are not adversarial verification.** A fresh reviewer is asked "what is wrong?";
  the panel's second stage must disprove each finding by quoting a line, or it stands.
- **Review the delta.** A fix round is reviewed from the last reviewed commit, never the whole
  PR again.
- **A green test proves only what its fixture exercises.** For each guard test, write one line:
  what the fixture would have to look like for this test to be meaningless; show it is not.

## 4. The high-risk review panel

Three finders, one angle each (guards and everything that consumes them; tests that cannot
fail; what leaves the building), then one verifier per finding, at most six, who may dismiss it
**only by quoting the line that makes it impossible**. Run it on a throwaway checkout at the head
commit: the Workflow tool with name `lanes:lane-h-review` and args `{tree, head, base, brief}`,
or typed, `/lanes:lane-h-review tree=<path> head=<sha> base=<sha>`. Trust a clean result only when `complete` is true and
`counts` show every agent returned; candidates over the cap are unverified, not cleared. How to
run it, read it, and do it by hand: [review-panel.md](review-panel.md).

## 5. Sessions and memory

A **base** session holds the work: picks the next slice riskiest-first, locks the design, names
the lane and model, writes the brief, drives the review (on H it dispatches the panel; it never reviews H in its own
context), merges. **Build** sessions are fresh, one
slice each. Memory lives on a **tracking issue**, not in the chat: start with `/lanes:slice-boot`,
end with `/lanes:handoff`. Details: [sessions-and-memory.md](sessions-and-memory.md).

## 6. Which check do I run?

Keep a gate map for the repo ("you changed... / run / what it checks"). The map points at a
check; it never restates what the check covers. [gate-map.md](gate-map.md).

## 7. Before a high-risk build or a first live write

A **claims table** before building H: each claim about existing code the design leans on gets
`path:line` at a named commit, or UNVERIFIED, and an unverified claim blocks the build. Before
the first write to live data that steers or serves answers, **read the full planned write
set**. [before-building.md](before-building.md).

## Red flags: stop and re-pick the lane

- "It's only ten lines." / "Keep it light."
- "A fresh-context reviewer is enough." / "High effort covers it."
- "I'll add a security review on top and send it."
- "The review came back clean." (How many agents? What did they read?)
- "It's big, so give it the works." (On docs: one reader, not the panel.)

| Excuse heard without this skill | Reality |
|---|---|
| "That's enough for a change this small and mechanical." (a migration) | Size never lowers a lane. A migration is H. |
| "A fresh-context AI reviewer reads the diff." (high-risk change) | One reviewer finds; nobody tries to kill the findings. H gets the panel. |
| "An independent automated review of the diff at high effort." | A level's name is not a verify stage. Count the agents. |
| "Sonnet builds it." (a migration) | H is built by the strong-tier main session. |
