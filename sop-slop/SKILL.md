---
name: sop-slop
description: Use for substantial product features, domain changes, or annotation batches that need intent alignment, bounded implementation and verified delivery. Also use for explicitly requested product reviews or strategy decisions. Not for isolated, already-clear small fixes.
---

# SOP SLOP v0.8.2

Turn what the user means into working, checked behavior. Keep one mission, ask
only questions that change it, and continue until its requested finish is proved
or a concrete blocker is recorded. A nested skill returning is not task closure.

## Understand without an interview ritual

Read the request, repository instructions, canonical product/task documents and
affected code. Distinguish **observations**, **user requirements**, **assumptions**
and **proposed solutions**. An observation is evidence of a problem, not automatic
approval of a suggested implementation.

State a short alignment brief: outcome, concrete before/after examples,
invariants, non-goals and requested finish. For each accepted problem write at
least one `given / when / then` acceptance example, including failure behavior
and permission boundaries where relevant. Reuse existing canonical specs/tasks.
Cluster duplicate annotations by root problem and account for every source,
including deferred/rejected ideas with reasons. Show the grouping before work.

If the request or approved spec already settles material questions, lock it
directly. Do not ask the user to approve a summary as a ritual. Otherwise ask only
the highest-dependency unresolved choice. There is **no fixed question ceiling**.
Clear bounded work usually needs zero to three questions; important or ambiguous
work may need more. After each three answered material questions, briefly summarize
what is settled and what still matters, then continue only with genuinely needed
questions—do not ask permission to continue. This is a check-in, not a stop gate.
Stop asking when remaining choices can safely be delegated, not when a counter
reaches three. Resolve environmental facts yourself and do not reopen settled
choices or ask speculative questions. Clear independent work need not wait for an unrelated
ambiguous problem: keep separate bounded runs linked to the same canonical tasks.

Routine reversible implementation, libraries, test seams, formatting and version
choices belong to the agent. Each question must name the behavior, scope, data,
security, cost or authority decision it blocks. Never ask `continue?` or repeat
release permission already supplied. “You decide” settles named reversible
choices, not unrelated or destructive authority.

## Save the run before implementation

For repository work, read [the supervisor guide](references/supervisor-guide.md)
and use `scripts/supervisor.py`. Start once; resume with `list` and `status`.
Local execution state lives under the repository's Git common directory, shared
by linked worktrees. Canonical docs remain product/task truth. Do not create a
parallel backlog or reconstruct a successful receipt after the fact.

The active phases are [understand → plan → build → check → release → finish](references/supervisor-graph.json).
The v0.6 `workflow-graph.json`, context, gate map and replay fixtures are retained
as **legacy diagnostics**, not a second active itinerary. Do not load them for a
v0.7 run. Resume older runs with their pinned package or close them honestly and
link a successor; never silently convert their evidence.

For strategy/review discussion without Git, use the same alignment/scope rules
and return the artifact. Do not initialize a repository or claim supervisor-
enforced closure merely to have a ledger.

## Pick the smallest useful route

Read [technique routing](references/technique-routing.md) when a specialist lens
is needed. Matt and gstack remain upstream-maintained techniques, not copied
native skills. Read the selected installed skill, record its actual path/digest
with `skill`, and preserve its true safety stops. Do not upgrade upstreams mid-run.

- Strategy: challenge the premise if needed, then produce the decision artifact.
  No engineering or deployment by default.
- Review-only: use the requested product/design/architecture/code/runtime lens.
  Findings are the deliverable, not permission to implement.
- Approved build: do not re-grill. Fill only missing plan/review evidence.
- Product/domain change: resolve domain ambiguities, challenge unproven value
  when material, synthesize the spec, review visible behavior before engineering,
  then implement vertical slices. T2/T3 need engineering review and an independent
  candidate review. Skip irrelevant ceremony with a concrete reason.

## Work and prove it

Use [bounded planning and evidence reuse](references/evidence-reuse.md) when
planning slices, selecting checks, diagnosing repeated failures or reusing proof.
Before implementation, map assertion-level prerequisites and their owners; reject
semantic dependency cycles. Name one bounded user outcome, practical preview/release
boundary, non-goals, finite exit predicates and next deployed learning milestone.
Do not make a whole roadmap or unrelated later feature the first release gate.
Keep implemented, qualified-for-environment and deployed states distinct.

Reproduce narrowly and classify failures as product, test-oracle or environment.
Run minimal causally affected checks; widen only for concrete shared/cross-layer
risk or the integrated release boundary. Review fixtures/oracles before expensive
runs. One adequate run can cover multiple case IDs only when every actual assertion
and environment matches. For assertion/parser/format repairs, exercise the same
helper offline on safe saved or synthetic outputs before one final affected
real-stack run. Cover supported formatting, units/numbers and timing/recovery;
prefer structured identities/values and observable invariants over prose templates.
Preserve exact business values, permissions, effects and error behavior. If the
same oracle failure class recurs, pause expensive retries until its diagnostics
and focused regression are reliable. Provider/runtime requirements still need
the smallest real path that proves them; synthetic results are not live proof.
After two unrelated infrastructure failures, diagnose the
environment before another broad run. After two repeated repair/review cycles or
one working day without a deployable increment, checkpoint and reduce/diagnose
scope before another broad round; preserve obligations and safety failures.

For user-facing repository work, read the project's maintained feature-map index
and affected entries (use its documented location; `docs/feature-map/README.md`
is a fallback). Use user paths, prerequisites, gotchas and existing verification
recipes to choose coverage; inspect source/callers for impact rather than trusting
the map as an exhaustive graph. Update affected entries and the index in the same
change when behavior, entry points, permissions or recipes change. Keep source
revision and actual runtime evidence distinct: mocked contracts are not live
database or production proof. Record gaps; never rewrite expectations to conceal
a regression. Full-map live sweeps are separately scoped work, not routine overhead.
If no map exists, follow existing project docs and propose one only when useful;
do not create a new map or audit unrelated features on every task.

1. Map each criterion/layer to real assertions, dependencies, receipt and remaining
   obligation in the existing plan/runner. Assertion files must exist at plan time.
   Prove an ordinary authentic user journey early, including existing-data edit/save
   and recovery where relevant; helper coverage is not a substitute. Put cheap
   oracle/environment checks in `requires` before expensive checks, and declare
   `freeze_requires` for the journey/readiness proof. No second acceptance catalog.
2. Follow [scoped coordination](references/coordination.md). After explicit
   activation, acquire your own worktree writer lease before implementation.
   Independent worktrees develop concurrently; never edit another owner's tree.
   Integration and production share one short FIFO `delivery` claim. Tests need
   a named shared resource claim or an explicitly verified isolated environment.
   Before activation the legacy repository-wide lease remains in force. Do not
   switch a running peer or steal a stale lease. Each peer owns its own run state.
3. Run the registered test with JSON `phase: "red"`, finish planned implementation
   in build, prove readiness, then freeze. Planned unfinished work is not a frozen
   candidate repair. Keep generated test artifacts outside the candidate
   or in intentionally ignored output paths. Do not count setup/import failures
   as the intended red proof.
4. Failures and review findings are work. `repair` reopens a bounded build; fix
   the root cause and recheck. `revise` explicitly changes the plan/test definition
   and invalidates proof. Never remove a failing assertion merely to get green.
   Resume the same run; a declared failed/blocked continuation inherits repairs,
   not new authority. Renaming/restarting a mission must not reset its budget.
5. Independent review inspects the current candidate and returns accepted,
   revision_required or fatal with evidence. Record the real reviewer/tool source;
   do not invent an identity. Rejection blocks even an optional review. If required
   independence is unavailable, report it rather than replacing it with self-review.

The supervisor observes exit status, bounded output and runtime, and binds proof
to code content, plan generation and assertions. Relevant changes need fresh verification.
Use one integrated qualification at the coherent release boundary, not focused
test → full suite → commit → identical full suite. Explicit `reuse` may bind an
eligible original pass during build or check after unchanged dependencies and a
fresh environment observation are proved. Full-repository scope remains the default;
an optional independently reviewed dependency closure also needs exact outside-delta
review. It never infers that unrelated-looking code is safe. It never reuses an
exact release/production observation or retrofits missing historical fingerprints.
Freeze still clears review; `review-reuse` explicitly retains only unchanged
reviewed content with approved narrative deltas. Real code fixes get targeted
independent rereview of changed findings and impact, not automatic acceptance.
Ignored build output is excluded; registered ignored test files are separately
hashed. Test adequacy and browser/service identity still need engineering judgment.

## New input without mission drift

Register each substantive new user input before further execution, then classify:

- `continuation_or_dependency`: required for the mission; keep it here.
- `side_quest`: independent work while active; capture a durable item and continue
  at the same phase. No inherited release authority.
- `explicit_replacement`: user replaces unfinished work; seal superseded/blocked,
  reconcile resources, and link a successor.
- `result_question`: answer about the result without reopening delivery.
- `successor_mission`: substantial work after sealed delivery; capture a new item.

Capture work **before** dispatch with a stable source key. Link the canonical task
when configured/authorized. Separate Codex task creation requires the user's
explicit request under host rules. Only then use `list_projects`/`create_thread`.
Record the actual task ID; a queued client ID is not a completed task ID. If
creation is uncertain, mark unknown, inspect existing tasks and reconcile; never
blindly retry. Pending work remains visible in `status`; no daemon is implied.

## Release to the requested finish

Use `candidate_verified` for a build without release authority. An explicit
implementation-through-production request binds routine repository delivery
authority once; review/planning requests do not. Record its source and exact
target. Compound ship/deploy skills may run only when **all** actions are scoped
and authorized. Preserve upstream safety stops and repository release safeguards.

Commit before the final release freeze; release requires a clean candidate.
After required checks, enter `release`, use the approved delivery path, then
capture provider-observed exact revision/resource/target/health and live behavior
through registered checks. Generated merge commits require reconciling the real
candidate and reverifying, not pretending revisions match. Ready/merged/deployed
is not production-verified without the live check.

This supervisor is not a sandbox or host hook. It cannot intercept arbitrary tools,
authenticate a pasted user decision, prove reviewer identity, or prevent false
chat claims. Host permissions and external protections remain the actual authority
boundaries. No paused memory/company service is required or restarted.

## Finish and resume honestly

`seal` only when the requested result is proved; otherwise `stop` records the exact
blocked/failed predicate. Reconcile run-owned resources after sealing. Preserve
dirty/shared/unpushed/unmerged/unknown resources with reasons. Destructive cleanup
needs separate exact-target approval; the supervisor does not delete them.
Then `finish` records safety, outcome, corrections/failures, unnecessary questions,
and an evidence-backed improvement if warranted. Learning is a linked proposal,
not an automatic skill/policy change. Delivery stays sealed.

Report outcome and actual checks, pending work/blocker, cleanup and terminal status.
No need to recite every phase. After context loss or nested-skill return, read
`status`, inspect live repository/process state and continue the incomplete phase.
Do not rebuild the interview.

## Codex questions

Follow current host question/permission rules. For an optional quality-improving
choice, use the native picker when available: one decision, 2–3 choices,
recommendation first. Empty answers are not submitted decisions. Continue only
with an already-authorized safe default. For a genuinely required material
decision or new permission, ask one concise plain-text question and stop. Never
automate Codex UI to fake a picker or make routine preferences into material gates.
