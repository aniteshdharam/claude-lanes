# The PR body, per lane

Every lane's PR names its lane on the first line and carries its review record. What differs
is how much else it carries. Copy the block for the lane; fill the angle brackets.

## Lane T: three lines

```markdown
Lane: T. <what changed, in one line>
Review: <one strong-tier pass on the diff | one strong-tier reader of the whole files>, <model>, <where its text lives>; result: <clean | n findings, all fixed | empty>
CI: <run id> green.
```

## Lane S: the template, lean

```markdown
Lane: S. Tracking issue: <#n>.

## What
<the change, in two or three lines; the locked decision it carries>

## Checks
- local: <suites run>
- CI: <run id> green; correctness gate: <green | not applicable, why>

## Review record
<label line> · <model> · <agents sent> · <where the text lives> · <n findings: fixed / filed / disputed>
```

## Lane H: the full template plus the review record

```markdown
Lane: H. Tracking issue: <#n>. Design: <link>. Plan: <link>.

## What
<the change and the done-when it serves>

## Claims table
<link to the table, or the table itself; every row verified or UNVERIFIED>

## Checks
- local gate: <command(s)>, green at <sha>
- fixtures: <for each guard test, the one line on what would make it meaningless>
- CI: <run id> green; correctness gate: <run id> green
- security review: <ran on <sha>, result | not applicable: auth, secrets and the public surface did not move>

## Review record
<label line> · <model> · `counts.agents_sent`: <n> · `complete`: <true | false, why> · <where the text lives>
| finding | verdict | disposition |
|---|---|---|
| <file:line, title> | <confirmed / stands / dismissed / unverified / over cap> | <fixed in <sha> / filed as <#n> / cannot happen: <quoted line>> |

Decisions in force: <the ones this PR locks>
```

A merge with no review record is a stop. The record is the only evidence the review ran:
an unrun review prints nothing.
