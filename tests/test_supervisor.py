"""Executable failure probes; all repositories and subprocesses are disposable."""
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "sop-slop/scripts/supervisor.py"
spec = importlib.util.spec_from_file_location("supervisor", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class SupervisorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="sop-probe-")
        self.repo = Path(self.tmp.name)
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Test")
        self.write(".gitignore", "__pycache__/\n")
        self.write("product.py", "def total(values):\n    return 0\n")
        self.write("test_product.py", "from product import total\nassert total([2, 3]) == 5, 'wrong total'\n")
        self.git("add", ".")
        self.git("commit", "-qm", "fixture")
        self.sup = mod.Supervisor(self.repo)
        self.contract = {"mission": "Correct totals", "source_ref": "user:1", "actor": "controller",
            "lane": "approved-build", "tier": "T1", "target": "candidate_verified", "non_goals": ["release"],
            "invariants": ["input is unchanged"], "authority": [], "sources": ["annotation-1"],
            "problems": [{"id": "total", "problem": "total returns zero", "desired": "sum values",
                "task_ref": "docs/tasks.md#total", "sources": ["annotation-1"],
                "criteria": [{"id": "sum", "given": "two values", "when": "total is called", "then": "their sum"}]}]}
        self.run = self.sup.operate("start", self.contract)["id"]
        self.check = {"id": "sum", "kind": "behavior", "argv": [sys.executable, "test_product.py"],
            "criteria": ["sum"], "test_files": ["test_product.py"], "require_red": True,
            "failure_contains": "wrong total", "timeout": 5}

    def tearDown(self):
        self.sup.close()
        self.tmp.cleanup()

    def write(self, name, content):
        (self.repo / name).write_text(content)

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.repo), *args], stderr=subprocess.STDOUT)

    def op(self, name, **data):
        return self.sup.operate(name, data, self.run, "controller")

    def plan(self, checks=None):
        self.op("lock", source_ref="user:1", basis="explicit behavior")
        self.op("plan", checks=checks or [self.check], source_ref="docs/plan.md")
        self.op("lease", action="acquire")

    def green(self):
        self.plan()
        self.assertEqual(self.op("check", id="sum", phase="red")["result"], "expected_failure")
        self.write("product.py", "def total(values):\n    return sum(values)\n")
        self.op("freeze")
        self.assertEqual(self.op("check", id="sum")["result"], "pass")

    def question(self, ident="q1", kind="behavior"):
        return self.op("decision", id=ident, kind=kind, question="Count zero?", options=["yes", "no"],
            recommendation="yes", blocks=["sum"], reversible=True, source_ref="request:ambiguity")

    def test_full_red_green_closure_and_restart(self):
        self.green()
        self.op("seal")
        with self.assertRaisesRegex(mod.GateError, "cleanup"):
            self.op("finish", classification="no_issue", finding="verified", source_ref="review:1")
        self.op("cleanup", note="No disposable resources", dispositions={})
        self.op("finish", classification="no_issue", finding="verified", source_ref="review:1")
        self.sup.close()
        self.sup = mod.Supervisor(self.repo)
        self.assertEqual(self.op("status")["terminal"], "completed")
        self.assertEqual(self.op("audit")["integrity"], "pass")

    def test_empty_answer_cannot_lock(self):
        self.question()
        with self.assertRaises(mod.GateError):
            self.op("answer", id="q1", answer="", source_ref="empty picker")
        with self.assertRaisesRegex(mod.GateError, "unanswered"):
            self.op("lock", source_ref="user:1", basis="assumed")

    def test_question_budget_and_routine_auto_decision(self):
        for i in range(3):
            self.question("q" + str(i))
            self.op("answer", id="q" + str(i), answer="yes", source_ref="user:answer")
        with self.assertRaisesRegex(mod.GateError, "budget"):
            self.question("q4")
        result = self.op("decision", id="routine", kind="routine", question="Which parser?",
                         recommendation="stdlib", source_ref="repo:inspection")
        self.assertEqual(result["action"], "auto_decided")
        self.assertEqual(self.op("status")["questions_used"], 3)

    def test_delegation_does_not_supply_security_authority(self):
        self.question(kind="security")
        with self.assertRaisesRegex(mod.GateError, "delegation"):
            self.op("answer", id="q1", answer="choose for me", use_recommendation=True, source_ref="user:2")

    def test_source_coverage_rejects_lost_or_duplicate_annotation(self):
        for sources in (["annotation-1", "lost"], []):
            contract = {**self.contract, "sources": sources}
            with self.assertRaisesRegex(mod.GateError, "every source"):
                mod.validate_contract(contract)

    def test_acceptance_coverage_required(self):
        self.op("lock", source_ref="user:1", basis="explicit")
        with self.assertRaisesRegex(mod.GateError, "every acceptance"):
            self.op("plan", checks=[{**self.check, "criteria": []}], source_ref="plan")

    def test_new_input_blocks_execution_then_sidequest_preserves_mission(self):
        self.plan()
        before = self.op("status")
        self.op("input", id="message2", summary="Also add exports", source_ref="user:2")
        with self.assertRaisesRegex(mod.GateError, "classify"):
            self.op("check", id="sum", phase="red")
        after = self.op("classify", id="message2", classification="side_quest", reason="independent work")
        self.assertEqual((before["phase"], before["contract"]), (after["phase"], after["contract"]))
        self.assertEqual(after["work"][0]["authority"], [])

    def test_work_deduplicates_and_unknown_spawn_cannot_retry(self):
        args = dict(key="export", title="Export data", reason="later", source_ref="user:2")
        first = self.op("work", **args)
        self.assertEqual(first["id"], self.op("work", **args)["id"])
        self.op("dispatch", id=first["id"], action="prepare", authority_source="user:explicit new task")
        self.op("dispatch", id=first["id"], action="unknown", source_ref="tool:timeout")
        with self.assertRaisesRegex(mod.GateError, "reconcile"):
            self.op("dispatch", id=first["id"], action="prepare", authority_source="same request")
        self.op("dispatch", id=first["id"], action="linked", thread_id="actual-thread", source_ref="tool:lookup")

    def test_writer_collision_across_linked_worktrees(self):
        self.op("lease", action="acquire")
        other_path = self.repo / "other"
        self.git("worktree", "add", "-qb", "other", str(other_path))
        other = mod.Supervisor(other_path)
        try:
            other_run = other.operate("start", {**self.contract, "actor": "other"})["id"]
            with self.assertRaisesRegex(mod.GateError, "another run"):
                other.operate("lease", {"action": "acquire"}, other_run, "other")
        finally:
            other.close()

    def test_no_self_attested_pass_or_premature_seal(self):
        self.plan()
        self.op("freeze")
        with self.assertRaisesRegex(mod.GateError, "missing observed"):
            self.op("seal", result="pass")
        self.assertEqual(self.op("check", id="sum", phase="candidate")["result"], "fail")
        with self.assertRaisesRegex(mod.GateError, "failed or stale"):
            self.op("seal")

    def test_stale_candidate_is_rejected(self):
        self.green()
        self.write("product.py", "def total(values):\n    return -1\n")
        with self.assertRaisesRegex(mod.GateError, "candidate changed"):
            self.op("seal")

    def test_modified_assertion_requires_replan(self):
        self.green()
        self.write("test_product.py", "assert True\n")
        self.op("repair", reason="changed test")
        self.op("freeze")
        with self.assertRaisesRegex(mod.GateError, "assertion files changed"):
            self.op("check", id="sum")

    def test_legitimate_replan_allows_new_assertions(self):
        self.green()
        self.op("revise", reason="stronger assertion", source_ref="review:1")
        self.write("test_product.py", "from product import total\nassert total([2, 3, 4]) == 9, 'wrong total'\n")
        self.op("plan", checks=[self.check], source_ref="plan:revised")
        self.write("product.py", "def total(values):\n    return 0\n")
        self.assertEqual(self.op("check", id="sum", phase="red")["result"], "expected_failure")

    def test_timeout_has_observed_receipt(self):
        self.write("slow.py", "import time\ntime.sleep(10)\n")
        check = {**self.check, "argv": [sys.executable, "slow.py"], "test_files": ["slow.py"],
                 "require_red": False, "timeout": 1}
        self.plan([check])
        self.op("freeze")
        self.assertEqual(self.op("check", id="sum")["result"], "timeout")
        self.assertIsNone(self.op("status")["execution"])

    def test_check_that_mutates_code_does_not_pass(self):
        self.write("mutate.py", "from pathlib import Path\nPath('product.py').write_text('changed')\n")
        self.plan([{**self.check, "argv": [sys.executable, "mutate.py"], "test_files": ["mutate.py"], "require_red": False}])
        self.op("freeze")
        self.assertEqual(self.op("check", id="sum")["result"], "subject_changed")

    def test_independent_review_is_required_and_attributed(self):
        self.op("revise", reason="risk", source_ref="intake", contract={**self.contract, "tier": "T2"})
        self.green()
        with self.assertRaisesRegex(mod.GateError, "independent review"):
            self.op("seal")

    def test_refreezing_cannot_erase_failed_review(self):
        self.green()
        self.op("review", reviewer="reviewer-agent", disposition="fatal", finding="unsafe", source_ref="tool:review")
        self.op("freeze")
        with self.assertRaisesRegex(mod.GateError, "independent review"):
            self.op("seal")
        with self.assertRaisesRegex(mod.GateError, "independent"):
            self.op("review", reviewer="controller", disposition="accepted", finding="fine", source_ref="self")
        self.op("review", reviewer="reviewer-agent", disposition="accepted", finding="verified", source_ref="tool:review")
        self.op("seal")

    def test_optional_fatal_review_still_blocks(self):
        self.green()
        self.op("review", reviewer="reviewer-agent", disposition="fatal", finding="unsafe", source_ref="tool:review")
        with self.assertRaisesRegex(mod.GateError, "independent review"):
            self.op("seal")

    def test_output_is_bounded_and_redacted(self):
        self.write("spam.py", "print('x' * 2000000)\n")
        self.plan([{**self.check, "argv": [sys.executable, "spam.py"], "test_files": ["spam.py"], "require_red": False}])
        self.op("freeze")
        receipt = self.op("check", id="sum")
        self.assertEqual(receipt["result"], "output_limit")
        self.assertLessEqual(len(receipt["output_tail"]), 4096)
        self.assertNotIn("sensitive", mod.redact("token=sensitive password=sensitive Bearer sensitive"))

    def test_repeated_command_arguments_are_valid(self):
        self.plan([{**self.check, "argv": [sys.executable, "test_product.py", "--tag", "one", "--tag", "two"]}])

    def test_crashed_supervisor_cannot_release_live_child_group(self):
        self.write("slow.py", "import time\ntime.sleep(30)\n")
        self.plan([{**self.check, "argv": [sys.executable, "slow.py"], "test_files": ["slow.py"], "require_red": False}])
        process = subprocess.Popen([sys.executable, str(SCRIPT), "check", "--repo", str(self.repo),
            "--run", self.run, "--actor", "controller"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        process.stdin.write(b'{"id":"sum"}')
        process.stdin.close()
        child = None
        try:
            for _ in range(50):
                execution = self.op("status")["execution"]
                if execution and execution.get("child_pid"):
                    child = execution["child_pid"]
                    break
                time.sleep(0.02)
            self.assertIsNotNone(child)
            process.kill()
            process.wait(timeout=5)
            with self.assertRaisesRegex(mod.GateError, "process group still exists"):
                self.op("recover-check", source_ref="inspection")
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            if child:
                try:
                    os.killpg(child, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            process.stdout.close()
            process.stderr.close()

    def test_graph_drift_is_rejected(self):
        old = mod.GRAPH["question_budget"]
        try:
            mod.GRAPH["question_budget"] = 9
            with self.assertRaisesRegex(mod.GateError, "graph changed"):
                self.op("status")
        finally:
            mod.GRAPH["question_budget"] = old

    def test_sealed_delivery_cannot_be_reopened_and_successor_is_durable(self):
        self.green()
        receipt = self.op("seal")["delivery"]
        with self.assertRaisesRegex(mod.GateError, "sealed"):
            self.op("repair", reason="new work")
        self.op("input", id="new", summary="Add export", source_ref="user:3")
        with self.assertRaises(mod.GateError):
            self.op("classify", id="new", classification="side_quest", reason="new")
        s = self.op("classify", id="new", classification="successor_mission", reason="delivered parent")
        self.assertEqual(receipt, s["delivery"])
        self.assertEqual(s["work"][0]["kind"], "successor_mission")

    def test_cleanup_preserves_data_and_review_can_downgrade_only_effective_status(self):
        self.op("resource", id="artifact", path=str(self.repo / "product.py"), kind="file", source_ref="run:created")
        self.green()
        delivery = self.op("seal")["delivery"]
        with self.assertRaisesRegex(mod.GateError, "still exists"):
            self.op("cleanup", note="delete", dispositions={"artifact": {"state": "released", "reason": "done"}})
        self.op("cleanup", note="retain product", dispositions={"artifact": {"state": "preserved", "reason": "user deliverable"}})
        result = self.op("finish", classification="executor_issue", finding="invariant breach", source_ref="review:2",
                         hard_invariant_breach=True)
        self.assertEqual(result["terminal"], "failed")
        self.assertEqual(result["delivery"], delivery)
        self.assertTrue((self.repo / "product.py").exists())

    def test_upstream_change_blocks_closure(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md") as skill:
            skill.write("Original skill\n")
            skill.flush()
            self.op("skill", path=skill.name, purpose="test upstream")
            self.green()
            skill.write("Changed upstream\n")
            skill.flush()
            with self.assertRaisesRegex(mod.GateError, "upstream changed"):
                self.op("seal")

    def test_release_authority_target_and_observed_revision(self):
        contract = {**self.contract, "target": "production_verified", "release_target": "https://fixture.invalid"}
        self.op("revise", reason="release request", source_ref="user:release", contract=contract)
        self.write("release.py", "import json,subprocess\nprint(json.dumps({'kind':'production','target':'https://fixture.invalid',"
            "'revision':subprocess.check_output(['git','rev-parse','HEAD']).decode().strip(),'healthy':True,'resource_id':'deploy-1',"
            "'debug':'Bearer dummy-sensitive-credential'}))\n")
        release_check = {**self.check, "id": "release", "kind": "release", "criteria": [],
            "argv": [sys.executable, "release.py"], "test_files": ["release.py"], "require_red": False}
        live_check = {**self.check, "id": "live", "kind": "production", "criteria": []}
        live_check["require_red"] = False
        self.plan([self.check, release_check, live_check])
        self.op("check", id="sum", phase="red")
        self.write("product.py", "def total(values):\n    return sum(values)\n")
        self.git("add", ".")
        self.git("commit", "-qm", "candidate")
        self.op("freeze")
        self.op("check", id="sum")
        with self.assertRaisesRegex(mod.GateError, "authority"):
            self.op("release")
        self.op("authorize", actions=["push", "pr", "merge", "deploy"], source_ref="user:release")
        self.op("release")
        receipt = self.op("check", id="release", phase="production")
        self.assertNotIn("dummy-sensitive", json.dumps(receipt))
        self.assertNotIn("dummy-sensitive", json.dumps(self.op("export")))
        self.op("check", id="live", phase="production")
        self.assertEqual(self.op("seal")["delivery"]["release"]["resource_id"], "deploy-1")

    def test_additional_authority_is_bound_to_contract(self):
        contract = {**self.contract, "target": "production_verified", "release_target": "A"}
        self.op("revise", reason="target A", source_ref="user:target-A", contract=contract)
        self.op("authorize", actions=["push", "pr", "merge", "deploy"], source_ref="user:target-A")
        self.op("revise", reason="different release target", source_ref="user:target-B",
                contract={**contract, "release_target": "B"})
        checks = [{**self.check, "require_red": False},
                  {**self.check, "id": "release", "kind": "release", "criteria": [], "require_red": False},
                  {**self.check, "id": "live", "kind": "production", "criteria": [], "require_red": False}]
        self.plan(checks)
        self.write("product.py", "def total(values):\n    return sum(values)\n")
        self.git("add", ".")
        self.git("commit", "-qm", "candidate for B")
        self.op("freeze")
        self.op("check", id="sum")
        with self.assertRaisesRegex(mod.GateError, "missing release authority"):
            self.op("release")

    def test_cli_invalid_request_is_structured(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "start", "--repo", str(self.repo)],
                                input="[]", capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("error", json.loads(result.stderr))

    def test_malformed_nested_request_is_rejected_without_partial_write(self):
        with self.assertRaisesRegex(mod.GateError, "problem must be an object"):
            mod.validate_contract({**self.contract, "problems": [None]})
        self.op("lock", source_ref="user:1", basis="explicit")
        before = self.op("status")["revision"]
        with self.assertRaisesRegex(mod.GateError, "check must be an object"):
            self.op("plan", checks=[None], source_ref="plan")
        self.assertEqual(self.op("status")["revision"], before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
