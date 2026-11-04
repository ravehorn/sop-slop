# Retention v1 and shared-store recovery plan

Status: source implementation for controller 0.8.3; live migration not implemented
or authorized. Installed pins unchanged. Tests use synthetic files only.

## Acceptance

Given completed final consumers and an owned disposable artifact, release needs
fresh exact-target authority/inspection and actual host action evidence. Required,
active, unknown or shared resources remain protected. Terminal revisits must keep
delivery, review, approvals, budgets and claims unchanged. Old runs must refuse
implicit adoption. This increment is a retention gate, not a deletion engine or
solution to repeated database snapshots. The runtime contract is in
`sop-slop/references/retention.md`.

## Incident baseline (2026-11-03, not a current capacity promise)

MenuMind `.git/sop-slop/runs.sqlite3`: 4,456,212 pages × 4,096 bytes =
18,252,644,352 bytes (~17 GiB), zero free pages, 36,238 events, 400 runs,
23 nonterminal runs and 13 claims. Current run JSON totals 26,118,854 bytes.
`Supervisor.save` repeats full state per event; export parses all event JSON and
audit compares latest snapshot to current projection. VACUUM alone cannot remove
live snapshots. This inspection did not validate every historical event.

## Immediate recovery: keep schema 1

1. Inventory all writers, pins, runs and claims; obtain an explicit maintenance
   window, including scheduled users. One paused chat is insufficient. Never steal
   claims or force-close unknown execution.
2. Obtain Max's exact destination approval before transferring real run data
   off-device. Use private encrypted storage with verified access controls, not
   public artifacts or unverified cloud sync.
3. Re-read file size, sidecar sizes, journal mode, free capacity and integrity.
   With writers quiescent, use SQLite's backup API into a new destination. Never
   raw-copy a changing database, ignore WAL, or change live journal mode as a fix.
4. Destination capacity for uncompressed backup and independent restore proof:
   **`2 × B + J + H`**, with B current database bytes, J sidecar bytes and H an
   explicit reserve of at least 2 GiB. At the measured B and J=0, round up to
   **37 GiB available**. Add workspace if the selected conversion needs it. Keep
   at least 2 GiB source-volume operational reserve; abort if either volume drops
   below its plan. Sampled compression and future swap reduction are not capacity.
5. Verify integrity and streaming logical digests for schema, triggers, indexes,
   all rows/events/sequences, claims, work, signals, migration IDs and state. Restore
   into a separate copy and exercise actual pinned status/export/audit there.
   Record hashes and tested recovery steps; do not mutate the original for proof.
6. Review an exact switch for every pin. Current controllers use Git-common-dir-
   relative storage: mounting/indirection needs separate path, locking and failure
   tests. A backup is not a transparent replacement; same-volume moves free no
   space. Keep original until verified switch/readback/recovery, then obtain exact
   removal approval. Before switch, original remains authoritative. After switch,
   stop writers and reconcile new writes before rollback; never overwrite newer
   state with an older backup.

## Versioned storage prevention (follow-up, not implemented)

Keep current projections and authority/ownership rows complete. A schema-2 design
can losslessly compress history with codec, original length and canonical digest;
index `(run_id, sequence)`. Update readers/export/audit together, preserving event
identities and digests. Never replace schema-1 JSON with opaque compressed values.
Reject unknown storage versions before initialization: 0.8.2 initializes tables
and triggers before its version check, so an old open is not guaranteed read-only.
Old binaries must stay on untouched schema 1 until an explicit all-writer migration
is approved; otherwise defer the switch.

Per-snapshot compression still repeats expanding history. Measure long synthetic
runs, then consider immutable compressed event segments with bounded checkpoints
or reviewed deltas. Do not build a delta engine as an emergency disk repair. No
age-only pruning or deleting terminal projections: continuation/restart guards,
ownership, financial and audit dependencies can survive completion.

Before adoption: test corruption/truncation/unknown codecs, source changes,
insufficient capacity, concurrent writers and interruption at each copy/verify/
switch boundary. Compare every original export/audit digest, prove restoration,
preserve approvals/budgets and measure allocated bytes plus long-run growth.
Publish a separately versioned candidate and obtain explicit adoption authority.
