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

    def args(self, **extra):
        return dict({"tree": "/tmp/tree", "head": HEAD, "base": BASE}, **extra)

    def test_node_parses_the_script(self):
        out = self.run_panel(self.args(), {})
        self.assertTrue(out["meta"]["name"])
        self.assertEqual([p["title"] for p in out["meta"]["phases"]], ["Find", "Verify"])

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
        })
        self.assertTrue(out["ok"], out.get("error"))
        r = out["result"]
        by = {f"{f['file']}:{f['line']}": f for f in r["findings"]}
        self.assertEqual(len(by["app.py:10"]["reports"]), 2, "two reports on one line pool into one candidate")
        self.assertEqual(by["app.py:10"]["verdict"], "dismissed")
        self.assertEqual(by["src/db.py:3"]["verdict"], "stands")
        self.assertEqual(by["tests/test_db.py:7"]["verdict"], "stands")
        self.assertEqual(by["src/api.py:22"]["verdict"], "confirmed")
        self.assertTrue(r["complete"])
        self.assertEqual(r["counts"]["agents_sent"], 3 + 4)
        self.assertEqual(r["model"], "opus")
        self.assertTrue(all(c["model"] == "opus" for c in out["calls"]))
        verifier_prompt = next(c["prompt"] for c in out["calls"] if c["label"] == "verifier:app.py:10")
        self.assertIn("2 reports name this line", verifier_prompt)
        self.assertIn("Being unconvinced", verifier_prompt)

    def test_only_a_file_and_line_with_its_text_counts_as_a_quote(self):
        quotes = {
            "checked at 10:30 and it is fine": "stands",
            "step:2 rejects it": "stands",
            "see line 12: it returns early": "stands",
            "Unconvinced: src/db.py:3 has no test for it, so unlikely": "stands",
            "the CI BUILD:3 passes so fine": "stands",
            "`src/db.py:3 if x is None: return`": "dismissed",
            "Makefile:4 test: lint": "dismissed",
            "/scratch/lhr-tree.verifier-1/src/db.py:42 if not rows: return []": "dismissed",
            ".gitlab-ci.yml:5 only: [main]": "dismissed",
            "bin/deploy:12 set -euo pipefail": "dismissed",
        }
        findings = [self.finding(f"f{i}.py", i + 1) for i in range(len(quotes))]
        responses = {"finder:guards": self.finder(findings[:4]), "finder:tests": self.finder(findings[4:8]),
                     "finder:harm": self.finder(findings[8:])}
        for i, quote in enumerate(quotes):
            responses[f"verifier:f{i}.py:{i + 1}"] = self.verdict("dismissed", quote=quote)
        out = self.run_panel(self.args(max_candidates=10), responses)
        self.assertTrue(out["ok"], out.get("error"))
        got = {f["quote"]: f["verdict"] for f in out["result"]["findings"]}
        self.assertEqual(got, quotes)

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
