# Retention lifecycle v1 (controller 0.8.3)

Close the last consumer, then reconcile owned disposable resources. Completion
and age alone are not deletion authority. This is a decision/receipt lifecycle,
not a filesystem deletion service, scheduler or database compactor.

## Initial closure and later revisit

1. Register resources during the run. Only `scratch` (regenerable artifacts) and
   `redundant_evidence` (raw artifacts with a reviewed retained replacement) are
   eligible here. Never relabel required evidence to make it disposable. Source
   worktrees, databases, package pins, approvals, financial records and the shared
   SOP store are not eligible; their maintenance is separately scoped.
2. Seal delivery. Stop resource owners and inspect actual dependencies, open files,
   peer claims and external consumers. Unknown means keep. A paused process is
   not proof of quiescence; a filename is not ownership evidence.
3. Call `retention` with a decision for **every** registered resource:

   ```json
   {"dispositions":{"scratch-id":{"state":"release","reason":"final consumer finished",
     "authority_source":"actual approval for this exact path",
     "inspection_source":"actual stopped-owner and dependency inspection",
     "no_longer_needed":true,"holds":[]}}}
   ```

   A preserved item instead needs `state:"preserve"`, `reason` and `revisit_when`.
   Redundant evidence additionally requires `replacement_source` (retained private
   manifest with original hashes and audit coverage) and `restore_source` (actual
   successful recovery verification). These are host attestations, not native
   proof that external archives are sound. Missing proof means preserve.
4. Read back `status.retention`, then call `retention-check` immediately before the
   host action. It checks revision, resource set, identity and native blockers.
   Keep writers stopped throughout. Directory stat is not a content hash: inspect
   the exact contents manifest separately. SQLite locks do not fence filesystem
   writers. The host must recheck targets and obey its own permissions.
   This read-only check is a host-required step, not a recorded native prerequisite
   proving the check preceded deletion; reconciliation cannot authenticate host
   actions or close the filesystem race window.
5. Perform only authorized exact-target disposal, preferring recoverable actions.
   No broad recursive targets. Record ordinary `cleanup` with `released` plus real
   action `source_ref`, or `preserved` plus reason and `revisit_when`, then `finish`.
6. If evidence is still needed, preserve it and hand off its revisit condition.
   Once met, use the **same pinned run**: `retention` → `retention-check` → host
   action → `retention-reconcile`. This terminal revisit leaves original delivery,
   cleanup, review, approvals, budgets and claims unchanged. No new delivery run
   or automatic schedule. Existing released receipts remain released in later
   batches; use preserved dispositions for those already absent resources.

Any intervening run mutation invalidates the release decision. Reinspect and
record a new decision if context changes. Missing paths before a decision or
uncertain outcomes are not successful disposal. After interruption inspect first;
do not retry deletion blindly. A recorded pre-action decision and actual action
evidence can reconcile absence; without those, preserve the unknown disposition.

Native blockers include unfinished/failed delivery, execution, unclassified input,
captured work, successor dependencies, outstanding owner test/delivery claims,
protected/redirected paths and overlapping peer resources/worktrees. Captured work
conservatively blocks release even if potentially unrelated; no bypass is added.
Preservation permits honest closure but is not reclaimed-space evidence.

## Compatibility and limits

Run graph changes to 0.8.3; SQLite schema stays 1. Do not replace a pinned 0.8.2
package or adopt an active run for this feature. Use versioned installation and new
runs by default. Existing explicit adoption gates still require separate authority.
Historical events and graph 0.8.2 remain intact.

This does not reclaim repeated event snapshots, compact the live store or cap
future growth. See `docs/retention-v1.md` in the source repository for the separately
reviewed migration plan. Report measured bytes after authorized cleanup, never
predicted savings or same-filesystem quarantine as recovered disk space.
