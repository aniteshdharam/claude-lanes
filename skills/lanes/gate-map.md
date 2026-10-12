# The gate-selection map

You changed a file. Which check watches it? Answering that by reading every check's
configuration is how a session ends up running the wrong check, getting green, and believing it.
Keep one small table in the repo (in `CLAUDE.md` or a doc it points to) that answers it.

## The table, for you to fill

| You changed... | Run | What it checks |
|---|---|---|
| `<paths or kind of change>` | `<command>` | `<the thing it grades, in a few words>` |
| `<e.g. database migrations>` | `<e.g. make migrate-check>` | `<e.g. upgrade and downgrade on a scratch database>` |
| `<e.g. the public API handlers>` | `<e.g. make api-contract>` | `<e.g. responses against the published schema>` |
| `<a path no check watches>` | **none** | write it down: a declared gap is still a gap |

Fill it from what each check actually runs, not from its name. A row with **none** is useful: it
tells the next session that green CI says nothing about that path. Name the **correctness
gate** under the table: the check that grades outputs against known-right values, which every
S and H slice must pass. A filled example ships with the plugin in `examples/CLAUDE.md`.

## Three rules

1. **The map points; it never restates.** Each row sends you to a check; what that check covers
   and does not cover lives with the check itself (its config, its own comments, a test that
   pins its scope). A prose copy of a coverage list drifts, and a drifted map is worse than none
   because it reads as verified.
2. **A regression baseline is not a correctness check.** A baseline pins what the code does
   today, including what is already known to be wrong. It answers "did this change?", never "is
   this right?". An intended change re-pins the baseline in the same PR, so the move is visible.
3. **A zero is not coverage.** A category with no live examples passes by default. If a check
   can only be proven with seeded examples, say so where the check is defined, so nobody reads
   its zeroes as "we watch this".

## Reports versus gates

Some useful commands only print numbers. Keep them as reports that always succeed rather than
gates that can fail for reasons outside the change: a check that goes red for environmental
reasons is one people learn to wrap in `|| true`. Where a report needs teeth, enforce exactly
one invariant with a test.
