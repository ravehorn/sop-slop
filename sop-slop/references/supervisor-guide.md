# Supervisor CLI

Python 3.9+ and Git; standard library only. Run the installed
`scripts/supervisor.py` with `--repo /absolute/repository`. Each operation accepts
one JSON object with `--input /absolute/request.json` or stdin. Use the host file
editing tool for requests outside the candidate. Mutation calls use `--run` with
the actual returned run ID and `--actor` with the recorded controller identity.
This identity check is consistency, not authentication.

```bash
python3 /path/to/sop-slop/scripts/supervisor.py start --repo /path/to/repo --input /tmp/contract.json
python3 /path/to/sop-slop/scripts/supervisor.py status --repo /path/to/repo --run run-RETURNED
python3 /path/to/sop-slop/scripts/supervisor.py lock --repo /path/to/repo --run run-RETURNED --actor controller --input /tmp/lock.json
```

`list` finds earlier runs. Exit 0 means the operation succeeded, 1 is an observed
check failure, 2 is an invalid request or failed gate. Errors are structured JSON.

## Start contract

```json
{
  "mission": "Archive recipes without losing them",
  "source_ref": "actual user message or approved spec",
  "actor": "controller",
  "lane": "approved-build",
  "tier": "T1",
  "target": "candidate_verified",
  "non_goals": ["hard deletion", "deployment"],
  "invariants": ["tenant isolation", "only managers mutate"],
  "assumptions": [],
  "authority": [],
  "sources": ["annotation-1", "annotation-2"],
  "problems": [{
    "id": "archive",
    "problem": "Old recipes clutter selection",
    "desired": "Hide and restore without deleting data",
    "task_ref": "docs/tasks.md#archive",
    "sources": ["annotation-1"],
    "criteria": [{"id": "restore", "given": "an archived recipe", "when": "its manager restores it", "then": "it is selectable with the same ID"}]
  }],
  "source_dispositions": {"annotation-2": "Export idea deferred as independent"},
  "repair_budget": 3
}
```

Lanes: `product-change`, `approved-build`, `strategy-decision`, `review-only`.
Targets: `decision_complete`, `spec_complete`, `review_complete`,
`candidate_verified`, `pr_opened`, `merged`, `staging_verified`,
`production_verified`. T1 is bounded with established patterns; T2 crosses
components/material behavior; T3 has major architecture/data/release risk.
T2/T3 require independent candidate review. A single unannotated request can use
empty sources; acceptance examples are still required.

Release targets need exact `release_target`, an `authority` subset of `commit`,
`push`, `pr`, `merge`, `deploy`, `production_read`, and `authority_source` when
nonempty. Empty authority can start a run but cannot pass release. Never invent it.

## Alignment and plan

- `lock`: `source_ref`, `basis` (why requirements are settled).
- `decision`: `id`, `kind` (`routine`, `behavior`, `scope`, `data`, `security`,
  `cost`, `authority`), `question`, `recommendation`, `source_ref`. Material choices
  also require 2–3 `options`, existing criterion IDs in `blocks`, and `reversible`.
  Routine choices auto-decide and do not count toward alignment check-ins.
  There is no question limit: every third answered material question makes status
  expose `alignment_check_in_due:true`, an advisory reminder to summarize settled
  choices and remaining uncertainty. It never blocks another needed question.
  Legacy `question_budget` fields are retained as input provenance only, not caps.
- `answer`: `id`, actual nonempty `answer`, `source_ref`. Optional
  `use_recommendation:true` is only for explicitly delegated reversible
  behavior/scope choices, never authority/security/data/cost.
- `plan`: `source_ref` and checks covering every criterion:

```json
{
  "source_ref": "docs/plan.md",
  "checks": [{
    "id": "restore",
    "kind": "behavior",
    "argv": ["python3", "-m", "unittest", "test_archive"],
    "criteria": ["restore"],
    "test_files": ["test_archive.py"],
    "require_red": true,
    "failure_contains": "AssertionError",
    "timeout": 120
  }]
}
```

Check kinds: `behavior`, `regression`, `required`, `artifact`, `release`,
`production`. Every criterion needs a behavior/artifact check. Release needs a
release check; staging/production also need a live production check. Inspect
assertions: broad expected error text is not enough if failure is unrelated to the
requested behavior. Set require_red false for existing regression/artifact/external
checks when appropriate, explaining the test choice in the canonical plan.

Arguments are literal, not shell expansion. Deliberate shell commands retain all
host privileges; this is not a sandbox. No credentials in arguments/artifacts.
Use existing integrations/environment, and avoid commands that dump secrets.
Test files must exist before check. Working directory is repo root. Timeout is
1–600 seconds; output over 1 MiB fails. Only a redacted 4 KiB tail is retained.
Redaction is best effort, so select safe commands. Failed results remain durable.

## Build and check

- `lease`: `action: acquire` before implementation, `release` afterward. One
  lease across linked worktrees. Never steal by time. Inspect an abandoned owner
  run/process/worktree, then close/release through that recorded owner before
  acquiring a new lease. Do not erase state to bypass another writer.
- `check`: `id`, `phase` (`red` before implementation; `candidate` after freeze).
  Phase is JSON input, not a CLI flag.
- `freeze`: empty object, binds HEAD plus tracked/nonignored working-tree files.
  Commit first for release. Changing docs/tests/code requires refreezing and
  reverifying. Intentionally ignored generated output can vary.
- `review`: real `reviewer`, `disposition` (`accepted`, `revision_required`,
  `fatal`), `finding`, `source_ref`. This is explicitly host review attestation,
  not observed subprocess truth. Review the current frozen candidate.
- `repair`: `reason`, bounded return to build preserving failures.
- `revise`: `reason`, `source_ref`, optional full `contract` if user intent changes.
  New contracts return to alignment; plan-only revisions return to plan. The next
  plan generation invalidates previous proof without deleting it. Do not replan
  merely to discard failure or reset budgets.
- `skill`: actual `path`, `purpose`; file digest is pinned. Upstream drift blocks
  closure. Resume with the pinned package instead of silently accepting change.

After a crash, status exposes pending execution. Never rerun blindly.
`recover-check` takes inspection `source_ref`, rejects a live supervisor/child
process group, and records interrupted—not pass. If no child ID was saved, actual
inspection must additionally support `confirmed_stopped:true`. It does not kill
uncertain/shared processes. Native checks stop their own process group on
completion, timeout or interruption.

## Inputs and pending work

- `input`: stable `id`, `summary`, `source_ref`; identical repetition is idempotent.
  Pending input blocks execution until classified.
- `classify`: `id`, legal `classification`, `reason`. Side quests/successors/
  replacements automatically create work items; replacement seals superseded.
- `work`: stable `key`, `kind` (`side_quest`, `successor_mission`, `improvement`,
  `dependency`), `title`, `reason`, `source_ref`. Repeated keys deduplicate.
- `dispatch`: work `id` and `action`. `prepare` requires explicit task-creation
  `authority_source`; call the native host tool only after preparation. `linked`
  records actual `thread_id` and tool `source_ref`. `unknown` preserves uncertainty;
  `not_created` needs evidence nothing was created before retry. `task` records a
  canonical `task_ref`. This operation never calls a host API itself.

## Release

`authorize` records newly supplied `actions` and `source_ref` bound to this
contract. Revised targets do not inherit extra authority. `release` checks proof,
clean committed state and required authority. Then use the approved delivery
path and registered release/live checks. The provider observation command must
query the actual provider and emit this JSON shape (example is not evidence):

```json
{"kind":"production","target":"https://app.example","revision":"exact deployed SHA","healthy":true,"resource_id":"actual provider deployment id"}
```

Kinds: pr, merge, staging, production. Target/revision/health must match the
contract/candidate, and resource ID must be nonempty. Dummy emitters are only for
explicitly labelled simulations. Reuse repository-specific CLI/adapters. Tests
must fail on wrong/unhealthy state. Generated merge commits require reconciling
the actual candidate and reverifying.

## Closure

- `resource`: `id`, exact `path`, `kind`, ownership `source_ref`. These rows cover
  run-owned filesystem items only, never broad roots. Record external process/port
  cleanup as attributed host evidence in the cleanup note; do not invent a path.
  Native check processes already have execution and process-group cleanup evidence.
- `seal`: empty object after proof. Otherwise `stop`: status blocked/failed and
  exact reason. Delivery becomes immutable.
- `cleanup`: `note` and `dispositions` keyed by resource ID. Each has state
  preserved/released and reason. Released paths need action source_ref and must
  be absent. This never deletes paths. Preservation with reason is valid closure;
  the writer lease is released after reconciliation. Deletion needs user authority.
- `finish`: classification no_issue/executor_issue/graph_issue/policy_issue,
  finding, source_ref. Optional hard_invariant_breach true downgrades effective
  terminal status without rewriting delivery. Optional proposal creates pending
  improvement work, never an automatic edit.
- `audit`: local state/event consistency and database integrity.
- `export`: full private state/work/event references; do not publish blindly.
  `status` is the smaller resume view.

SQLite transactions store the projection and append-only events together. This
is crash-consistent local storage, not a cryptographic audit service. Filesystem/
code access can bypass it. Never hand-edit the database to make a run pass.
Preserve package versions for old runs and rollback.
