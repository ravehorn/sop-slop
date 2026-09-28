# Scoped coordination, protocol 1

Parallel development; serialized integration and production. One local Git common
directory, SQLite and Python stdlib. No daemon, LLM coordinator or remote service.
Every peer owns a separate worktree and branch. This is cooperative tooling, not
a sandbox: arbitrary shell commands and external actors can bypass it.

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

Each owner calls `adopt` on its original v0.7.1 run with its original actor and
`source_ref`. Only the exact archived v0.7.1 graph is admitted; other versions must
use their pinned package or explicit successor. Adoption requires a clean tree,
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
