"""Checks for the lanes plugin: manifests, skill and command files, and the review panel's logic.

The panel tests run workflows/lane-h-review.js under Node with stand-in agents
(tests/workflow_harness.mjs), so the rules that make the panel trustworthy are tested without a
model: a dismissal needs a quoted line, a confirmation needs a command, an incomplete run says so.
"""
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_DIR = os.path.join(ROOT, "skills", "lanes")
WORKFLOW = os.path.join(ROOT, "workflows", "lane-h-review.js")
HARNESS = os.path.join(ROOT, "tests", "workflow_harness.mjs")
NODE = shutil.which("node")

HEAD = "a" * 40
BASE = "b" * 40


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None
    fields = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
    return fields


def read_path(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def public_files():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in (".git", "results", "__pycache__")]
        for name in filenames:
            if name.endswith((".md", ".js", ".mjs", ".json", ".py", ".yml")):
                yield os.path.join(dirpath, name)


class ManifestTests(unittest.TestCase):
    def test_manifests_parse_and_agree(self):
        plugin = json.loads(read(".claude-plugin", "plugin.json"))
        market = json.loads(read(".claude-plugin", "marketplace.json"))
        self.assertEqual(plugin["name"], "lanes")
        self.assertRegex(plugin["version"], r"^\d+\.\d+\.\d+$")
        self.assertIn(plugin["name"], [p["name"] for p in market["plugins"]])

    def test_changelog_names_the_manifest_version(self):
        version = json.loads(read(".claude-plugin", "plugin.json"))["version"]
        self.assertIn("## " + version, read("CHANGELOG.md"))


class SkillTests(unittest.TestCase):
    def test_skill_frontmatter(self):
        fields = frontmatter(read("skills", "lanes", "SKILL.md"))
        self.assertIsNotNone(fields)
        self.assertEqual(fields["name"], "lanes")
        self.assertTrue(fields["description"].startswith("Use when"))
        self.assertLessEqual(len(fields["description"]), 1024)

    def test_skill_stays_under_its_word_budget(self):
        words = len(read("skills", "lanes", "SKILL.md").split())
        self.assertLessEqual(words, 1500, "SKILL.md is loaded whole; move detail to a reference file")

    def test_every_linked_reference_exists(self):
        text = read("skills", "lanes", "SKILL.md")
        links = re.findall(r"\]\(([\w.-]+\.md)\)", text)
        self.assertTrue(links)
        for link in links:
            self.assertTrue(os.path.exists(os.path.join(SKILL_DIR, link)), link)

    def test_commands_have_descriptions(self):
        for name in os.listdir(os.path.join(ROOT, "commands")):
            fields = frontmatter(read("commands", name))
            self.assertIsNotNone(fields, name)
            self.assertTrue(fields.get("description"), name)


class EvalTests(unittest.TestCase):
    """Every eval case has the shape `claude plugin eval` reads; nothing else checks it."""

    def cases(self):
        root = os.path.join(ROOT, "evals")
        return sorted(d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d, "graders")))

    def test_every_case_has_a_prompt_and_a_scored_grader(self):
        names = self.cases()
        self.assertGreaterEqual(len(names), 4)
        for name in names:
            prompt = frontmatter(read("evals", name, "prompt.md"))
            self.assertIsNotNone(prompt, name)
            self.assertTrue(prompt["max_turns"].isdigit(), name)
            self.assertIn("Skill", prompt["allowed_tools"], f"{name}: the skill cannot fire without the Skill tool")
            graders = os.listdir(os.path.join(ROOT, "evals", name, "graders"))
            types = {}
            for g in graders:
                fields = frontmatter(read("evals", name, "graders", g))
                self.assertIsNotNone(fields, f"{name}/{g}")
                types[g] = fields["type"]
            self.assertIn("llm", types.values(), f"{name}: no rubric grader")
            self.assertIn("tool_used", types.values(), f"{name}: no skill-fired grader")

    def test_the_readme_names_every_case(self):
        readme = read("README.md")
        for name in self.cases():
            self.assertIn(name, readme, f"{name} is not in the README's scenario list")


class PublicTextTests(unittest.TestCase):
    """Nothing machine-specific or tracker-specific leaks into the published files."""

    def test_no_home_directory_paths(self):
        for path in public_files():
            text = read_path(path)
            self.assertIsNone(re.search(r"/(Users|home)/[A-Za-z]", text), path)

    def test_no_bare_issue_numbers(self):
        for path in public_files():
            text = read_path(path)
            self.assertIsNone(re.search(r"(?<![\w&])#\d{3,}\b", text), path)

    def test_the_company_is_named_once_in_the_readme_manifesto_link(self):
        name = "celo" + "rus"  # built, so this file does not contain it
        hits = []
        for dirpath, dirnames, filenames in os.walk(ROOT):
            dirnames[:] = [d for d in dirnames if d not in (".git", "results", "__pycache__")]
            for fname in filenames:
                path = os.path.join(dirpath, fname)
                with open(path, encoding="utf-8", errors="replace") as f:
                    for line in f:
                        if name in line.lower():
                            hits.append((os.path.relpath(path, ROOT), line.strip()))
        self.assertEqual(len(hits), 1, hits)
        self.assertEqual(hits[0][0], "README.md")
        self.assertIn(f"(https://{name}.com/manifesto)", hits[0][1])


@unittest.skipUnless(NODE, "node is not installed")
class PanelTests(unittest.TestCase):
    def run_panel(self, args, responses):
        with tempfile.TemporaryDirectory() as tmp:
            case = os.path.join(tmp, "case.json")
            with open(case, "w", encoding="utf-8") as f:
                json.dump({"args": args, "responses": responses}, f)
            proc = subprocess.run([NODE, HARNESS, WORKFLOW, case], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    @staticmethod
    def finder(findings, files_read=("app.py",), head=HEAD):
        return {"head_seen": head, "files_read": list(files_read), "findings": findings}

    @staticmethod
    def finding(path, line, severity="high", title="defect"):
        return {"severity": severity, "file": path, "line": line, "title": title,
                "failure": "input x gives wrong y", "evidence": "read the lines"}

    @staticmethod
    def verdict(verdict, quote="", reproduction="none", head=HEAD):
        return {"head_seen": head, "verdict": verdict, "quote": quote,
                "reproduction": reproduction, "severity": "high", "reason": "because"}

    @staticmethod
    def check(printed, head=HEAD, error=""):
        """What the checker reports after re-reading the quoted line at head."""
        return {"head_seen": head, "printed": printed, "error": error}

    def args(self, **extra):
        return dict({"tree": "/tmp/tree", "head": HEAD, "base": BASE}, **extra)

    def test_node_parses_the_script(self):
        out = self.run_panel(self.args(), {})
        self.assertTrue(out["meta"]["name"])
        self.assertEqual([p["title"] for p in out["meta"]["phases"]], ["Find", "Verify", "Check"])

    def test_phase_calls_match_meta(self):
        out = self.run_panel(self.args(), {
            "finder:guards": self.finder([]), "finder:tests": self.finder([]), "finder:harm": self.finder([]),
        })
        self.assertTrue(out["ok"], out.get("error"))
        self.assertEqual(out["phases"], [p["title"] for p in out["meta"]["phases"]])

    def test_rejects_missing_or_bad_arguments(self):
        cases = [
            ({"head": HEAD, "base": BASE}, "args.tree"),
            ({"tree": "relative/path", "head": HEAD, "base": BASE}, "args.tree"),
            ({"tree": "/t", "head": "abc", "base": BASE}, "args.head"),
            ({"tree": "/t", "head": HEAD, "base": HEAD}, "delta is empty"),
            ({"tree": "/t", "head": HEAD}, "args.base"),
            (self.args(max_candidates=0), "max_candidates"),
            (self.args(angles=[]), "args.angles"),
            (self.args(angles=[{"key": "Bad Key", "title": "t", "ask": "a"}]), "key"),
        ]
        for args, expected in cases:
            out = self.run_panel(args, {})
            self.assertFalse(out["ok"], args)
            self.assertIn(expected, out["error"])
            self.assertEqual(out["calls"], [], "no agent is sent on bad arguments")

    def test_burden_of_proof_is_enforced(self):
        out = self.run_panel(self.args(), {
            "finder:guards": self.finder([self.finding("app.py", 10), self.finding("src/db.py", 3, "medium")]),
            "finder:tests": self.finder([self.finding("app.py", 10, "low", "same line, other angle"),
                                         self.finding("tests/test_db.py", 7, "medium")]),
            "finder:harm": self.finder([self.finding("src/api.py", 22, "low")]),
            # quoted line at the repo root: a valid dismissal
            "verifier:app.py:10": self.verdict("dismissed", quote="app.py:12 if x is None: return 0"),
            # dismissal without a quoted line: does not count
            "verifier:src/db.py:3": self.verdict("dismissed", quote="looks fine to me"),
            # confirmation with no command behind it: does not count
            "verifier:tests/test_db.py:7": self.verdict("confirmed", reproduction="none"),
            "verifier:src/api.py:22": self.verdict("confirmed", reproduction="pytest -k api: 1 failed"),
            # the quoted line, re-read at head by a checker that runs one command
            "checker:app.py:10": self.check("    if x is None: return 0"),
        })
        self.assertTrue(out["ok"], out.get("error"))
        r = out["result"]
        by = {f"{f['file']}:{f['line']}": f for f in r["findings"]}
        self.assertEqual(len(by["app.py:10"]["reports"]), 2, "two reports on one line pool into one candidate")
        self.assertEqual(by["app.py:10"]["verdict"], "dismissed")
        self.assertEqual(by["app.py:10"]["quoted"], {"path": "app.py", "line": 12, "text": "if x is None: return 0"})
        self.assertEqual(by["src/db.py:3"]["verdict"], "stands")
        self.assertEqual(by["tests/test_db.py:7"]["verdict"], "stands")
        self.assertEqual(by["src/api.py:22"]["verdict"], "confirmed")
        self.assertTrue(r["complete"])
        self.assertEqual(r["counts"]["agents_sent"], 3 + 4 + 1)
        self.assertEqual(r["counts"]["checkers_sent"], 1)
        self.assertEqual(r["model"], "opus")
        self.assertIn("opus", r["label"], "the record names the model that ran the panel")
        checker_prompt = next(c["prompt"] for c in out["calls"] if c["label"] == "checker:app.py:10")
        self.assertIn(f"git -C '/tmp/tree' show {HEAD}:'app.py' | sed -n '12p'", checker_prompt)
        self.assertTrue(all(c["model"] == "opus" for c in out["calls"]))
        verifier_prompt = next(c["prompt"] for c in out["calls"] if c["label"] == "verifier:app.py:10")
        self.assertIn("2 reports name this line", verifier_prompt)
        self.assertIn("Being unconvinced", verifier_prompt)

    def test_only_a_file_and_line_with_its_text_counts_as_a_quote(self):
        quotes = {
            "checked at 10:30 and it is fine": "stands",
            "see line 12: it returns early": "stands",
            "Unconvinced: src/db.py:3 has no test for it, so unlikely": "stands",
            "the CI BUILD:3 passes so fine": "stands",
            "`src/db.py:3 if x is None: return`": "dismissed",
            "Makefile:4 test: lint": "dismissed",
            # an absolute path, or one that climbs out of the checkout, is a verifier's own
            # copy of the tree, not the reviewed commit: it never counts
            "/scratch/lhr-tree.verifier-1/src/db.py:42 if not rows: return []": "stands",
            "../lhr-tree.verifier-2/src/db.py:42 if not rows: return []": "stands",
            ".gitlab-ci.yml:5 only: [main]": "dismissed",
            "bin/deploy:12 set -euo pipefail": "dismissed",
        }
        findings = [self.finding(f"f{i}.py", i + 1) for i in range(len(quotes))]
        responses = {"finder:guards": self.finder(findings[:4]), "finder:tests": self.finder(findings[4:8]),
                     "finder:harm": self.finder(findings[8:])}
        for i, quote in enumerate(quotes):
            responses[f"verifier:f{i}.py:{i + 1}"] = self.verdict("dismissed", quote=quote)
            # every quoted line is there at head, so the checker cannot be the reason
            responses[f"checker:f{i}.py:{i + 1}"] = self.check(quote.split(" ", 1)[1].strip("`"))
        out = self.run_panel(self.args(max_candidates=10), responses)
        self.assertTrue(out["ok"], out.get("error"))
        got = {f["quote"]: f["verdict"] for f in out["result"]["findings"]}
        self.assertEqual(got, quotes)
        sent = {c["label"] for c in out["calls"] if c["label"].startswith("checker:")}
        self.assertEqual(len(sent), 4, "only a quote that parses is sent to a checker")

    def test_a_quote_not_at_head_turns_the_dismissal_into_stands(self):
        base = {"finder:guards": self.finder([self.finding("a.py", 1), self.finding("b.py", 2), self.finding("c.py", 3),
                                             self.finding("d.py", 4)]),
                "finder:tests": self.finder([]), "finder:harm": self.finder([]),
                "verifier:a.py:1": self.verdict("dismissed", quote="a.py:5 if not rows: return []"),
                "verifier:b.py:2": self.verdict("dismissed", quote="b.py:9 raise ValueError(x)"),
                "verifier:c.py:3": self.verdict("dismissed", quote="c.py:4   return total"),
                "verifier:d.py:4": self.verdict("dismissed", quote="d.py:8 if not rows and not cache.get(key): return []"),
                # the line at head is something else: the verifier quoted its own edit
                "checker:a.py:1": self.check("    if rows: return rows"),
                # the file or line is not there at head
                "checker:b.py:2": self.check("", error="fatal: path 'b.py' does not exist"),
                # the same line, with different whitespace: that is a match
                "checker:c.py:3": self.check("        return total"),
                # a short line that is only a piece of a long quote is not that line
                "checker:d.py:4": self.check("return []"),
                }
        out = self.run_panel(self.args(), base)
        self.assertTrue(out["ok"], out.get("error"))
        by = {f["file"]: f for f in out["result"]["findings"]}
        self.assertEqual(by["a.py"]["verdict"], "stands")
        self.assertIn("not at a.py:5 in the reviewed commit", by["a.py"]["reason"])
        self.assertEqual(by["b.py"]["verdict"], "stands")
        self.assertIn("does not exist", by["b.py"]["reason"])
        self.assertEqual(by["c.py"]["verdict"], "dismissed")
        self.assertEqual(by["c.py"]["line_at_head"], "        return total")
        self.assertEqual(by["d.py"]["verdict"], "stands")
        self.assertTrue(out["result"]["complete"], "a checked run is complete even when checks fail")
        self.assertEqual(out["result"]["counts"]["stands"], 3)
        for c in out["calls"]:
            if c["label"].startswith("checker:"):
                self.assertNotIn("worktree add", c["prompt"], "a checker makes no worktree")
                self.assertNotIn("if not rows", c["prompt"], "a checker is not told what the verifier quoted")

    def test_a_fragment_of_the_line_is_not_a_quote_of_it(self):
        cases = {
            # (quote text, line at head): verdict
            ("return", "    return unsafe_value"): "stands",
            (")", "foo(bar)"): "stands",
            # words after the line: the verifier was told to put nothing there; stands is the safe side
            ("if not rows: return []  -- this guards the empty case", "if not rows: return []"): "stands",
            ("'if not rows: return []'", "    if not rows: return []"): "dismissed",
            ("if not rows: return [] and more and more and more and more", "if not rows"): "stands",
        }
        findings, responses = [], {"finder:tests": self.finder([]), "finder:harm": self.finder([])}
        for i, ((text, at_head), _) in enumerate(cases.items()):
            findings.append(self.finding(f"q{i}.py", i + 1))
            responses[f"verifier:q{i}.py:{i + 1}"] = self.verdict("dismissed", quote=f"src/x.py:9 {text}")
            responses[f"checker:q{i}.py:{i + 1}"] = self.check(at_head)
        responses["finder:guards"] = self.finder(findings[:4])
        responses["finder:tests"] = self.finder(findings[4:])
        out = self.run_panel(self.args(max_candidates=10), responses)
        self.assertTrue(out["ok"], out.get("error"))
        got = [f["verdict"] for f in sorted(out["result"]["findings"], key=lambda f: f["file"])]
        self.assertEqual(got, list(cases.values()))

    def test_a_number_after_a_bare_word_is_not_a_quote(self):
        out = self.run_panel(self.args(), {
            "finder:guards": self.finder([self.finding("a.py", 1)]), "finder:tests": self.finder([]), "finder:harm": self.finder([]),
            "verifier:a.py:1": self.verdict("dismissed", quote="step:2 rejects it"),
        })
        self.assertEqual(out["result"]["findings"][0]["verdict"], "stands")
        self.assertEqual(out["result"]["counts"]["checkers_sent"], 0)

    def test_a_dismissal_whose_checker_returns_nothing_is_unverified(self):
        out = self.run_panel(self.args(), {
            "finder:guards": self.finder([self.finding("a.py", 1), self.finding("b.py", 2)]),
            "finder:tests": self.finder([]), "finder:harm": self.finder([]),
            "verifier:a.py:1": self.verdict("dismissed", quote="a.py:5 if not rows: return []"),
            "verifier:b.py:2": self.verdict("dismissed", quote="b.py:9 raise ValueError(x)"),
            "checker:b.py:2": self.check("raise ValueError(x)", head="c" * 40),
        })
        by = {f["file"]: f for f in out["result"]["findings"]}
        self.assertEqual(by["a.py"]["verdict"], "unverified")
        self.assertEqual(by["b.py"]["verdict"], "unverified", "a checker on the wrong commit proves nothing")
        self.assertFalse(out["result"]["complete"])
        self.assertEqual(out["result"]["counts"]["checkers_returned"], 1)

    def test_a_verifier_returning_nothing_is_unverified(self):
        out = self.run_panel(self.args(), {
            "finder:guards": self.finder([self.finding("a.py", 1)]),
            "finder:tests": self.finder([]), "finder:harm": self.finder([]),
        })
        f = out["result"]["findings"][0]
        self.assertEqual(f["verdict"], "unverified")
        self.assertFalse(out["result"]["complete"])
        self.assertEqual(out["result"]["counts"]["verifiers_returned"], 0)

    def test_an_empty_reproduction_counts_as_standing(self):
        out = self.run_panel(self.args(), {
            "finder:guards": self.finder([self.finding("a.py", 1)]),
            "finder:tests": self.finder([]), "finder:harm": self.finder([]),
            "verifier:a.py:1": self.verdict("confirmed", reproduction="   "),
        })
        self.assertEqual(out["result"]["findings"][0]["verdict"], "stands")

    def test_findings_past_the_fourth_are_pooled_not_dropped(self):
        six = [self.finding(f"g{i}.py", i, "low") for i in range(6)]
        out = self.run_panel(self.args(max_candidates=10), {
            "finder:guards": self.finder(six), "finder:tests": self.finder([]), "finder:harm": self.finder([]),
        })
        self.assertTrue(out["ok"], out.get("error"))
        r = out["result"]
        self.assertEqual(r["counts"]["candidates"], 4, "the first four compete for verifiers")
        self.assertEqual([f["file"] for f in r["over_cap"]], ["g4.py", "g5.py"], "the rest are returned unverified, not lost")
        self.assertTrue(all(f["past_finder_limit"] for f in r["over_cap"]))
        self.assertFalse(r["complete"])
        self.assertTrue(any("more than 4 findings" in m for m in out["logs"]))

    def test_an_over_limit_finder_cannot_crowd_the_other_angles_out(self):
        out = self.run_panel(self.args(), {
            "finder:guards": self.finder([self.finding(f"g{i}.py", i) for i in range(10)]),
            "finder:tests": self.finder([self.finding("t.py", 1, "medium")]),
            "finder:harm": self.finder([self.finding("h.py", 1, "medium")]),
        })
        verified = [f["file"] for f in out["result"]["findings"]]
        self.assertIn("t.py", verified)
        self.assertIn("h.py", verified)
        self.assertEqual(len(verified), 6)

    def test_ties_go_round_robin_across_finders(self):
        out = self.run_panel(self.args(max_candidates=3), {
            "finder:guards": self.finder([self.finding(f"g{i}.py", i) for i in range(4)]),
            "finder:tests": self.finder([self.finding(f"t{i}.py", i) for i in range(4)]),
            "finder:harm": self.finder([self.finding(f"h{i}.py", i) for i in range(4)]),
        })
        r = out["result"]
        self.assertEqual([f["file"] for f in r["findings"]], ["g0.py", "t0.py", "h0.py"],
                         "every finder's first finding is verified before any finder's second")
        self.assertEqual(len(r["over_cap"]), 9)

    def test_a_checkout_path_with_spaces_is_quoted(self):
        out = self.run_panel({"tree": "/tmp/my tree", "head": HEAD, "base": BASE}, {
            "finder:guards": self.finder([]), "finder:tests": self.finder([]), "finder:harm": self.finder([]),
        })
        self.assertTrue(out["ok"], out.get("error"))
        prompt = out["calls"][0]["prompt"]
        self.assertIn("git -C '/tmp/my tree' diff", prompt)
        self.assertIn("worktree add --detach '/tmp/my tree.finder-guards' HEAD", prompt)

    def test_a_fast_tier_model_is_warned_about(self):
        out = self.run_panel(self.args(model="sonnet"), {
            "finder:guards": self.finder([]), "finder:tests": self.finder([]), "finder:harm": self.finder([]),
        })
        self.assertTrue(any("fast tier" in m for m in out["logs"]))
        self.assertIn("sonnet", out["result"]["label"])

    def test_arguments_typed_after_the_command(self):
        empty = {"finder:guards": self.finder([]), "finder:tests": self.finder([]), "finder:harm": self.finder([])}
        typed = f'tree=/tmp/tree head={HEAD} base={BASE} files="app.py, src/db.py" max_candidates=2 brief="adds a guard"'
        out = self.run_panel(typed, empty)
        self.assertTrue(out["ok"], out.get("error"))
        self.assertEqual(out["result"]["files"], ["app.py", "src/db.py"])
        self.assertIn("adds a guard", out["calls"][0]["prompt"])
        self.assertIn("≤2 candidates", out["result"]["label"])
        out = self.run_panel(json.dumps(self.args()), empty)
        self.assertTrue(out["ok"], out.get("error"))
        good = f"tree=/tmp/tree head={HEAD} base={BASE}"
        bad_inputs = [
            ("please review my change", "key=value"),
            ("{not json", "JSON"),
            (good + " brief=adds a guard", "key=value"),     # unquoted spaces: not silently cut to "adds"
            (good + " max_candidate=3", "unknown max_candidate"),
            (good + f" base={BASE}", "base is given twice"),
            (self.args(files="app.py,src/db.py"), "args.files"),
            (self.args(breif="typo"), "unknown breif"),
        ]
        for bad, expected in bad_inputs:
            out = self.run_panel(bad, {})
            self.assertFalse(out["ok"], bad)
            self.assertIn(expected, out["error"])
            self.assertEqual(out["calls"], [])

    def test_the_label_names_this_runs_shape(self):
        angles = [{"key": k, "title": k, "ask": "look"} for k in ("one", "two")]
        out = self.run_panel(self.args(angles=angles, max_candidates=3),
                             {"finder:one": self.finder([]), "finder:two": self.finder([])})
        self.assertTrue(out["ok"], out.get("error"))
        self.assertIn("2 finders", out["result"]["label"])
        self.assertIn("≤3 candidates", out["result"]["label"])
        self.assertTrue(out["calls"][0]["prompt"].startswith("`" + out["result"]["label"]))

    def test_over_cap_candidates_are_unverified_not_cleared(self):
        out = self.run_panel(self.args(max_candidates=1), {
            "finder:guards": self.finder([self.finding("a.py", 1, "low"), self.finding("b.py", 2, "high")]),
            "finder:tests": self.finder([]), "finder:harm": self.finder([]),
            "verifier:b.py:2": self.verdict("confirmed", reproduction="run: failed"),
        })
        r = out["result"]
        self.assertEqual([f["file"] for f in r["findings"]], ["b.py"], "the most severe is verified first")
        self.assertEqual([f["file"] for f in r["over_cap"]], ["a.py"])
        self.assertFalse(r["complete"])
        self.assertEqual(r["counts"]["unverified"], 1)
        self.assertTrue(any("over the cap" in m for m in out["logs"]))

    def test_a_silent_finder_makes_the_run_incomplete(self):
        out = self.run_panel(self.args(), {"finder:guards": self.finder([]), "finder:tests": self.finder([])})
        r = out["result"]
        self.assertFalse(r["complete"])
        self.assertEqual(r["counts"]["finders_returned"], 2)

    def test_a_blind_finder_makes_the_run_incomplete(self):
        out = self.run_panel(self.args(), {
            "finder:guards": self.finder([]), "finder:tests": self.finder([]),
            "finder:harm": self.finder([], files_read=()),
        })
        self.assertFalse(out["result"]["complete"])

    def test_every_finder_blind_is_an_error(self):
        blind = self.finder([], files_read=())
        out = self.run_panel(self.args(), {"finder:guards": blind, "finder:tests": blind, "finder:harm": blind})
        self.assertFalse(out["ok"])
        self.assertIn("no finder read a file", out["error"])

    def test_wrong_checkout_is_an_error(self):
        out = self.run_panel(self.args(), {"finder:guards": self.finder([], head="c" * 40)})
        self.assertFalse(out["ok"])
        self.assertIn("check out the head commit", out["error"])

    def test_a_verifier_on_the_wrong_commit_leaves_the_candidate_unverified(self):
        out = self.run_panel(self.args(), {
            "finder:guards": self.finder([self.finding("a.py", 1)]),
            "finder:tests": self.finder([]), "finder:harm": self.finder([]),
            "verifier:a.py:1": self.verdict("dismissed", quote="a.py:1 x", head="c" * 40),
        })
        r = out["result"]
        self.assertEqual(r["findings"][0]["verdict"], "unverified")
        self.assertFalse(r["complete"])

    def test_custom_angles_and_model(self):
        angles = [{"key": "perf", "title": "performance", "ask": "Find the slow path."},
                  {"key": "docs", "title": "docs drift", "ask": "Find the stale claim."}]
        out = self.run_panel(self.args(angles=angles, model="sonnet"), {
            "finder:perf": self.finder([]), "finder:docs": self.finder([]),
        })
        r = out["result"]
        self.assertTrue(r["complete"])
        self.assertEqual(r["angles"], ["performance", "docs drift"])
        self.assertEqual({c["label"] for c in out["calls"]}, {"finder:perf", "finder:docs"})
        self.assertTrue(all(c["model"] == "sonnet" for c in out["calls"]))

    def test_files_scope_without_base(self):
        out = self.run_panel({"tree": "/tmp/tree", "head": HEAD, "files": ["it's.py"]}, {
            "finder:guards": self.finder([]), "finder:tests": self.finder([]), "finder:harm": self.finder([]),
        })
        self.assertTrue(out["ok"], out.get("error"))
        self.assertIn("read whole", out["calls"][0]["prompt"])


if __name__ == "__main__":
    unittest.main()
