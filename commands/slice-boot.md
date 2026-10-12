---
description: Boot a session for one slice of work in its lane, from the tracking issue's latest record and live repo state
argument-hint: "[T|S|H] [tracking issue number or URL]"
allowed-tools: Bash(git:*), Bash(gh:*), Read, Grep, Glob, Skill
---

Boot this session for one slice. Arguments, if any: `$ARGUMENTS` (a lane letter and/or a
tracking issue).

1. Load the `lanes` skill.
2. Find the tracking issue: the one in the arguments, else the one named in the brief or the
   user's message. If there is none, say so in one line and continue from the brief alone.
3. Read the issue's **body** and its **latest comment only**, never the thread:
   - `gh issue view <n> --json title,body,state,url`
   - `gh issue view <n> --json comments --jq '.comments[-1] | {author: .author.login, createdAt, body}'`
   If the latest comment is not a self-contained record (shipped, decisions in force, next
   slice), say so and ask the user whether to write a consolidated one before building.
4. Check live state, one command each: `git status --short --branch`, `git fetch --quiet`,
   `git log --oneline -5 @{upstream}` (or the default branch), `gh pr list --state open --limit 10`,
   and the latest CI run on the default branch (`gh run list --branch <default> --limit 1`).
   Note anything that landed since the record was written.
5. Settle the lane. Use the letter in the arguments if given, but check it against the skill's
   high-risk list and the slice described in the record or brief: if the slice touches the list,
   it is H whatever was passed, and say why in one line. If no lane was given, pick it.
6. Print, in this order and nothing else:
   - **Slice:** one line. **Lane:** the letter and the one-line reason. **Model:** who builds.
   - **State:** what the record says shipped, what live state adds, anything that conflicts.
   - **Decisions in force** and **open risks**, from the record.
   - The lane's checklist from the skill's `lanes-reference.md`, unticked.
   - For H only: the design and plan to read next, and whether a claims table exists yet.

Do not start building in this command. Do not read the issue thread, project-wide docs beyond
the lane's boot reading, or previous sessions.
