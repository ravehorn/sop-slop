#!/usr/bin/env python3
"""Local SOP SLOP supervisor. JSON requests in, observed state out; no daemon."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import signal
import sqlite3
import subprocess
import sys
import time
import uuid

GRAPH_PATH = Path(__file__).resolve().parents[1] / "references" / "supervisor-graph.json"
GRAPH = json.loads(GRAPH_PATH.read_text())
VERSION = GRAPH["version"]
TARGETS = {"decision_complete", "spec_complete", "review_complete", "candidate_verified",
           "pr_opened", "merged", "staging_verified", "production_verified"}
RELEASES = {"pr_opened": "pr", "merged": "merge", "staging_verified": "staging",
            "production_verified": "production"}
BUILD_LANES = {"product-change", "approved-build"}
ACTIONS = {"commit", "push", "pr", "merge", "deploy", "production_read"}
REVIEW_CLASSES = set(GRAPH["review_classes"])
ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,95}$")


class GateError(ValueError):
    """A failed predicate; the caller may inspect status and repair."""


def require(ok, message):
    if not ok:
        raise GateError(message)


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value):
    return hashlib.sha256(encoded(value).encode()).hexdigest()


def text(value, label):
    require(isinstance(value, str) and bool(value.strip()) and len(value) <= 12000,
            f"{label} must be a non-empty bounded string")
    return value


def identifier(value, label="id"):
    require(isinstance(value, str) and ID.fullmatch(value), f"invalid {label}")
    return value


def strings(value, label, empty=False):
    require(isinstance(value, list) and (empty or bool(value)), f"{label} must be a list")
    for v in value:
        text(v, label)
    require(len(set(value)) == len(value), f"duplicate {label}")
    return value


def git(repo, *args):
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, timeout=30)
    require(result.returncode == 0, "git inspection failed: " + result.stderr.decode(errors="replace")[:500])
    return result.stdout


def file_hash(path):
    h = hashlib.sha256()
    if path.is_symlink():
        h.update(b"symlink:" + os.readlink(path).encode())
    elif not path.exists():
        h.update(b"missing")
    elif path.is_file():
        with path.open("rb") as f:
            for block in iter(lambda: f.read(1024 * 1024), b""):
                h.update(block)
        h.update(str(path.stat().st_mode & 0o111).encode())
    else:
        raise GateError(f"expected a file: {path}")
    return h.hexdigest()


def subject(repo):
    # Ignored build output is excluded; registered assertion files are checked separately.
    names = sorted(set(git(repo, "ls-files", "-z", "--cached", "--others", "--exclude-standard").split(b"\0")) - {b""})
    files = [(os.fsdecode(name), file_hash(repo / os.fsdecode(name))) for name in names]
    head = git(repo, "rev-parse", "HEAD").decode().strip()
    return {"head": head, "digest": digest({"head": head, "files": files})}


def redact(value):
    value = re.sub(r"(?i)(bearer\s+)[A-Za-z0-9_.~+/-]+", r"\1[REDACTED]", value)
    value = re.sub(r"(?i)((?:password|token|api[_-]?key|secret)\s*[:=]\s*)[^\s,;]+",
                   r"\1[REDACTED]", value)
    value = re.sub(r"(?:sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9]{12,}|eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)",
                   "[REDACTED]", value)
    return value


def validate_contract(c):
    require(isinstance(c, dict), "contract must be an object")
    for key in ("mission", "source_ref", "actor"):
        text(c.get(key), key)
    require(c.get("lane") in BUILD_LANES | {"strategy-decision", "review-only"}, "invalid lane")
    require(c.get("target") in TARGETS, "invalid completion target")
    require(c.get("tier") in ("T1", "T2", "T3"), "invalid tier")
    if c["lane"] not in BUILD_LANES:
        require(c["target"] in {"decision_complete", "spec_complete", "review_complete"}, "artifact lane cannot authorize delivery")
    strings(c.get("non_goals"), "non_goals", empty=True)
    strings(c.get("invariants"), "invariants")
    strings(c.get("assumptions", []), "assumptions", empty=True)
    strings(c.get("authority", []), "authority", empty=True)
    require(set(c.get("authority", [])) <= ACTIONS, "unknown authority")
    if c.get("authority"):
        text(c.get("authority_source"), "authority_source")
    if c["target"] in RELEASES:
        text(c.get("release_target"), "release_target")
    problems = c.get("problems")
    require(isinstance(problems, list) and problems, "problems required")
    sources = strings(c.get("sources", []), "sources", empty=True)
    assigned = []
    problem_ids, criterion_ids = set(), set()
    for p in problems:
        require(isinstance(p, dict), "problem must be an object")
        pid = identifier(p.get("id"), "problem id")
        require(pid not in problem_ids, "duplicate problem id")
        problem_ids.add(pid)
        for key in ("problem", "desired", "task_ref"):
            text(p.get(key), key)
        ps = strings(p.get("sources", []), "problem sources", empty=True)
        assigned.extend(ps)
        require(isinstance(p.get("criteria"), list) and p["criteria"], "acceptance criteria required")
        for criterion in p["criteria"]:
            require(isinstance(criterion, dict), "criterion must be an object")
            cid = identifier(criterion.get("id"), "criterion id")
            require(cid not in criterion_ids, "duplicate criterion id")
            criterion_ids.add(cid)
            for key in ("given", "when", "then"):
                text(criterion.get(key), key)
    dispositions = c.get("source_dispositions", {})
    require(isinstance(dispositions, dict), "source_dispositions must be an object")
    for reason in dispositions.values():
        text(reason, "source disposition")
    assigned += list(dispositions)
    require(set(assigned) == set(sources) and len(assigned) == len(set(assigned)),
            "every source needs exactly one problem or non-actionable disposition")
    for key, default in (("question_budget", 3), ("repair_budget", 3)):
        value = c.get(key, default)
        require(type(value) is int and 0 <= value <= 10, f"invalid {key}")
    return c


class Supervisor:
    def __init__(self, repo):
        self.repo = Path(git(Path(repo).resolve(), "rev-parse", "--show-toplevel").decode().strip()).resolve()
        common = Path(git(self.repo, "rev-parse", "--git-common-dir").decode().strip())
        self.common = (self.repo / common).resolve()
        self.home = self.common / "sop-slop"
        self.home.mkdir(mode=0o700, exist_ok=True)
        self.db = sqlite3.connect(self.home / "runs.sqlite3", timeout=10, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA busy_timeout=10000")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS metadata(version INTEGER NOT NULL);
            INSERT INTO metadata SELECT 1 WHERE NOT EXISTS(SELECT 1 FROM metadata);
            CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, state TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS events(
              sequence INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL,
              kind TEXT NOT NULL, time REAL NOT NULL, detail TEXT NOT NULL, state TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS work(
              id TEXT PRIMARY KEY, parent TEXT NOT NULL, source_key TEXT NOT NULL,
              state TEXT NOT NULL, UNIQUE(parent, source_key));
            CREATE TABLE IF NOT EXISTS writer(
              slot INTEGER PRIMARY KEY CHECK(slot=1), run_id TEXT NOT NULL, actor TEXT NOT NULL);
            CREATE TRIGGER IF NOT EXISTS events_no_update BEFORE UPDATE ON events
              BEGIN SELECT RAISE(ABORT, 'events are append-only'); END;
            CREATE TRIGGER IF NOT EXISTS events_no_delete BEFORE DELETE ON events
              BEGIN SELECT RAISE(ABORT, 'events are append-only'); END;
        """)
        require(self.db.execute("SELECT version FROM metadata").fetchone()[0] == 1, "unknown database version")

    def close(self):
        self.db.close()

    def load(self, run):
        row = self.db.execute("SELECT state FROM runs WHERE id=?", (run,)).fetchone()
        require(row is not None, "unknown run")
        state = json.loads(row[0])
        require(state["repo"] == str(self.repo), "run belongs to another worktree; use its recorded repository")
        require(state["version"] == VERSION, "run version differs; resume with its pinned supervisor")
        require(state["graph_digest"] == digest(GRAPH), "graph changed; resume with its pinned supervisor")
        require(state["contract_digest"] == digest(state["contract"]), "contract integrity mismatch")
        return state

    def save(self, state, kind, detail):
        state["revision"] += 1
        state["updated_at"] = time.time()
        value = encoded(state)
        self.db.execute("INSERT INTO runs VALUES(?, ?) ON CONFLICT(id) DO UPDATE SET state=excluded.state",
                        (state["id"], value))
        self.db.execute("INSERT INTO events(run_id,kind,time,detail,state) VALUES(?,?,?,?,?)",
                        (state["id"], kind, time.time(), encoded(detail), value))

    def active(self, s, actor, pending=False):
        require(actor == s["contract"]["actor"], "only the recorded controller may change run state")
        require(s["delivery"] is None, "delivery is sealed; capture a successor")
        require(s["execution"] is None, "execution outcome pending; inspect or reconcile it first")
        if not pending:
            require(not any(i["classification"] is None for i in s["inputs"].values()), "classify pending input first")

    def has_writer(self, s):
        row = self.db.execute("SELECT * FROM writer WHERE slot=1").fetchone()
        require(row is not None and row["run_id"] == s["id"] and row["actor"] == s["contract"]["actor"],
                "repository writer lease required")

    def criteria(self, s):
        return {x["id"] for p in s["contract"]["problems"] for x in p["criteria"]}

    def assertions(self, definition):
        paths = {}
        for relative in definition["test_files"]:
            path = (self.repo / relative).resolve()
            require(path.is_relative_to(self.repo) and path.is_file(), "assertion file must exist inside repository")
            paths[relative] = file_hash(path)
        return digest(paths)

    def work_item(self, s, key, kind, title, reason, source_ref):
        existing = self.db.execute("SELECT state FROM work WHERE parent=? AND source_key=?", (s["id"], key)).fetchone()
        if existing:
            item = json.loads(existing[0])
            require(item["kind"] == kind and item["title"] == title, "work key already used for different work")
            return item
        item = {"id": "work-" + uuid.uuid4().hex[:12], "parent": s["id"], "source_key": key,
                "kind": kind, "title": text(title, "work title"), "reason": text(reason, "work reason"),
                "source_ref": text(source_ref, "work source"), "status": "captured",
                "authority": [], "thread_id": None, "canonical_task_ref": None}
        self.db.execute("INSERT INTO work VALUES(?,?,?,?)", (item["id"], s["id"], key, encoded(item)))
        return item

    def candidate_ok(self, s):
        require(s["candidate"] is not None, "freeze a candidate first")
        require(subject(self.repo) == s["candidate"], "candidate changed; repair and reverify")

    def check_results(self, s, release=False):
        self.candidate_ok(s)
        require(not any(d["answer"] is None for d in s["decisions"].values()), "material decision unanswered")
        ids = []
        for definition in s["checks"]:
            if (definition["kind"] in ("release", "production")) != release:
                continue
            matches = [r for r in s["receipts"] if r["check_id"] == definition["id"] and
                       r.get("plan_epoch") == s["plan_epoch"] and r["phase"] != "red"]
            require(matches, "missing observed check: " + definition["id"])
            latest = matches[-1]
            require(latest["result"] == "pass" and latest["subject"] == s["candidate"],
                    "failed or stale check: " + definition["id"])
            require(latest["definition_digest"] == digest(definition) and
                    latest["assertions_digest"] == self.assertions(definition), "test definition changed; replan")
            if definition["require_red"]:
                require(any(r["check_id"] == definition["id"] and r["phase"] == "red" and
                            r["result"] == "expected_failure" and
                            r.get("plan_epoch") == s["plan_epoch"] and
                            r["definition_digest"] == latest["definition_digest"] and
                            r["assertions_digest"] == latest["assertions_digest"]
                            for r in s["receipts"]), "missing matching red proof: " + definition["id"])
            ids.append(latest["id"])
        if not release and (s.get("review_required") or s["contract"]["tier"] != "T1" or s["contract"].get("review_required", False)):
            review = s["review"]
            require(review and review["subject"] == s["candidate"] and review["disposition"] == "accepted",
                    "independent review of current candidate required")
        return ids

    def operate(self, op, data, run=None, actor=None):
        if op == "check":
            return self.run_check(run, actor, data)
        self.db.execute("BEGIN IMMEDIATE")
        try:
            result = self._operate(op, data, run, actor)
            self.db.execute("COMMIT")
            return result
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def _operate(self, op, d, run, actor):
        if op == "start":
            c = validate_contract(d)
            rid = "run-" + uuid.uuid4().hex[:12]
            s = {"id": rid, "version": VERSION, "graph_digest": digest(GRAPH), "repo": str(self.repo),
                 "contract": c, "contract_digest": digest(c), "revision": 0, "phase": "understand",
                 "inputs": {}, "decisions": {}, "recommendations": [], "checks": [], "receipts": [],
                 "candidate": None, "execution": None, "review": None, "release": None,
                 "resources": [], "delivery": None, "run_review": None, "terminal": None,
                 "repairs": 0, "skills": [], "alignment": None, "plan_epoch": 0}
            self.save(s, "started", {"source": c["source_ref"]})
            return self.status(s)
        if op == "list":
            return [{"id": r["id"], "mission": json.loads(r["state"])["contract"]["mission"],
                     "phase": json.loads(r["state"])["phase"], "terminal": json.loads(r["state"])["terminal"]}
                    for r in self.db.execute("SELECT id,state FROM runs")]
        s = self.load(run)
        if op == "status":
            return self.status(s)
        if op == "export":
            return {"state": s, "work": self.work_list(s), "events": [
                {"sequence": r["sequence"], "kind": r["kind"], "time": r["time"],
                 "detail": json.loads(r["detail"]), "state_digest": digest(json.loads(r["state"]))}
                for r in self.db.execute("SELECT * FROM events WHERE run_id=? ORDER BY sequence", (run,))]}
        if op == "audit":
            row = self.db.execute("SELECT state FROM events WHERE run_id=? ORDER BY sequence DESC LIMIT 1", (run,)).fetchone()
            require(row and json.loads(row[0]) == s, "stored state differs from last event")
            require(self.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "database integrity failed")
            return {"integrity": "pass", "delivery": s["delivery"], "terminal": s["terminal"],
                    "limit": "Local consistency, not hostile-writer authentication or live production recheck."}
        require(actor == s["contract"]["actor"], "controller identity mismatch")
        if op == "input":
            iid = identifier(d.get("id"), "input id")
            incoming = {"digest": digest(d), "summary": text(d.get("summary"), "input summary"),
                        "source_ref": text(d.get("source_ref"), "input source"), "classification": None}
            if iid in s["inputs"]:
                require(s["inputs"][iid]["digest"] == incoming["digest"], "input id reused with changed content")
                return self.status(s)
            s["inputs"][iid] = incoming
            self.save(s, "input_received", {"id": iid})
            return self.status(s)
        if op == "classify":
            inp = s["inputs"].get(identifier(d.get("id"), "input id"))
            require(inp is not None and inp["classification"] is None, "input missing or already classified")
            classification = d.get("classification")
            legal = GRAPH["sealed_input_classes"] if s["delivery"] else GRAPH["active_input_classes"]
            require(classification in legal, "input class is illegal for current delivery state")
            inp.update(classification=classification, reason=text(d.get("reason"), "classification reason"))
            if classification in ("side_quest", "successor_mission", "explicit_replacement"):
                item = self.work_item(s, d["id"], classification, inp["summary"], d["reason"], inp["source_ref"])
                inp["work_id"] = item["id"]
            if classification == "explicit_replacement":
                require(s["execution"] is None, "reconcile running execution before replacement")
                s["delivery"] = {"status": "blocked", "reason": "explicitly superseded", "source_ref": inp["source_ref"],
                                 "candidate": s["candidate"], "time": time.time()}
                s["phase"] = "finish"
            self.save(s, "input_classified", {"id": d["id"], "classification": classification})
            return self.status(s)
        if op == "work":
            item = self.work_item(s, identifier(d.get("key")), d.get("kind", "side_quest"),
                                  d.get("title"), d.get("reason"), d.get("source_ref"))
            require(item["kind"] in ("side_quest", "successor_mission", "improvement", "dependency"),
                    "invalid work kind")
            self.save(s, "work_captured", {"work_id": item["id"]})
            return item
        if op == "dispatch":
            row = self.db.execute("SELECT state FROM work WHERE id=? AND parent=?", (d.get("id"), run)).fetchone()
            require(row is not None, "unknown work item")
            item = json.loads(row[0])
            action = d.get("action")
            if action == "prepare":
                require(item["status"] in ("captured", "not_created"), "dispatch pending or complete; reconcile before retry")
                text(d.get("authority_source"), "explicit task-creation authority source")
                item.update(status="dispatching", authority_source=d["authority_source"])
            elif action == "linked":
                require(item["status"] in ("dispatching", "unknown"), "no pending dispatch")
                item.update(status="linked", thread_id=text(d.get("thread_id"), "actual thread id"),
                            source_ref=text(d.get("source_ref"), "tool result source"))
            elif action in ("unknown", "not_created"):
                require(item["status"] in ("dispatching", "unknown"), "no uncertain dispatch")
                item.update(status=action, reconciliation=text(d.get("source_ref"), "reconciliation evidence"))
            elif action == "task":
                item["canonical_task_ref"] = text(d.get("task_ref"), "canonical task ref")
            else:
                raise GateError("invalid dispatch action")
            self.db.execute("UPDATE work SET state=? WHERE id=?", (encoded(item), item["id"]))
            self.save(s, "work_dispatch", {"id": item["id"], "status": item["status"]})
            return item
        if op == "lease":
            action = d.get("action")
            row = self.db.execute("SELECT * FROM writer WHERE slot=1").fetchone()
            if action == "acquire":
                self.active(s, actor)
                require(s["contract"]["lane"] in BUILD_LANES, "review/decision run cannot own implementation writes")
                require(row is None or row["run_id"] == run, "another run owns the repository writer lease")
                self.db.execute("INSERT OR IGNORE INTO writer VALUES(1,?,?)", (run, actor))
            elif action == "release":
                require(s["execution"] is None, "cannot release a writer during an execution")
                self.has_writer(s)
                self.db.execute("DELETE FROM writer WHERE slot=1 AND run_id=?", (run,))
            else:
                raise GateError("lease action must be acquire or release; recover via recorded owner")
            self.save(s, "writer_" + action, {})
            return self.status(s)
        if op == "cleanup":
            require(s["delivery"], "seal delivery before cleanup")
            require(s["terminal"] is None, "run already terminal")
            for resource in s["resources"]:
                disposition = d.get("dispositions", {}).get(resource["id"])
                require(isinstance(disposition, dict), "every resource needs a disposition")
                state = disposition.get("state")
                require(state in ("preserved", "released"), "invalid resource disposition")
                text(disposition.get("reason"), "resource reason")
                if state == "released":
                    require(not Path(resource["path"]).exists() and not Path(resource["path"]).is_symlink(),
                            "released resource still exists")
                    text(disposition.get("source_ref"), "cleanup action evidence")
                resource["disposition"] = disposition
            s["cleanup"] = {"time": time.time(), "resources_digest": digest(s["resources"]),
                            "note": text(d.get("note"), "cleanup note")}
            self.db.execute("DELETE FROM writer WHERE slot=1 AND run_id=?", (run,))
            self.save(s, "cleanup_reconciled", s["cleanup"])
            return self.status(s)
        if op == "finish":
            require(s["delivery"] and s.get("cleanup"), "delivery and cleanup receipts required")
            require(s["terminal"] is None, "run already terminal")
            require(not any(i["classification"] is None for i in s["inputs"].values()), "classify pending input first")
            classification = d.get("classification")
            require(classification in REVIEW_CLASSES, "invalid run review classification")
            review = {"classification": classification, "finding": text(d.get("finding"), "review finding"),
                      "source_ref": text(d.get("source_ref"), "review source"), "time": time.time(),
                      "failed_checks": sum(r["result"] in ("fail", "timeout", "interrupted") for r in s["receipts"]),
                      "questions": len(s["decisions"]), "repairs": s["repairs"]}
            s["run_review"] = review
            s["terminal"] = "failed" if d.get("hard_invariant_breach") is True else s["delivery"]["status"]
            if d.get("proposal"):
                item = self.work_item(s, "review-proposal", "improvement", d["proposal"], review["finding"], d["source_ref"])
                review["proposal_id"] = item["id"]
            self.save(s, "finished", review)
            return self.status(s)
        if op == "recover-check":
            ex = s["execution"]
            require(ex is not None, "no pending execution")
            require(not self.process_exists(ex["controller_pid"]), "supervisor process still exists")
            if ex.get("child_pid") is not None:
                require(not self.process_exists(-ex["child_pid"]), "execution process group still exists; inspect it before recovery")
            else:
                require(d.get("confirmed_stopped") is True,
                        "spawn outcome unknown; explicit inspection must confirm no child remains")
            text(d.get("source_ref"), "inspection/recovery source")
            s["receipts"].append({**ex, "result": "interrupted", "id": ex["id"],
                                  "check_id": ex["check_id"], "phase": ex["phase"]})
            s["execution"] = None
            self.save(s, "execution_recovered", {"source_ref": d["source_ref"]})
            return self.status(s)
        self.active(s, actor)
        if op == "decision":
            identifier(d.get("id"), "decision id")
            require(d["id"] not in s["decisions"], "decision already recorded")
            text(d.get("question"), "question")
            text(d.get("recommendation"), "recommendation")
            text(d.get("source_ref"), "decision source")
            if d.get("kind") == "routine":
                s["recommendations"].append({"id": d["id"], "choice": d["recommendation"], "source_ref": d["source_ref"]})
                self.save(s, "routine_decided", {"id": d["id"]})
                return {"action": "auto_decided", "choice": d["recommendation"]}
            require(d.get("kind") in ("behavior", "scope", "data", "security", "cost", "authority"), "invalid decision kind")
            blockers = strings(d.get("blocks"), "blocked criteria")
            require(set(blockers) <= self.criteria(s), "decision must name existing acceptance criteria")
            require(s["phase"] in ("understand", "plan"), "material change after build needs revise first")
            require(len(s["decisions"]) < s["contract"].get("question_budget", GRAPH["question_budget"]),
                    "question budget exhausted; narrow the unresolved decision, do not continue grilling")
            options = strings(d.get("options"), "options")
            require(2 <= len(options) <= 3 and d["recommendation"] in options, "2-3 choices including recommendation required")
            s["decisions"][d["id"]] = {**d, "answer": None}
            self.save(s, "question_registered", {"id": d["id"]})
        elif op == "answer":
            decision = s["decisions"].get(identifier(d.get("id"), "decision id"))
            require(decision is not None and decision["answer"] is None, "unknown or already answered decision")
            answer = text(d.get("answer"), "actual non-empty answer")
            source = text(d.get("source_ref"), "user answer source")
            if d.get("use_recommendation") is True:
                require(decision["kind"] in ("behavior", "scope") and decision.get("reversible") is True,
                        "delegation cannot resolve authority, safety, data or cost decisions")
                answer = decision["recommendation"]
            decision.update(answer=answer, answer_source=source)
            self.save(s, "decision_answered", {"id": d["id"]})
        elif op == "lock":
            require(s["phase"] == "understand", "alignment already locked")
            require(not any(d["answer"] is None for d in s["decisions"].values()), "material decision unanswered")
            s["alignment"] = {"source_ref": text(d.get("source_ref"), "alignment source"),
                              "basis": text(d.get("basis"), "alignment basis"), "contract_digest": s["contract_digest"]}
            s["phase"] = "plan"
            self.save(s, "alignment_locked", s["alignment"])
        elif op == "plan":
            require(s["phase"] == "plan", "plan can only be recorded before build")
            checks = d.get("checks")
            require(isinstance(checks, list) and checks, "checks required")
            seen, covered = set(), set()
            for c in checks:
                require(isinstance(c, dict), "check must be an object")
                cid = identifier(c.get("id"), "check id")
                require(cid not in seen, "duplicate check id")
                seen.add(cid)
                require(isinstance(c.get("argv"), list) and c["argv"], "command argv required")
                require(c.get("kind") in ("behavior", "regression", "required", "artifact", "production", "release"), "invalid check kind")
                criteria = strings(c.get("criteria", []), "check criteria", empty=True)
                require(set(criteria) <= self.criteria(s), "unknown check criterion")
                if c["kind"] in ("behavior", "artifact"):
                    covered.update(criteria)
                strings(c.get("test_files"), "test files")
                require(type(c.get("require_red")) is bool, "require_red must be boolean")
                if c["require_red"]:
                    text(c.get("failure_contains"), "expected failure signature")
                require(type(c.get("timeout", 120)) is int and 1 <= c.get("timeout", 120) <= 600, "invalid check timeout")
                require(all(isinstance(a, str) and a for a in c["argv"]), "argv must contain strings")
                require(not any(redact(a) != a for a in c["argv"]), "credentials must not appear in arguments")
            require(covered == self.criteria(s), "every acceptance criterion needs a behavior/artifact check")
            if s["contract"]["target"] in RELEASES:
                require(any(c["kind"] == "release" for c in checks), "release target needs a release observation check")
                if s["contract"]["target"] in ("production_verified", "staging_verified"):
                    require(any(c["kind"] == "production" for c in checks), "live behavior check required")
            s["checks"] = checks
            s["plan_epoch"] += 1
            s["plan_ref"] = text(d.get("source_ref"), "canonical plan source")
            s["phase"] = "build" if s["contract"]["lane"] in BUILD_LANES else "check"
            self.save(s, "plan_recorded", {"plan_ref": s["plan_ref"], "checks_digest": digest(checks)})
        elif op == "revise":
            reason = text(d.get("reason"), "revision reason")
            source = text(d.get("source_ref"), "revision source")
            if d.get("contract") is not None:
                c = validate_contract(d["contract"])
                require(c["actor"] == actor, "revision cannot change controller")
                s["contract"], s["contract_digest"] = c, digest(c)
                s["decisions"] = {}
                s["alignment"] = None
                s["phase"] = "understand"
            else:
                s["phase"] = "plan"
            s.update(candidate=None, review=None, release=None, checks=[])
            self.save(s, "revised", {"reason": reason, "source_ref": source})
        elif op == "freeze":
            require(s["phase"] in ("build", "check"), "candidate can only freeze after plan/build")
            if s["contract"]["lane"] in BUILD_LANES:
                self.has_writer(s)
            s["candidate"] = subject(self.repo)
            s["phase"] = "check"
            s["review"] = None
            self.save(s, "candidate_frozen", s["candidate"])
        elif op == "review":
            self.candidate_ok(s)
            require(s["phase"] == "check", "review belongs to candidate phase")
            require(d.get("disposition") in ("accepted", "revision_required", "fatal"), "invalid review disposition")
            reviewer = text(d.get("reviewer"), "reviewer identity")
            require(reviewer != actor, "reviewer must be independent of controller/implementer")
            s["review_required"] = True
            s["review"] = {**d, "subject": s["candidate"], "provenance": "host_review_attestation",
                           "source_ref": text(d.get("source_ref"), "review tool result source")}
            text(d.get("finding"), "review finding")
            self.save(s, "review_recorded", {"disposition": d["disposition"], "source_ref": d["source_ref"]})
        elif op == "repair":
            require(s["phase"] in ("check", "release"), "repair requires a candidate or release gate")
            require(s["contract"]["lane"] in BUILD_LANES, "artifact lane needs plan revision")
            require(s["repairs"] < s["contract"].get("repair_budget", GRAPH["repair_budget"]), "repair budget exhausted")
            text(d.get("reason"), "repair reason")
            s["repairs"] += 1
            s.update(phase="build", candidate=None, review=None, release=None)
            self.save(s, "repair_started", {"reason": d["reason"]})
        elif op == "authorize":
            actions = strings(d.get("actions"), "authorized actions")
            require(set(actions) <= ACTIONS, "unknown action")
            source = text(d.get("source_ref"), "actual authorization source")
            s.setdefault("additional_authority", []).append({"actions": actions, "source_ref": source,
                                                            "contract_digest": s["contract_digest"]})
            self.save(s, "authority_recorded", {"actions": actions, "source_ref": source})
        elif op == "release":
            require(s["phase"] == "check", "release must follow candidate checks")
            require(s["contract"]["target"] in RELEASES, "run does not request release")
            self.check_results(s)
            require(not git(self.repo, "status", "--porcelain"), "release requires a clean committed candidate")
            needed = {"pr_opened": {"push", "pr"}, "merged": {"push", "pr", "merge"},
                      "staging_verified": {"deploy"}, "production_verified": {"push", "pr", "merge", "deploy"}}[s["contract"]["target"]]
            granted = set(s["contract"].get("authority", []))
            for receipt in s.get("additional_authority", []):
                if receipt["contract_digest"] == s["contract_digest"]:
                    granted.update(receipt["actions"])
            require(needed <= granted, "missing release authority: " + ", ".join(sorted(needed - granted)))
            s["phase"] = "release"
            self.save(s, "release_entered", {"authority": sorted(granted)})
        elif op == "resource":
            path = Path(text(d.get("path"), "resource path")).resolve()
            require(path not in (Path("/"), Path.home(), self.repo, self.common), "broad resource target forbidden")
            resource_id = identifier(d.get("id"), "resource id")
            require(not any(r["id"] == resource_id for r in s["resources"]), "resource already registered")
            s["resources"].append({"id": resource_id, "path": str(path),
                                   "kind": text(d.get("kind"), "resource kind"),
                                   "source_ref": text(d.get("source_ref"), "ownership proof"), "disposition": None})
            self.save(s, "resource_registered", {"id": resource_id})
        elif op == "skill":
            path = Path(text(d.get("path"), "skill path")).resolve()
            require(path.is_file(), "skill file missing")
            record = {"path": str(path), "digest": file_hash(path), "purpose": text(d.get("purpose"), "skill purpose")}
            previous = next((r for r in s["skills"] if r["path"] == str(path)), None)
            require(previous is None or previous["digest"] == record["digest"], "upstream changed during run; inspect and replan")
            if previous is None:
                s["skills"].append(record)
            self.save(s, "skill_bound", record)
        elif op == "seal":
            require(s["phase"] in ("check", "release"), "seal requires verified candidate or release phase")
            self.check_results(s)
            if s["contract"]["target"] in RELEASES:
                require(s["phase"] == "release", "enter authorized release phase first")
                self.check_results(s, release=True)
                observations = [r for r in s["receipts"] if r.get("observation") and r["subject"] == s["candidate"]]
                require(observations, "no captured release observation")
                observed = observations[-1]["observation"]
                require(observed.get("kind") == RELEASES[s["contract"]["target"]] and
                        observed.get("target") == s["contract"]["release_target"] and
                        observed.get("revision") == s["candidate"]["head"] and observed.get("healthy") is True,
                        "release observation does not prove requested target/revision/health")
                text(observed.get("resource_id"), "observed release resource id")
                s["release"] = observed
            for bound in s["skills"]:
                require(Path(bound["path"]).is_file() and file_hash(Path(bound["path"])) == bound["digest"],
                        "bound upstream changed; inspect before sealing")
            s["delivery"] = {"status": "completed", "target": s["contract"]["target"], "candidate": s["candidate"],
                             "contract_digest": s["contract_digest"], "receipt_ids": [r["id"] for r in s["receipts"]],
                             "release": s["release"], "time": time.time()}
            s["phase"] = "finish"
            self.save(s, "delivery_sealed", s["delivery"])
        elif op == "stop":
            require(d.get("status") in ("blocked", "failed"), "stop must be blocked or failed")
            s["delivery"] = {"status": d["status"], "reason": text(d.get("reason"), "blocking predicate"),
                             "candidate": s["candidate"], "time": time.time()}
            s["phase"] = "finish"
            self.save(s, "delivery_sealed", s["delivery"])
        else:
            raise GateError("unknown operation: " + op)
        return self.status(s)

    @staticmethod
    def process_exists(pid):
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True

    def run_check(self, run, actor, d):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            s = self.load(run)
            self.active(s, actor)
            if s["contract"]["lane"] in BUILD_LANES:
                self.has_writer(s)
            require(s["phase"] in ("build", "check", "release"), "check has no approved plan")
            definition = next((c for c in s["checks"] if c["id"] == d.get("id")), None)
            require(definition is not None, "unregistered check")
            phase = d.get("phase", "candidate")
            require(phase in ("red", "green", "candidate", "production"), "invalid check phase")
            require((definition["kind"] in ("release", "production")) == (s["phase"] == "release"),
                    "check kind does not match current phase")
            require(phase != "red" or definition["require_red"], "red proof not requested by definition")
            fingerprint = self.assertions(definition)
            prior = [r for r in s["receipts"] if r.get("check_id") == definition["id"] and
                     r.get("plan_epoch") == s["plan_epoch"] and
                     r.get("definition_digest") == digest(definition)]
            require(not prior or all(r.get("assertions_digest") == fingerprint for r in prior),
                    "assertion files changed; replan explicitly")
            before = subject(self.repo)
            if phase != "red" and s["phase"] in ("check", "release"):
                self.candidate_ok(s)
            execution = {"id": "check-" + uuid.uuid4().hex[:12], "check_id": definition["id"], "phase": phase,
                         "plan_epoch": s["plan_epoch"],
                         "subject": before, "definition_digest": digest(definition), "assertions_digest": fingerprint,
                         "started_at": time.time(), "controller_pid": os.getpid(), "child_pid": None}
            s["execution"] = execution
            self.save(s, "check_started", {"id": execution["id"], "check_id": definition["id"]})
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise
        result, exit_code, observation = "fail", None, None
        started = time.monotonic()
        output = ""
        proc = None
        try:
            proc = subprocess.Popen(definition["argv"], cwd=self.repo, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    start_new_session=True)
            self.db.execute("BEGIN IMMEDIATE")
            try:
                current = self.load(run)
                current["execution"]["child_pid"] = proc.pid
                execution["child_pid"] = proc.pid
                self.save(current, "check_spawned", {"id": execution["id"], "child_pid": proc.pid})
                self.db.execute("COMMIT")
            except BaseException:
                self.db.execute("ROLLBACK")
                raise
            # Drain pipes without unbounded memory/disk. Excess output fails the check.
            tail, size = b"", 0
            with selectors.DefaultSelector() as selector:
                selector.register(proc.stdout, selectors.EVENT_READ)
                while selector.get_map():
                    if time.monotonic() - started > definition.get("timeout", 120):
                        result = "timeout"
                        break
                    for key, _ in selector.select(0.1):
                        block = os.read(key.fileobj.fileno(), 65536)
                        if not block:
                            selector.unregister(key.fileobj)
                            continue
                        size += len(block)
                        tail = (tail + block)[-8192:]
                    if size > 1024 * 1024:
                        result = "output_limit"
                        break
            output = tail.decode(errors="replace")
            if result not in ("timeout", "output_limit"):
                remaining = max(0.01, definition.get("timeout", 120) - (time.monotonic() - started))
                exit_code = proc.wait(timeout=remaining)
                if phase == "red":
                    result = "expected_failure" if exit_code != 0 and definition["failure_contains"] in output else "fail"
                else:
                    result = "pass" if exit_code == 0 else "fail"
            if definition["kind"] == "release" and result == "pass":
                try:
                    observation = json.loads(output)
                    require(isinstance(observation, dict), "release observation must be JSON object")
                    observation = {key: redact(value) if isinstance(value, str) else value
                                   for key in ("kind", "target", "revision", "healthy", "resource_id")
                                   if isinstance(value := observation.get(key), (str, bool))}
                except (ValueError, GateError):
                    result = "fail"
        except subprocess.TimeoutExpired:
            result = "timeout"
        except (OSError, KeyboardInterrupt) as error:
            output, result = str(error), "interrupted"
        finally:
            if proc is not None:
                self.stop_process_group(proc)
                proc.stdout.close()
        try:
            if before != subject(self.repo) or fingerprint != self.assertions(definition):
                result = "subject_changed"
        except (OSError, GateError, subprocess.SubprocessError):
            result = "subject_changed"
        receipt = {**execution, "result": result, "exit_code": exit_code,
                   "duration_seconds": round(time.monotonic() - started, 3),
                   "output_tail": redact(output)[-4096:], "observation": observation,
                   "provenance": "local_subprocess", "finished_at": time.time()}
        self.db.execute("BEGIN IMMEDIATE")
        try:
            s = self.load(run)
            require(s["execution"] and s["execution"]["id"] == execution["id"], "execution ownership changed")
            s["receipts"].append(receipt)
            s["execution"] = None
            self.save(s, "check_observed", {"id": receipt["id"], "result": result})
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise
        return receipt

    @staticmethod
    def stop_process_group(proc):
        try:
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait()

    def work_list(self, s):
        return [json.loads(r[0]) for r in self.db.execute("SELECT state FROM work WHERE parent=? ORDER BY rowid", (s["id"],))]

    def status(self, s):
        return {"id": s["id"], "version": s["version"], "phase": s["phase"], "mission": s["contract"]["mission"],
                "target": s["contract"]["target"], "repo": s["repo"], "state_path": str(self.home / "runs.sqlite3"),
                "contract": s["contract"], "alignment": s["alignment"], "revision": s["revision"],
                "pending_inputs": [k for k, v in s["inputs"].items() if v["classification"] is None],
                "open_decisions": [v for v in s["decisions"].values() if v["answer"] is None],
                "questions_used": len(s["decisions"]), "candidate": s["candidate"],
                "checks": [{"id": c["id"], "kind": c["kind"]} for c in s["checks"]],
                "last_results": {r["check_id"]: {"result": r["result"], "id": r["id"]} for r in s["receipts"]},
                "execution": s["execution"], "work": self.work_list(s), "resources": s["resources"],
                "delivery": s["delivery"], "cleanup": s.get("cleanup"), "review": s["run_review"], "terminal": s["terminal"]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("operation", choices=["start", "list", "status", "input", "classify", "decision", "answer", "lock",
                    "plan", "revise", "lease", "check", "recover-check", "freeze", "review", "repair", "authorize",
                    "release", "resource", "skill", "seal", "cleanup", "finish", "stop", "work", "dispatch", "audit", "export"])
    p.add_argument("--repo", default=".")
    p.add_argument("--run")
    p.add_argument("--actor")
    p.add_argument("--input", type=Path, help="JSON request file; default reads stdin when piped")
    args = p.parse_args()
    sup = None
    try:
        if args.input:
            require(args.input.stat().st_size <= 256000, "request exceeds 256 KB")
            data = json.loads(args.input.read_text())
        elif not sys.stdin.isatty():
            raw = sys.stdin.read(256001)
            require(len(raw) <= 256000, "request exceeds 256 KB")
            data = json.loads(raw) if raw.strip() else {}
        else:
            data = {}
        require(isinstance(data, dict), "request must be a JSON object")
        sup = Supervisor(args.repo)
        result = sup.operate(args.operation, data, args.run, args.actor)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 1 if args.operation == "check" and result["result"] not in ("pass", "expected_failure") else 0
    except (GateError, OSError, ValueError, sqlite3.Error, subprocess.SubprocessError) as error:
        print(json.dumps({"error": str(error), "operation": args.operation}), file=sys.stderr)
        return 2
    finally:
        if sup:
            sup.close()


if __name__ == "__main__":
    raise SystemExit(main())
