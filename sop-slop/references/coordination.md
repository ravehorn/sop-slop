# Scoped coordination, protocol 1

Parallel development; serialized integration and production. One local Git common
directory, SQLite and Python stdlib. No daemon, LLM coordinator or remote service.
Every peer owns a separate worktree and branch. This is cooperative tooling, not
a sandbox: arbitrary shell commands and external actors can bypass it.

## Lean subagent delegation

At planning and meaningful checkpoints, identify work that can finish independently
of the lead's next action. Delegate when useful overlap outweighs briefing and
integration cost; do small or tightly coupled work directly. No agent-count quota,
extra approval gate, scheduler or nested manager layer. Use available host slots;
a working lead plus up to three bounded subagents is a starting shape, not a rule.

- The lead owns critical-path decisions, integration, shared-resource coordination
  and release, not personal execution of every check. Useful
  parallel outputs include an isolated implementation with focused tests, an audit
  of the next gate's real interfaces/fixtures/observations, and independent review
  or evidence reconciliation. Assign only currently useful work; authors cannot
  independently approve their own changes.
- Each brief names the outcome, exact base revision and needed sources, owned files,
  dependencies, acceptance checks, resource limits and forbidden actions. Return a
  commit or patch, actual check results and remaining gaps. Give minimal relevant
  context, not an entire long transcript; do not delegate the same investigation
  twice without a concrete independent-verification reason.
- Concurrent writers require separate worktrees/branches and valid existing
  coordination. In a shared checkout keep one writer; other agents read an immutable
  snapshot or prepare patches outside it. Do not mutate a frozen test subject.
  If isolation is unavailable, parallelize read-only preparation, not shared edits.
- Separate check ownership from execution concurrency. Delegate useful browser and
  database verification to bounded subagents, including execution, diagnosis and
  evidence handoff within existing authority. Serialization is not a reason to
  keep both on the lead. Assign the exact registered check, candidate/environment,
  owned output paths and cleanup responsibility; preserve authentic receipt capture.
- Run delegated checks concurrently when their actual fixtures, writes, ports,
  services, output paths and cleanup cannot interfere, measured capacity is adequate,
  and the pinned controller permits it. Browser/DB labels alone do not require
  serialization; a browser may use the very database another check resets. Unknown
  sharing requires inspection before overlap. One native run still serializes checks;
  do not bypass it with raw commands, new runs or changed gates merely to overlap.
  When constrained, retain subagent ownership and sequence execution through the
  existing authorized owner/controller; overlap safe preparation or other useful work.
  Never multiply paid calls or divide a cap into per-agent caps.
- Continue independent work after dispatch; wait only when the next action needs
  the result. The lead does not duplicate delegated checks or rerun valid results
  merely to take ownership; retain required integration and fresh-release checks.
- Integrate at a coherent boundary, review changed findings and run affected checks;
  perform required combined qualification once on the integrated candidate, not
  automatically after every handoff. Preserve all acceptance and fresh-release rules.
- Use compact event-driven updates. In Codex, `followup_task` resumes an idle
  subagent; `send_message` alone does not. Separate user-owned chats still require
  host messaging authorization. Record useful overlap, repeated expensive runs,
  conflicts and available elapsed/token measurements in the existing checkpoint;
  do not invent savings or add a parallel tracker.
- At a delegation checkpoint, report in the existing progress update:
  `Delegated: agent → deliverable; kept serial: work → resource/dependency reason;
  next join: result needed before action.` Name actual assignments, not intentions.
  If none are useful or safe, state the concrete reason; do not create busywork,
  duplicate completed reviews or add an approval gate to fill slots.

An authorized pilot on a running task is supplemental working guidance only:
preserve its immutable controller/SKILL package pin, run history and lineage,
acceptance gates, budgets and authority. Preserving the pin does not freeze run
state: normal authorized planning/replanning, freeze, checks, review, release and
closure may continue through the pinned controller when their existing predicates
are satisfied. This is not authority to reset state, bypass an exhausted repair
limit, weaken acceptance, transfer stale proof or add paid calls. A replan retains
history and requires proof valid for its new epoch; it is not a repair-budget bypass.
It does not activate scoped coordination or permit concurrent native operations.

## Activate only at a drained checkpoint

Preserve the old installed package. Use the reviewed new package by its immutable
versioned path. All active owners must acknowledge cutover, commit their own clean
checkpoint, finish/recover their checks and release the legacy writer themselves.
Do not interrupt their edits or checks. Inspect other active runs, not only the
two pilot peers. An owner confirmation also covers commands outside the supervisor.

Start a v0.8 coordination run, then call `coordination` with
`{"action":"activate","source_ref":"actual cutover approval/checkpoint evidence","participants":[...]}`.
First run `adopt-check` with each active owner's original run/actor and source_ref;
it is read-only and works before activation. Pass those returned receipts in
`participants`: activation rechecks their revisions, HEADs and clean worktrees.
Owners remain quiescent between preflight and adoption. The check cannot prevent
arbitrary filesystem writes; the explicit owner acknowledgment is required.
The transaction refuses any legacy writer or pending execution, activates scoped
claims, and fences **all legacy controller writes** in this repository. Existing
old connections are fenced too. Their read-only status still works. Activation
does not transfer any owner's claim and does not grant release authority.

Each owner calls `adopt` on its original run with its original actor and
`source_ref`. Only exact archived v0.7.1, v0.8.0 and v0.8.1 graphs are admitted;
other versions must use their pinned package or explicit successor. Adoption requires a clean tree,
no pending input/execution, and unchanged frozen subject/assertions when present.
It records the old version, graph and receipt IDs without rewriting old events,
receipts, plan epoch, skill pins or product scope. Preserve the old skill path;
bind the new SKILL.md as an additional `skill`. Historical evidence retains its
original meaning; changed commands, assertions or test fixtures require replan.
For a dormant old run with stale proof discovered after cutover, explicit
`adopt` with `replan:true` preserves historical receipts but clears candidate,
review and checks and returns to plan. The next plan advances its epoch; stale
proof cannot satisfy it. This is recovery, never silent evidence conversion.

There is deliberately no automatic downgrade or TTL takeover. If the new package
fails, stop new work, preserve the database, and repair forward from the pinned
package. Never remove triggers or edit SQLite to make a lease or check pass.

## Claims

`lease` defaults to the current real worktree path. `action:acquire` is idempotent.
The branch is also exclusive; detached worktrees need their own named branch.
`status.coordination.claims` returns an opaque token for each owned claim.
Release requires `action:release`, its `key`, and its exact current `token`.
Tokens reject stale releases, not arbitrary Git/provider actions.

Shared keys:

- `delivery`: one FIFO lane for integrating/rebasing the candidate against latest
  main, combined verification, merge, migrations, deployment, exact-SHA readback
  and rollback. Hold it only for that bounded delivery sequence, not development.
  Do not launch a deployment outside it. Release only when owned external jobs
  completed or were reconciled; the ledger cannot inspect external providers.
- `test:<resource-name>`: an actual shared DB/port/server/fixture group. Use the
  same canonical name for the same resources. Do not label shared ports isolated.

Acquisition returns `waiting:[key]` when queued: that is **not ownership**.
The owner releases; the earliest queued peer retries acquisition. Later peers
cannot jump the queue. `action:cancel` removes only your own queued request.
Acquire shared locks in this order only: delivery, then at most one test resource
group. Combined integration tests may need both. A test owner must release its
test claim before requesting delivery; reverse acquisition is rejected. Release
test claims/cancel queued tests before releasing delivery. Group test resources
that must be acquired together into one name. Worktree claims remain independent.
Release shared claims and cancel queues before releasing the tree.

An unclassified check requires `test:unclassified`. After inspecting its actual
environment, call `coordination` with `action:tests`, `resources:["test:name"]`
or `resources:[]` and a `source_ref` proving isolation. Empty means no shared mutable
resource, not “unknown.” Every check in that run uses this declaration, so split
different environments into separate runs or declare the conservative common lock.
Production checks and `release` require `delivery` regardless of test declaration.
Changed fixture/command semantics require explicit plan revision, not a relabel.

No time-based stealing. A crashed owner keeps its claims. Inspect process groups,
worktree and external jobs; use existing `recover-check` for dead checks (records
interrupted, never pass), then the recorded owner releases with its current token.
Live child groups remain a blocker. Cleanup releases only that run's claims/queue;
migration allocations remain durable. Never assume a quiet task is dead.

## Compact peer communication

`checkpoint`: `thread_id`, `summary`, `contracts:[]`, `dependencies:[]`. HEAD and
dirty state are observed. Dependencies name exact commits/contracts needed, not
“wait until the other task is done.” Shared tracker/map files merge at delivery;
they do not block independent implementation. Inspect real callers for semantic
conflicts; separate files are not proof of independent behavior.

`signal`: stable `key`, `recipient` run ID, `kind`, `body` (max 2,000 chars).
Kinds: `contract_changed`, `dependency_ready`, `integration_failed`,
`resource_released`, `review_requested`. Identical retries deduplicate; changing a
key's content fails. `inbox` with `after` reads at most 50 events and returns the
next cursor. Only record concrete dependency/resource changes, not heartbeat chatter.

**The mailbox does not wake a Codex task.** Use authorized native task messaging
for an actionable event with the exact artifact/commit and ledger event ID.
Recipients read their bounded inbox at a checkpoint; no transcript scraping or
all-to-all polling. A waiting task can do unrelated scoped work or yield. Until a
native event subscription adapter exists, delivery is explicit, not autonomous.

Before creating a migration, `coordination` `action:reserve-migration` takes a
14-digit `id`, matching `supabase/migrations/<id>_name.sql` `path` and `source_ref`.
Allocation is atomic and permanent; existing IDs in current linked worktrees are
rejected. This is collision avoidance for participating peers, not a substitute
for integrated migration-order and deployed-ledger checks.

## Limits

Repository-local claims do not serialize another repository, another computer,
or Lovable/provider actions. Use external branch/environment protections for
those actors. This pilot does not add cross-host coordination, an automatic merge
worker, automatic peer wakeups, or permission to resume paused services.
