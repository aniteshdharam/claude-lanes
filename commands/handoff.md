---
description: Write the end-of-session hand-off record and post it on the tracking issue, so the next session can start from it alone
argument-hint: "[tracking issue number or URL]"
allowed-tools: Bash(git:*), Bash(gh:*), Read, Grep, Glob, Write
---

Write the hand-off record for the slice this session worked on. Tracking issue, if given:
`$ARGUMENTS`; otherwise the one this session booted from.

1. Gather facts from live sources, not from memory of the session:
   - the PR: `gh pr view --json number,url,state,headRefOid,mergeCommit,isDraft` (or the PR
     named in the conversation);
   - CI on it: `gh pr checks <n>` (name the run, and every job's conclusion; a job still running
     is "not read", never green);
   - the review record: what review ran, its label line, how many agents it sent, on which
     model, and where its text lives. If no review ran, write "no review record" plainly.
2. Draft the record in exactly this shape:

   ```markdown
   ## Record: <slice>, <date, UTC>
   **Shipped:** <PR link, final commit sha, merged or draft or open>
   **Verified by:** <CI run id and result; local tests run; the review record>
   **Decisions in force:** <locked decisions the next slice must not reopen>
   **Open risks:** <known wrong or unproven, and where each is tracked>
   **Next slice:** <one slice, its lane, its model, and the one thing to read first>
   ```

   It must stand alone: everything the next session needs is in this one comment, and it never
   says "see above" or "as discussed".
3. Show the draft. Then post it with
   `gh issue comment <n> --body-file <file>` and print the comment URL. If there is no tracking
   issue, save it to `.claude/handoff.md` in the repo instead and say where it is;
   `/lanes:slice-boot` reads that file when it finds no issue. Commit it with the slice so the
   next checkout has it, or ignore it in git if the repo is shared and the record is yours.
4. If the slice is done and the issue's checklist has its box, tick it in the issue body. Close
   the issue only if its done-when gate has passed, and quote the gate when you do.
