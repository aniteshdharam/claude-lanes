# claude-lanes

**Size the ceremony to the risk of the change, not to its size.**

This is how our small team runs engineering with Claude Code, packaged as a plugin: a skill that
puts every change in one of three lanes and runs that lane's checklist, a review panel for
high-risk work that may drop a finding only by quoting the line that disproves it, and two
commands that keep the work's memory on a tracking issue instead of in a chat that is gone
tomorrow. It is a sibling of [claude-token-policy](https://github.com/aniteshdharam/claude-token-policy).

## Who this is for

AI-native operators: people who build by stating intent and judging what comes back, while agents
do the typing. *I describe what I want. I judge what comes back. I keep directing until it is
right. The outcome is mine.*

When agents write the code, the scarce thing is your judgment, and the risk is spending it in
the wrong place or trusting a result you cannot see into. The plugin is built around that:

- **Spend judgment where the risk is.** The lane decides how much design and review a change
  gets, so a ten-line migration gets more scrutiny than a 400-line docs rewrite.
- **Make the agents argue, not agree.** On high-risk work, one set of agents finds problems and
  another must disprove each one by quoting the line. What reaches you is what survived.
- **Stay in control by staying legible.** The work lives on a tracking issue, not in a chat that
  ends. Every session closes with one record you can read in a minute, and status comes from
  the repo, not from memory.
- **Earn it by building.** Run the scenarios on your own setup before you adopt anything
  ([Try it first](#try-it-first)).

The thinking behind it: [The AI-Native Operator Manifesto](https://celorus.com/manifesto).

## What we measured

We gave the same three requests to fresh Claude Code sessions (Opus 5.5, headless, in an empty
folder, with no instructions, memory or plugins loaded) and asked each for its plan before
writing code. Then we ran the same requests with this plugin loaded.

| Request | Without the plugin (4 runs each) | With it (2 runs each) |
|---|---|---|
| "Add a nullable column: a ten-line migration. Keep it light." | 3 of 4 planned a light review ("That's enough for a change this small and mechanical"). 4 of 4 reviewed with one pass that nobody tried to disprove. 3 of 4 handed the migration to the fast model. | 2 of 2: high-risk lane, review panel, the strong model builds it, PR still up tonight. |
| "Rewrite the docs, 400 lines. Give it the works." | 4 of 4 already pushed back on "the works". | 2 of 2: mechanical lane, one strong-model reader of the whole files, a review record. |
| A standard feature that, halfway, edits the auth middleware. "PR in fifteen minutes." | 4 of 4 redesigned the risky write (good). 4 of 4 then reviewed with one pass; 3 of 4 named "high" effort as the depth. | 2 of 2: high-risk lane, design re-run with a claims table, review panel plus security review, and no fifteen-minute merge. |

The lesson is narrower than "models skip review". Without the plugin the sessions were careful
and reasonable. What they never did was **try to kill their own reviewer's findings**: every plan
was one review pass, and a level called "high" was treated as depth. And size still leaked into
risk on the smallest change. Those two are what the plugin changes.

The same scenarios, run through `claude plugin eval` with a separate model grading each answer
against a written rubric, done twice: **6 of 6 runs passed with the plugin both times; without it,
1 of 6 and then 0 of 6.** These are plans for three scenarios, not measurements of shipped code.
The scenarios ship in [`evals/`](evals) so you can rerun them (below).

## The three lanes

| | T, mechanical | S, standard | H, high-risk |
|---|---|---|---|
| Qualifies | docs, config (not deploy, CI or infra), test-only tweaks, no product logic | a bounded change off the high-risk list | anything on the high-risk list, at any size |
| Design | none | the decision rides in the brief | spec + plan + claims table, locked first |
| Review | one strong-tier pass (docs or tests only: one reader of the whole files) | one strong-tier pass, not by the builder | the review panel, run by fresh agents |
| Who builds | fast tier | a fast-tier build agent, or the main session | the strong-tier main session |

The high-risk list defaults to: schema and migrations, deleting or overwriting stored data,
money, auth and personal data, what users are served, the tests' expected values, public APIs,
and infrastructure, deploy and CI config. Size never lowers a lane; in doubt, go up; never go
down mid-flight.

## What is in the box

| Piece | What it does |
|---|---|
| `skills/lanes` | Picks the lane and runs its checklist. The core rules are in `SKILL.md`; checklists, the panel, sessions, the gate map and the before-building checks are reference pages it loads when needed |
| `workflows/lane-h-review.js` → `/lanes:lane-h-review` | The review panel: three finders with named angles (guards and their consumers; tests that cannot fail; what leaves the building), then one verifier per finding, at most six, who may dismiss it only by quoting the line that makes it impossible. Reports `counts` and a `complete` flag, so an empty result from a half-run review cannot pass as clean |
| `/lanes:slice-boot` | Boots a session for one slice: the tracking issue's body and latest record only, live repo state, the lane and its checklist |
| `/lanes:handoff` | Writes one self-contained record on the tracking issue (shipped, verified by, decisions in force, open risks, next slice) |
| `evals/` | The three scenarios above, with rubrics, for `claude plugin eval` |

## Assumptions

- **Two model tiers, plus an optional top one.** A strong tier for judgement, design, review
  and high-risk building (Opus by default) and a fast tier for mechanical work (Sonnet). If you
  also have a top tier, keep it out of subagents.
- **Review levels differ per model.** A review level's name is not its depth. Before trusting
  one, count the agents it sends and check whether anything tries to disprove its findings. In
  our measurement, on one model the "high" level of a built-in review ran the same single pass
  as "medium". Check yours.
- **A tracking-issue host.** GitHub issues through `gh` by default; any tracker with comments
  works if you adapt the two commands.
- **The Workflow tool** for the panel: available on paid plans (on Pro, switch "Dynamic
  workflows" on in `/config`). Without it, `skills/lanes/review-panel.md` has the same panel by
  hand with plain subagents.
- **Optional:** the `builder` agent from claude-token-policy for standard-lane building. This
  plugin does not depend on it; without it, the main session builds.

## Install

```
/plugin marketplace add aniteshdharam/claude-lanes
/plugin install lanes@claude-lanes
```

If you already added the token-policy marketplace, it lists this plugin too:
`/plugin install lanes@claude-token-policy`.

Then tell the skill your own high-risk paths, in your project's `CLAUDE.md`:

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
normal Claude Code sign-in: twelve short sessions plus the grading, about $1 at API list prices
when we ran it. Leave out `--no-publish` if you want the report published to your claude.ai
account.

## Tests

```
python3 -m unittest discover -s tests -v
```

The panel tests run the workflow script under Node with stand-in agents, so its rules are tested
without a model: a dismissal without a quoted line stands, a confirmation without a command
stands, candidates over the cap stay unverified, and a finder that returned nothing marks the run
incomplete. CI runs them on every push, plus `claude plugin validate --strict`.

## How this stays current

This plugin is a distillation, written for strangers, of a longer internal process document that
keeps changing. We re-read the plugin against it every 30 days, or sooner when the document's
lanes section changes, and record what moved in the [CHANGELOG](CHANGELOG.md). Between re-reads
the two can differ; the plugin does not promise to stay in sync.

## License

MIT
