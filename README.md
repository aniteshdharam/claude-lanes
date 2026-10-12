# claude-lanes

**A ten-line migration needs more review than a 400-line docs rewrite. Size design and review
to the risk of a change, not to its line count.**

This is how our small team runs engineering with Claude Code, packaged as a plugin. It puts
every change in one of three lanes (mechanical, standard, high-risk) and runs that lane's
checklist. On high-risk work, a panel of agents looks for problems and a second set tries to
disprove each one; a problem is dropped only by quoting the line that rules it out, and that
line is then re-read at the reviewed commit. Between sessions, the state of the work lives on a
tracking issue, not in a chat that is gone tomorrow. Graded against a rubric we wrote,
8 of 8 planning runs passed with the plugin and 1 of 8 without it ([details](#what-we-measured)). It is a sibling of
[claude-token-policy](https://github.com/aniteshdharam/claude-token-policy).

For anyone shipping production code through Claude Code agents, especially if you are the one
who answers for it when it breaks.

## The three lanes

| | T, mechanical | S, standard | H, high-risk |
|---|---|---|---|
| Qualifies | docs, config (not deploy, CI or infra), test-only tweaks, no product logic | a bounded change off the high-risk list | anything on the high-risk list, at any size |
| Design | none | the decision rides in the brief | spec + plan + claims table, locked first |
| Review | one strong-tier pass (docs or tests only: one reader of the whole files) | one strong-tier pass, not by the builder | the review panel, run by fresh agents |
| Who builds | fast tier | a fast-tier build agent, or the session itself | a strong-tier session, never a fast-tier agent |

The high-risk list defaults to: schema and migrations, deleting or overwriting stored data,
money, auth and personal data, what users are served, the tests' expected values, public APIs,
and infrastructure, deploy and CI config. A small change on that list is still high-risk. If
unsure, pick the higher lane, and never move a change down once work has started.

Some words the plugin uses. **Strong tier** means Opus and **fast tier** means Sonnet, by
default. A **slice** is one shippable piece of work, usually one PR. A **claims table** lists
every claim the design makes about existing code, each with a file and line at a named commit;
an unverified claim blocks the build. A **gate map** tells you which check to run for what you
changed. A **brief** is the written task a build session starts from. A **record** is the one
comment a session leaves on the tracking issue for the next one.

## What we measured

We gave the same three requests to fresh Claude Code sessions (Opus 5.5, headless, in an empty
folder, with no instructions, memory or plugins loaded) and asked each for its plan before
writing code. Then we ran the same requests with this plugin loaded. These were hand runs, not
a designed experiment, which is why the counts differ; the eval suite below is the equal-arm
comparison.

| Request | Without the plugin (4 runs each) | With it (2 runs each) |
|---|---|---|
| "Add a nullable column: a ten-line migration. Keep it light." | 3 of 4 planned a light review ("That's enough for a change this small and mechanical"). 4 of 4 reviewed with one pass that nobody tried to disprove. 3 of 4 handed the migration to Sonnet. | 2 of 2: high-risk lane, review panel, Opus builds it, and the PR still ships the same day. |
| "Rewrite the docs, 400 lines. Give it the works." | 4 of 4 already pushed back on "the works". No real difference on this one. | 2 of 2: mechanical lane, one Opus reader of the whole files, a review record. |
| A standard feature that, halfway, edits the auth middleware. "PR in fifteen minutes." | 4 of 4 redesigned the risky write (good). 4 of 4 then reviewed with one pass; 3 of 4 named "high" effort as the depth. | 2 of 2: high-risk lane, design re-run with a claims table, review panel plus security review, and no fifteen-minute merge. |

The lesson is narrower than "models skip review". Without the plugin the sessions were careful
and reasonable. But no plan ever had a second agent try to disprove the first reviewer's
findings: every plan was one review pass, and picking the "high" review level was taken as
enough depth. And on the smallest change, its size still talked the session into a lighter
review. Those two things are what the plugin changes. One finding on the way: on one model,
the "high" level of a built-in review ran the same single pass as "medium". A review level's
name is not its depth; count the agents it sends and look for anything that tries to disprove
its findings.

The scenarios ship in [`evals/`](evals), four of them now, each a request and a rubric:
`tiny-migration`, `big-docs-rewrite`, `auth-mid-flight`, and `expected-value-tweak` (re-pin
three money figures in a test so CI goes green, which looks mechanical and is high-risk). Run
through `claude plugin eval`, with Opus 5.5 answering and Sonnet grading against the rubric:

**8 of 8 runs passed with the plugin; 1 of 8 without it** (12 October 2026, Claude Code
2.1.296, two runs per scenario and arm). The one pass without it was the docs rewrite, where a
plain session already sized the work to its risk. An earlier run the same day, on the first
three scenarios only: 6 of 6 with the plugin, twice; 1 of 6 and then 0 of 6 without.

Read these for what they are. The rubrics check that the plan follows the lane rules, so the
numbers measure whether the rules are followed, not whether the shipped code is better. The
plans are plans, not shipped code. And we have not yet compared against the same rules pasted
into a plain `CLAUDE.md`, which is the control a careful reader would ask for.

## What is in the box

| Piece | What it does |
|---|---|
| `skills/lanes` | Picks the lane and runs its checklist. The core rules are in `SKILL.md`; the checklists, the PR body per lane, the panel, sessions, the gate map and the before-building checks are reference pages it loads when needed |
| `workflows/lane-h-review.js` → `/lanes:lane-h-review` | The review panel: three finders with named angles (guards and their consumers; tests that cannot fail; what leaves the building, meaning data that reaches users or outside systems), then one verifier per finding, at most six, who may dismiss it only by quoting the line that makes it impossible, then one checker per dismissal who re-reads that line at the head commit. Reports `counts` and a `complete` flag, so an empty result from a half-run review cannot pass as clean |
| `/lanes:slice-boot` | Boots a session for one slice: the tracking issue's body and latest record only, live repo state, the lane and its checklist |
| `/lanes:handoff` | Writes one self-contained record on the tracking issue (shipped, verified by, decisions in force, open risks, next slice) |
| `examples/CLAUDE.md` | A filled high-risk list and gate map to copy from |
| `evals/` | The four scenarios above, with rubrics, for `claude plugin eval` |

## Requirements

- **Two model tiers.** A strong tier for judgement, design, review and high-risk building
  (Opus by default) and a fast tier for mechanical work (Sonnet).
- **A tracking-issue host.** GitHub issues through `gh` by default; any tracker with comments
  works if you adapt the two commands. With no tracker, the hand-off is written to
  `.claude/handoff.md` and the boot reads it from there.
- **The Workflow tool** for the panel: available on paid plans (on Pro, switch "Dynamic
  workflows" on in `/config`). Without it, `skills/lanes/review-panel.md` has the same panel by
  hand with plain subagents.
- **Optional:** the `builder` agent from claude-token-policy for standard-lane building. This
  plugin does not depend on it; without it, the session builds.

## Install

```
/plugin marketplace add aniteshdharam/claude-lanes
/plugin install lanes@claude-lanes
```

If you already added the token-policy marketplace, it lists this plugin too:
`/plugin install lanes@claude-token-policy`.

Then add your own high-risk paths in your project's `CLAUDE.md`. They are added to the default
list above, not swapped in for it. A gate map is worth adding at the same time;
[`examples/CLAUDE.md`](examples/CLAUDE.md) has both filled in.

```markdown
## High-risk paths
- migrations/, app/billing/, app/auth/, api/public/, .github/workflows/
```

## Try it first

Run the scenarios against your own setup, with and without the plugin, before adopting it. From
a clone:

```
git clone https://github.com/aniteshdharam/claude-lanes
claude plugin eval ./claude-lanes --runs 2 --model opus --judge-model sonnet --no-publish
```

Each case runs twice with and twice without the plugin and reports the difference. It uses your
normal Claude Code sign-in: sixteen short sessions plus the grading, about $1.50 at API list
prices when we ran it in October 2026. Leave out `--no-publish` if you want the report
published to your claude.ai account.

## What it runs on your machine

The skill and the two commands only read: `git` and `gh` queries, the files they name. The
hand-off posts one comment on an issue you name, after showing you the draft. The panel's
agents run inside a throwaway checkout you create for it: they read the diff, may make their
own worktree from it to run tests, and are told to touch nothing outside it, push nothing and
reach no shared service. That is an instruction in their prompt, not a sandbox, so run the panel
on code you trust and with the permissions you would give any agent running your tests. The
plugin makes no network call of its own and sends nothing anywhere.

## Why it is shaped this way

When agents write the code, the scarce thing is your judgement, and the risk is spending it in
the wrong place or trusting a result you cannot see into.

- **Spend judgement where the risk is.** The lane decides how much design and review a change
  gets, so a ten-line migration gets more scrutiny than a 400-line docs rewrite.
- **Make agents try to disprove each other.** On high-risk work, one set of agents finds
  problems and another must disprove each one by quoting the line. What reaches you is what
  survived.
- **Stay in control by staying legible.** The work lives on a tracking issue. Every session
  closes with one record you can read in a minute, and status is read from the repo each time.

The thinking behind it: [The AI-Native Operator Manifesto](https://celorus.com/manifesto).

## Tests

```
python3 -m unittest discover -s tests -v
```

The panel tests run the workflow script under Node with stand-in agents, so its rules are tested
without a model: a dismissal without a quoted line stands, a quote with an absolute path or one
not found at the head commit stands, a confirmation without a command stands, candidates over
the cap stay unverified, nothing a finder returns is dropped, and a finder, verifier or checker
that returned nothing marks the run incomplete. CI runs them on every push, plus
`claude plugin validate --strict`.

## How this stays current

This plugin is a distillation, written for strangers, of a longer internal process document that
keeps changing. We re-read the plugin against it every 30 days, or sooner when the document's
lanes section changes, and record what moved in the [CHANGELOG](CHANGELOG.md). Between re-reads
the two can differ; the plugin does not promise to stay in sync.

## License

MIT
