export const meta = {
  name: 'lane-h-review',
  description: 'High-risk review panel: three finders with named angles, then one verifier per candidate (at most six) who may dismiss a finding only by quoting the line that makes it impossible, then every quoted line re-read at the head commit',
  whenToUse: 'The adversarial review of a high-risk (Lane H) change, on the delta only, in a throwaway checkout at the head commit. Not for mechanical or standard changes.',
  phases: [
    { title: 'Find', detail: 'three finders, one named angle each' },
    { title: 'Verify', detail: 'one verifier per candidate, a quoted line to dismiss' },
    { title: 'Check', detail: 'each dismissal: the quoted line is re-read at the head commit' },
  ],
}

// The adversarial stage of a high-risk review. A single reviewer, however fresh, is asked
// "what is wrong here?"; this panel adds a second stage that tries to kill every candidate
// and may drop one only by quoting the line that makes it impossible. Being unconvinced is
// not a dismissal. That inverted burden of proof is what the panel is for. A third stage
// re-reads every quoted line at the head commit, so a verifier cannot dismiss a finding by
// quoting a line from its own edited copy, or one that is not there.
//
// Launch it from the session that coordinates the work (working solo: once the build is
// committed), never from a build session on its own change. Every agent below starts fresh, so
// the review never runs in the context that built or coordinated the change.
//   1. git -C <repo> worktree add --detach <scratch>/lhr-tree <head sha>
//   2. Run this workflow with args {tree, head, base, brief}: typed, /lanes:lane-h-review
//      followed by the arguments as a JSON object, or as key=value pairs (quote a value that
//      has spaces: brief="..."); from a session, the Workflow tool with the name your
//      Claude Code lists for it (check /workflows; 'lanes:lane-h-review' on ours)
//        tree            absolute path of that throwaway checkout
//        head            the full sha the checkout is at
//        base            the full sha the delta starts from; the panel reads base...head
//        files           optional paths to scope to (typed: comma-separated); with no base, those
//                        files as they stand at head
//        brief           optional: what the change claims to do, and where its spec lives
//        angles          optional: replace the three finder angles, [{key, title, ask}], one to five
//                        (JSON form only)
//        max_candidates  optional: how many candidates get a verifier, 1 to 10 (default 6)
//        model           optional: the model every agent runs on (default 'opus')
//   3. git -C <repo> worktree remove --force for that checkout and any <tree>.<role> an agent left
// Before trusting the result, read `complete` and `counts`. Record LABEL and counts.agents_sent
// with the review: an unrun or half-run review prints nothing, so the record is the evidence.

const MAX_PER_FINDER = 4
const SEVERITY_RANK = { high: 0, medium: 1, low: 2 }
const SHA = /^[0-9a-f]{40}$/
// A dismissal counts only when the quote STARTS with a location (a path with a slash, a dotfile,
// file.ext, or a known name such as Makefile), then :LINE, then that line's text. So "checked at
// 10:30 and it is fine" and prose that merely names a line are not quotes. The path is relative
// to the checkout root: an absolute path, or one that climbs out with "..", is not a quote,
// because a verifier's own copy of the tree (<tree>.verifier-N) is not the reviewed commit.
// A reproduction that is empty or "none" backs no confirmation.
const QUOTED_LINE = /^\s*[`'"(]?((?:[\w.@+-]+\/)+[\w.@+-]+|\.[\w@+-][\w.@+-]*|[\w@+-][\w.@+-]*\.[A-Za-z]\w*|Makefile|Dockerfile|Containerfile|Gemfile|Rakefile|Procfile|Justfile|Vagrantfile|Jenkinsfile|BUILD|WORKSPACE):(\d+)\S*[ \t]+(\S[^\n]*)/
const NO_COMMAND = /^\s*(none\.?)?\s*$/i
const parseQuote = quote => {
  const m = QUOTED_LINE.exec(quote || '')
  if (!m) return null
  const path = m[1]
  if (path.split('/').includes('..')) return null
  return { path, line: Number(m[2]), text: m[3].trim().replace(/^[`'"]+|[`'"]+$/g, '').trim() }
}
const squash = s => String(s || '').replace(/\s+/g, ' ').trim()

const DEFAULT_ANGLES = [
  {
    key: 'guards',
    title: 'guards and their consumers',
    ask: 'Every condition, filter, gate, guard, default, exception path and return shape the scope adds or changes. For each, find the input that makes it wrong, and search for every consumer of the changed name, value or contract, not only the one it was written for: a guard narrowed for one consumer moves the defect to the next.',
  },
  {
    key: 'tests',
    title: 'tests that cannot fail',
    ask: 'Every test the scope adds or changes, and every claim that a test proves something. For each, would it go red if the code it protects were reverted or broken? Look for a test that passes by sort order, by a fixture that never reaches the path, by a skip, by asserting its own mock, or by a filter that selects nothing. Where you can, prove it: revert or mutate the protected lines in your own checkout and run the test.',
  },
  {
    key: 'harm',
    title: 'what leaves the building',
    ask: 'Where the scope can delete, overwrite, truncate or skip data without saying so; serve a value, a claim or a word that the stored data or the tests\' expected values do not support; or widen access to personal data, credentials or an authenticated surface. Follow each write, each served value and each access check from the scope to where it lands.',
  },
]

// Typed after the command, args arrive as one string: a JSON object, or key=value pairs.
const parseArgs = raw => {
  if (raw === undefined || raw === null) return {}
  if (typeof raw !== 'string') return raw
  const text = raw.trim()
  if (!text) return {}
  if (text.startsWith('{')) {
    try { return JSON.parse(text) } catch (e) { throw new Error(`args: not valid JSON (${e.message})`) }
  }
  const out = {}
  const pair = /([a-z_]+)=(?:"((?:[^"\\]|\\.)*)"|'([^']*)'|(\S+))/g
  let m, used = ''
  while ((m = pair.exec(text))) {
    const value = m[2] !== undefined ? m[2].replace(/\\(.)/g, '$1') : m[3] !== undefined ? m[3] : m[4]
    if (m[1] in out) throw new Error(`args: ${m[1]} is given twice`)
    out[m[1]] = m[1] === 'files' ? value.split(',')
      : m[1] === 'max_candidates' && /^\d+$/.test(value) ? Number(value) : value
    used += m[0]
  }
  if (!used || text.replace(pair, '').trim()) throw new Error('args: give a JSON object, or key=value pairs such as tree=/abs/path head=<sha> base=<sha> brief="..."')
  return out
}
const a = parseArgs(args)
const KNOWN = ['tree', 'head', 'base', 'files', 'brief', 'angles', 'max_candidates', 'model']
if (!a || typeof a !== 'object' || Array.isArray(a)) throw new Error('args: give an object such as {tree, head, base, brief}')
const unknown = Object.keys(a).filter(k => !KNOWN.includes(k))
if (unknown.length) throw new Error(`args: unknown ${unknown.join(', ')}; the arguments are ${KNOWN.join(', ')}`)
if (a.files !== undefined && !(Array.isArray(a.files) && a.files.every(f => typeof f === 'string'))) throw new Error('args.files: a list of paths (typed: comma-separated)')
if (typeof a.tree !== 'string' || !a.tree.startsWith('/')) throw new Error('args.tree: the absolute path of a throwaway checkout at the head commit')
if (!SHA.test(a.head || '')) throw new Error('args.head: the full 40-character sha the checkout is at')
if (a.base !== undefined && !SHA.test(a.base)) throw new Error('args.base: a full 40-character sha')
if (a.base === a.head) throw new Error('args.base equals args.head: the delta is empty')
const files = (a.files || []).map(f => f.trim()).filter(Boolean)
if (!a.base && !files.length) throw new Error('give args.base (review base...head) or args.files (review those files as they stand at head)')

const ANGLES = a.angles === undefined ? DEFAULT_ANGLES : a.angles
if (!Array.isArray(ANGLES) || ANGLES.length < 1 || ANGLES.length > 5) throw new Error('args.angles: one to five angles, each {key, title, ask}')
ANGLES.forEach((g, i) => {
  if (!g || ![g.key, g.title, g.ask].every(s => typeof s === 'string' && s.trim())) throw new Error(`args.angles[${i}]: needs non-empty key, title and ask`)
  if (!/^[a-z0-9-]+$/.test(g.key)) throw new Error(`args.angles[${i}].key: lower-case letters, digits and hyphens only`)
})
if (new Set(ANGLES.map(g => g.key)).size !== ANGLES.length) throw new Error('args.angles: keys must be distinct')

const MAX_CANDIDATES = a.max_candidates === undefined ? 6 : a.max_candidates
if (!Number.isInteger(MAX_CANDIDATES) || MAX_CANDIDATES < 1 || MAX_CANDIDATES > 10) throw new Error('args.max_candidates: a whole number from 1 to 10')
const MODEL = a.model === undefined ? 'opus' : a.model
if (typeof MODEL !== 'string' || !MODEL.trim()) throw new Error('args.model: a model name such as opus')

const LABEL = `lane-h-review v2 (lanes plugin, ${MODEL}) → ${ANGLES.length} finders, one named angle each → ≤${MAX_CANDIDATES} candidates → 1 verifier each, a quoted line to dismiss → each quoted line re-read at head`
if (/haiku|sonnet|fast/i.test(MODEL)) log(`the panel is running on ${MODEL}: a fast tier dismisses less carefully, so read every dismissal yourself`)

const tree = a.tree.replace(/\/+$/, '')
const shellQuote = s => `'${s.replace(/'/g, `'\\''`)}'`
const T = shellQuote(tree)
const pathspec = files.length ? ' -- ' + files.map(shellQuote).join(' ') : ''
const SCOPE = a.base
  ? `Scope: the delta, \`git -C ${T} diff ${a.base}...HEAD${pathspec}\`. Code outside it matters only as a caller or consumer of what it changes.`
  : `Scope: these files as they stand at the checkout's HEAD, read whole (there is no diff): ${files.join(', ')}.`
const BRIEF = a.brief ? `What the change claims to do: ${a.brief}` : ''

const rules = role => '- ' + [
  `Checkout: ${tree}. First run \`git -C ${T} rev-parse HEAD\` and report exactly what it prints as head_seen.`,
  `Other agents read that checkout at the same time: never edit, check out, stash or reset in it. To run anything against changed code, make your own checkout with \`git -C ${T} worktree add --detach ${shellQuote(tree + '.' + role)} HEAD\` (if that path already exists, a previous run left it: remove it first), change it there, and remove it with \`git -C ${T} worktree remove --force ${shellQuote(tree + '.' + role)}\` when done.`,
  'Make sure every command you run executes the code in your checkout, not an installed copy elsewhere: print something that proves which copy ran, and clear build caches after reverting a change.',
  'Your brief is complete: do not read the project\'s onboarding docs, plans or memory files. Read the scope and what it touches, nothing wider.',
  'Nothing that reaches production or a shared service: no push, no commit, no cloud accounts, no production or shared database, no writes to the code host or the issue tracker.',
].join('\n- ')

const FINDINGS = {
  type: 'object',
  properties: {
    head_seen: { type: 'string', description: 'what `git rev-parse HEAD` printed in the checkout' },
    files_read: { type: 'array', items: { type: 'string' }, description: 'the files in scope you read, as paths relative to the checkout root; empty if the scope showed nothing' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          severity: { type: 'string', enum: ['high', 'medium', 'low'] },
          file: { type: 'string', description: 'path relative to the checkout root' },
          line: { type: 'integer' },
          title: { type: 'string', description: 'the defect, in one line' },
          failure: { type: 'string', description: 'the concrete input or state, and the wrong outcome' },
          evidence: { type: 'string', description: 'the lines read or the command run, and what it showed' },
        },
        required: ['severity', 'file', 'line', 'title', 'failure', 'evidence'],
      },
    },
  },
  required: ['head_seen', 'files_read', 'findings'],
}

const VERDICT = {
  type: 'object',
  properties: {
    head_seen: { type: 'string', description: 'what `git rev-parse HEAD` printed in the checkout' },
    verdict: {
      type: 'string',
      enum: ['confirmed', 'stands', 'dismissed'],
      description: 'confirmed: a command showed the failure. stands: neither shown nor disproved. dismissed: a quoted line makes it impossible.',
    },
    quote: { type: 'string', description: 'to dismiss: starts with the path relative to the checkout root, :LINE, then the exact text of the line that makes the failure impossible (src/db.py:42 if not rows: return []); otherwise empty' },
    reproduction: { type: 'string', description: 'the command run and what it printed, or "none"' },
    severity: { type: 'string', enum: ['high', 'medium', 'low'] },
    reason: { type: 'string' },
  },
  required: ['head_seen', 'verdict', 'quote', 'reproduction', 'severity', 'reason'],
}

const finderPrompt = (g, i) => [
  '`' + LABEL + '`',
  `You are finder ${i + 1} of ${ANGLES.length} on a high-risk review panel. Your one angle: ${g.title}.`,
  BRIEF,
  SCOPE,
  g.ask,
  `Report at most ${MAX_PER_FINDER} findings, most severe first, each tied to a file and line in the checkout. A finding names the concrete input or state and the wrong outcome. Real defects only: no style, no naming, no "consider". An empty list is a valid answer. List in files_read every file in scope you read; if the scope command shows nothing, return files_read empty rather than reviewing something else.`,
  'Rules:\n' + rules(`finder-${g.key}`),
].filter(Boolean).join('\n\n')

const verifierPrompt = (f, i, n) => [
  '`' + LABEL + '`',
  `You are verifier ${i + 1} of ${n} on a high-risk review panel, on the candidate at ${f.file}:${f.line}. ${f.reports.length === 1 ? 'One finder reported it:' : `${f.reports.length} reports name this line, and you rule on them together:`}`,
  f.reports.map(r => `- from the finder on ${r.angle}, severity ${r.severity}: ${r.title}\n  failure: ${r.failure}\n  finder's evidence: ${r.evidence}`).join('\n'),
  BRIEF,
  SCOPE,
  'The burden is on dismissal. The candidate stands unless you quote the line of code that makes the failure impossible: the quote starts with the path relative to the checkout root, then :LINE, then the exact text of that line as it stands in the shared checkout at HEAD, and nothing after it: put your reasoning in reason, not in the quote (never a line from your own copy, and never an absolute path; the line is re-read at HEAD after you answer, and a quote that is not there, or only a fragment of it, turns your dismissal into "stands"); where several reports name the line, it stands if any one of them does, so a dismissal must answer every one. Being unconvinced, finding it unlikely, or seeing no test for it is not a dismissal. Where a command can show the failure, run it in your own checkout and report the command and what it printed: a candidate shown that way is confirmed. Give the severity you would put on it.',
  'Rules:\n' + rules(`verifier-${i + 1}`),
].filter(Boolean).join('\n\n')

phase('Find')
const found = await parallel(ANGLES.map((g, i) => () =>
  agent(finderPrompt(g, i), { label: `finder:${g.key}`, phase: 'Find', schema: FINDINGS, model: MODEL })
    .then(r => r && { ...r, angle: g.title })))

const returned = found.filter(Boolean)
const wrongTree = returned.filter(r => squash(r.head_seen) !== a.head)
if (wrongTree.length) throw new Error(`a finder saw HEAD ${squash(wrongTree[0].head_seen)} in ${tree}, not ${a.head}: check out the head commit and run again`)
if (returned.length < ANGLES.length) log(`${ANGLES.length - returned.length} of ${ANGLES.length} finders returned nothing: this run is incomplete`)
const blind = returned.filter(r => !(r.files_read || []).length)
if (returned.length && blind.length === returned.length) throw new Error('no finder read a file in scope: the delta is empty or the paths do not exist')
if (blind.length) log(`${blind.length} finders read no file in scope: this run is incomplete`)

// Pool every finder's list into one candidate per file:line, keeping every report at that
// line for its verifier; rank by the most severe report, then cap. Each finder's first
// MAX_PER_FINDER findings compete for verifiers, so one finder that ignores its limit cannot
// crowd the other angles out; what it returned past the limit is not dropped but returned as
// over_cap, unverified. Ties within a severity go round-robin across finders (every finder's
// first finding before any finder's second), so no angle is always the first cut. The cap
// needs every finder's list at once, so this stage is a barrier on purpose.
const overLimit = returned.filter(r => r.findings.length > MAX_PER_FINDER)
if (overLimit.length) log(`${overLimit.length} finders returned more than ${MAX_PER_FINDER} findings; the rest are returned as over_cap, unverified`)
const pastLimit = returned.flatMap(r => r.findings.slice(MAX_PER_FINDER).map(f => ({ file: f.file, line: f.line, severity: f.severity, angles: [r.angle], reports: [{ angle: r.angle, severity: f.severity, title: f.title, failure: f.failure, evidence: f.evidence }], past_finder_limit: true })))
const byLine = new Map()
returned.forEach((r, fi) => r.findings.slice(0, MAX_PER_FINDER).forEach((f, j) => {
  const key = `${f.file}:${f.line}`
  const report = { angle: r.angle, severity: f.severity, title: f.title, failure: f.failure, evidence: f.evidence }
  const seen = byLine.get(key)
  if (!seen) byLine.set(key, { file: f.file, line: f.line, severity: f.severity, angles: [r.angle], reports: [report], order: j * 100 + fi })
  else {
    seen.reports.push(report)
    if (!seen.angles.includes(r.angle)) seen.angles.push(r.angle)
    if (SEVERITY_RANK[f.severity] < SEVERITY_RANK[seen.severity]) seen.severity = f.severity
  }
}))
const ranked = [...byLine.values()].sort((x, y) => SEVERITY_RANK[x.severity] - SEVERITY_RANK[y.severity] || x.order - y.order)
const candidates = ranked.slice(0, MAX_CANDIDATES)
const overCap = [...ranked.slice(MAX_CANDIDATES), ...pastLimit]
if (overCap.length) log(`${overCap.length} candidates over the cap of ${MAX_CANDIDATES} were not verified; they are returned as over_cap, unverified rather than cleared`)

phase('Verify')
const verdicts = await parallel(candidates.map((f, i) => () =>
  agent(verifierPrompt(f, i, candidates.length), { label: `verifier:${f.file}:${f.line}`, phase: 'Verify', schema: VERDICT, model: MODEL })))

const judged = candidates.map((f, i) => {
  const v = verdicts[i]
  const { order, ...finding } = f
  if (!v) return { ...finding, verdict: 'unverified', reason: 'the verifier returned nothing' }
  if (squash(v.head_seen) !== a.head) return { ...finding, verdict: 'unverified', reason: `the verifier saw HEAD ${squash(v.head_seen)}, not ${a.head}` }
  const parsed = v.verdict === 'dismissed' ? parseQuote(v.quote) : null
  const unquoted = v.verdict === 'dismissed' && !parsed
  const unshown = v.verdict === 'confirmed' && NO_COMMAND.test(v.reproduction || '')
  const why = unquoted ? 'a dismissal without a quoted path:line and its text, relative to the checkout root, does not count. '
    : unshown ? 'a confirmation with no command behind it counts as standing. ' : ''
  return {
    ...finding,
    verdict: why ? 'stands' : v.verdict,
    verified_severity: v.severity,
    quote: v.quote,
    quoted: parsed || undefined,
    reproduction: v.reproduction,
    reason: why + v.reason,
  }
})

// Every dismissal rests on one quoted line. A checker re-reads that line at the head commit
// in the shared checkout and reports what git printed, so the quote is checked against the
// reviewed commit rather than taken from the verifier. The checker runs one command and
// judges nothing; the comparison is done here.
const CHECK = {
  type: 'object',
  properties: {
    head_seen: { type: 'string', description: 'what `git rev-parse HEAD` printed in the checkout' },
    printed: { type: 'string', description: 'exactly what the show command printed, verbatim; empty if it printed nothing or failed' },
    error: { type: 'string', description: 'the error text if the command failed, otherwise empty' },
  },
  required: ['head_seen', 'printed', 'error'],
}
// The checker is not told what the verifier quoted: it reports what git printed for a path
// and line, and the comparison happens here, so it cannot echo the expected answer.
const checkerPrompt = f => [
  '`' + LABEL + '`',
  'You are a checker on a high-risk review panel. You read one line of one file at one commit and report it. You judge nothing.',
  `Run exactly these two commands and report their output verbatim. Run nothing else, read nothing else, edit nothing.\n1. \`git -C ${T} rev-parse HEAD\` → head_seen\n2. \`git -C ${T} show ${a.head}:${shellQuote(f.quoted.path)} | sed -n ${shellQuote(f.quoted.line + 'p')}\` → printed (the one line it prints, with its leading spaces; empty if it prints nothing). If the command fails, put the error text in error.`,
  `Rules:\n- Other agents read ${tree} at the same time: never edit, check out, stash or reset in it, and make no worktree.\n- Nothing that reaches production or a shared service: no push, no commit, no cloud accounts, no writes to the code host or the issue tracker.`,
].join('\n\n')

const toCheck = judged.filter(f => f.verdict === 'dismissed')
phase('Check')
const checks = await parallel(toCheck.map(f => () =>
  agent(checkerPrompt(f), { label: `checker:${f.file}:${f.line}`, phase: 'Check', schema: CHECK, model: MODEL })))

const settled = judged.map(f => {
  const i = toCheck.indexOf(f)
  if (i < 0) return f
  const c = checks[i]
  if (!c) return { ...f, verdict: 'unverified', reason: `the quoted line could not be re-read at head (the checker returned nothing). ${f.reason}` }
  if (squash(c.head_seen) !== a.head) return { ...f, verdict: 'unverified', reason: `the checker saw HEAD ${squash(c.head_seen)}, not ${a.head}. ${f.reason}` }
  const printed = squash(c.printed)
  const quoted = squash(f.quoted.text)
  // The quote is there when it is the line or at least half of it, either way round: a lone
  // bracket or a bare `return` is not a quote of the line, and a line that is only a short
  // piece of a long quote is not that quote. Words after the line make the quote fail; the
  // verifier is told to put nothing after it, and a false "stands" is the safe direction.
  const there = printed.length > 0 && quoted.length > 0 && (
    (printed.includes(quoted) && quoted.length * 2 >= printed.length)
    || (quoted.includes(printed) && printed.length * 2 >= quoted.length))
  if (!there) return { ...f, verdict: 'stands', line_at_head: c.printed, reason: `the quoted line is not at ${f.quoted.path}:${f.quoted.line} in the reviewed commit (git printed: ${JSON.stringify(c.printed)}${c.error ? '; error: ' + c.error : ''}), so the dismissal does not count. ${f.reason}` }
  return { ...f, line_at_head: c.printed }
})

return {
  label: LABEL,
  model: MODEL,
  tree, head: a.head, base: a.base || null, files,
  angles: ANGLES.map(g => g.title),
  counts: {
    agents_sent: ANGLES.length + candidates.length + toCheck.length,
    finders_sent: ANGLES.length,
    finders_returned: returned.length,
    finders_blind: blind.length,
    candidates: ranked.length,
    verifiers_sent: candidates.length,
    verifiers_returned: verdicts.filter(Boolean).length,
    checkers_sent: toCheck.length,
    checkers_returned: checks.filter(Boolean).length,
    confirmed: settled.filter(f => f.verdict === 'confirmed').length,
    stands: settled.filter(f => f.verdict === 'stands').length,
    dismissed: settled.filter(f => f.verdict === 'dismissed').length,
    unverified: settled.filter(f => f.verdict === 'unverified').length + overCap.length,
  },
  // Complete only when every finder read its scope, every candidate got a valid verdict, and
  // every dismissal's quoted line was re-read at head. Over-cap candidates make it incomplete:
  // they need a written disposition from a person before the review is whole.
  complete: returned.length === ANGLES.length && blind.length === 0
    && settled.every(f => f.verdict !== 'unverified') && overCap.length === 0,
  findings: settled,
  over_cap: overCap.map(({ order, ...f }) => f),
}
