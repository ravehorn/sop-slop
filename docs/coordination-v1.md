# Parallel development, serialized delivery

Approved by Max on 2026-09-28. Scope: extend SOP's existing local supervisor and
pilot on `SAGE agent architecture` (V04) and `Finish SAGE V02 acceptance` (V02).

Before: separate worktrees still contend for one writer, including local checks.
After: each owns its worktree; shared test resources and one delivery lane remain
exclusive. No central agent, new service, or changes to product release authority.
Canonical operating contract: [coordination protocol](../sop-slop/references/coordination.md).

Acceptance:

1. Four real subprocesses run independent checks with overlapping intervals.
2. Same checkout/branch and shared-resource rivals cannot own simultaneously.
3. Delivery requests retain FIFO order; canceled heads and stale tokens are safe.
4. Pending writers/checks block activation. Already-open and real legacy package
   connections cannot write afterward. Explicit adoption preserves historical
   events/receipts and rejects dirty/stale checkpoints.
5. Crash/restart retains claims; pending checks cannot release them. Existing
   live-child recovery guards remain in force.
6. Targeted events deduplicate and resume by bounded cursor. Migration IDs do not
   become reusable on cleanup.
7. Live rollout requires owner acknowledgments, clean checkpoints and inspected
   resources. Prove real concurrent task progress, not just simultaneous claims.

Tests use disposable Git repositories and subprocesses. They are controller
evidence, not proof of SAGE correctness, production deployment or task wakeups.
Existing package regression/installer/replay checks remain required. Independent
engineering review requires atomic cutover, exact legacy allowlist and explicit
native event delivery; independent candidate review follows executable probes.

Rollout: preserve installed 0.7.1; deploy a versioned 0.8.0 package side-by-side;
drain active owners; activate atomically; each peer explicitly adopts and pins;
verify bounded live progress. No package overwrite during a pinned active run.
If any gate fails, peers retain the old workflow until safely drained; after
activation, fail closed and repair forward instead of bypassing database fences.
