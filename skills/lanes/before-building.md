# Before a high-risk build, and before a first live write

## The claims table (every H slice, before building)

A design leans on things it believes about the code that already exists: "this function already
rejects nulls", "nothing else writes this table", "that path is exempt". When one of those is
false, every review of the new code passes, because the reviewers check the new code against the
same false belief.

So before an H slice is built, list every such claim, one row each:

| Claim | Where | How verified this session |
|---|---|---|
| `<the belief, in one sentence>` | `path:line` at `<commit sha>` | `<command run, or code read>` |
| `<a claim nobody checked>` | | **UNVERIFIED** |

- An **UNVERIFIED** row blocks the build, the same as an unanswered design question.
- Check the claims against the code at a named commit, not against memory or a previous
  summary.
- A design review approves the design **given** these claims. It is not evidence about the code;
  each UNVERIFIED row goes to the code review by name.

## The fixture rule (every guard test)

A green test proves only what its fixture exercises. A degenerate fixture passes for the same
reason a wrong expected value does: nothing in it can trip the guard. For each test that guards
behaviour, write one line on what the fixture would have to look like for the test to be
meaningless (empty input, one item where the bug needs many, the one shape the bug cannot hit),
and show the real fixture is not that. A fix is not done until the original failing case is
the test.

## The write-set review (before the first write to live data that serves answers)

Some writers put rows where they steer what users are served: a lookup table, a name index, a
mapping that routes queries. For these, green checks are not enough for the first real write:

1. **Dump the full planned write set**, untruncated, to a durable place (the tracking issue or a
   file it links). A capped or elided preview hides exactly the rows that matter.
2. **Someone who did not write the writer reads it** against the bar the data must meet, using
   evidence from outside the writer's own inputs.
3. A later run whose output is a strict subset of a reviewed set (rows removed, none added)
   inherits the review; anything added or moved re-opens it.

Why: a green suite proves the code does what the code says. In our use, a writer passed three
reviews and nineteen unit tests, and at least a third of its planned write set was wrong rows:
the tests had been built from the writer's own assumption. Only reading the write set showed
what the data was about to be told.
