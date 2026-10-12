// Runs a workflow script with stand-in agents, so its control logic can be tested without a
// model. Usage: node workflow_harness.mjs <script.js> <case.json>
// case.json: {args, responses: {<agent label>: <structured result or null>}}
// Prints one JSON line: {ok, result | error, calls: [{label, model, phase}], logs, phases, meta}.
import { readFileSync } from 'node:fs'

const [scriptPath, casePath] = process.argv.slice(2)
const source = readFileSync(scriptPath, 'utf8')
const testCase = JSON.parse(readFileSync(casePath, 'utf8'))

const body = source.replace(/^export const meta\s*=/m, 'const meta =')
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor
const run = new AsyncFunction('args', 'agent', 'parallel', 'phase', 'log', body + '\n')
const metaOnly = new Function(source.slice(0, source.indexOf('\n}\n') + 3).replace(/^export const meta\s*=/m, 'return'))

const calls = []
const logs = []
const phases = []
const agent = async (prompt, opts = {}) => {
  calls.push({ label: opts.label, model: opts.model, phase: opts.phase, prompt })
  const r = testCase.responses[opts.label]
  return r === undefined ? null : r
}
const parallel = async thunks => Promise.all(thunks.map(t => Promise.resolve().then(t).catch(() => null)))

let out
try {
  const result = await run(testCase.args, agent, parallel, t => phases.push(t), m => logs.push(m))
  out = { ok: true, result }
} catch (e) {
  out = { ok: false, error: String(e && e.message || e) }
}
out.calls = calls
out.logs = logs
out.phases = phases
out.meta = metaOnly()
process.stdout.write(JSON.stringify(out) + '\n')
