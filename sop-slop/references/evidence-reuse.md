# Bounded planning and verification

## Plan one observable increment

Name one next deployed learning milestone, its user-visible outcome, practical
preview/release boundary, exact exit predicates and non-goals. A roadmap is not
the current completion gate. Challenge bundled release units: read-only runtime
does not automatically depend on later memory or full-generation features. Keep
genuinely inseparable writer/schema transitions atomic; never split by hiding an
unsafe old writer behind a flag.

Choose the deployment environment from explicit user authority and existing
context; do not turn every milestone into a new staging-infrastructure project.
Resolve compatible dependency revisions, existing-data risks and rollback before
using an approved main-project tenant canary. Local qualification, that bounded
canary and full feature completion are different claims, not interchangeable proof.

Before implementation, review the finite acceptance matrix at **assertion-level**:
which component owns each prerequisite, when that prerequisite exists, and which
actual fixture/oracle can exercise it. Check semantic cycles, not only a manifest
DAG. For example, an earlier persistence case cannot require managed actions from
a later slice which itself depends on that persistence work. Record precursor
proof separately from later managed integration; never rename it into a pass.

For each test layer name its distinct risk, case IDs, real assertions, fixture and
environment. One adequate execution can cover several case IDs through one check's
`criteria` list when **all** assertions actually run in the matching environment.
Do not invent an alias pass for an unexecuted assertion. Review oracle and fixture
adequacy before costly execution; distinguish missing adapters from missing
product behavior. Keep remaining obligations visible with their proper owner.

## Select tests from the causal change

Reproduce a failure narrowly, inspect the causal path and shared callers, fix one
bounded cause, and run the minimal affected checks. Expand for a concrete shared
root, cross-layer risk, schema/permission change or release integration—not every
failure, commit or receipt. Label failures product, test-oracle, or environment
using observed evidence; do not blame the product for an unstarted fixture.

After **two unrelated infrastructure failures**, stop launching broad suites and
diagnose the shared environment. Preserve failing receipts. Resume only after the
actual environmental predicate is repaired or a safe isolated alternative exists.
Do not turn a timeout into a skip/pass or silently remove the case.

Use focused checks during development and **one integrated** qualification at a
coherent release boundary. A relevant executable change after qualification needs
affected reverification; this is not permission to reuse stale evidence. Keep
tenant/privacy, stale-write/duplicate-effect, data integrity, spending and recovery
gates. Required linked migration-ledger checks before merge/closure still apply.
No routine full-map audit or live-provider repeat for prose-only reporting.

After two repeated repair/review cycles, or **one working day** without a deployable
increment, checkpoint scope, elapsed time, blockers and next user outcome. Diagnose
or propose a smaller safe boundary with exact retained/deferred obligations before
another broad round. This applies before freezing too; the frozen-candidate repair
counter is not a substitute. No automatic deadline pass, scope deletion, new
authority or promise that all complex work fits a day.

Report separately: **implemented** locally, **qualified** for named environment,
and **deployed** at exact revision/target. Publish a fixed remaining-predicate list,
not an expanding “gaps” count. Authorization blockers need authorization resolution,
not more tests. Preserve scoped worktree development and real shared-resource locks.

## Explicit evidence equivalence (v0.8.1)

**Mechanism limit:** any real code change invalidates every reusable check's
conservative repository fingerprint. This release solves HEAD/prose reruns, not
automatic retention of unaffected acceptance after code repairs. It does not
implement independently reviewed per-check dependency closures.

The practical narrow-testing path is to select a bounded implementation run's
acceptance checks before execution: register its causally relevant behavior and
regression checks, not the entire future release suite. Keep cross-layer release
obligations in the canonical plan and qualify them in the integration/release run
at the coherent boundary. A narrow run's seal means only its stated local target;
it cannot claim integration or deployed completion. During repairs run focused
diagnostics first and delay the broad qualification until the fix is stable.
If a full suite is already registered as a gate, a real code repair still requires
that gate before sealing. Do not delete it to get green; any genuine rescope must
be explicit, reviewed and preserve its obligations at the proper delivery gate.

The candidate remains HEAD plus all tracked/nonignored files. Freeze still clears
current review. Reuse is opt-in **before the original execution**, never reconstructed
from an old receipt. Default checks remain strict. The initial conservative scope
is every tracked/nonignored dependency except specifically reviewed exact narrative
Markdown paths; it is not an automatic per-module dependency graph. Source, schema,
generated code, fixtures, assertions, configuration, lockfiles and behavior docs
remain included. Ignored assertion files remain separately hashed as before.
Ignored dependencies must be measured by the environment check; otherwise do not
enable reuse. This includes the actual installed dependencies, not just a lockfile.

Register an `environment` check and an eligible product check:

```json
{
  "id": "recipe-behavior",
  "kind": "behavior",
  "criteria": ["stale-write", "undo-preserves-unrelated"],
  "argv": ["python3", "tests/recipe_checks.py"],
  "test_files": ["tests/recipe_checks.py"],
  "require_red": false,
  "reuse": {
    "narrative_paths": ["docs/evidence/recipe-receipt.md"],
    "environment_check": "recipe-environment",
    "max_environment_age_seconds": 60,
    "revision_independent": true,
    "reviewer": "actual-independent-reviewer",
    "source_ref": "actual-scope-and-oracle-review",
    "environment_coverage": "Actual toolchain, installed dependencies, test configuration and immutable/resettable schema/fixture baseline; no unmeasured mutable input"
  }
}
```

The separate check `recipe-environment` has kind `environment`, no criteria,
`require_red:false`, an actual observer command and its assertion/collector files.
It cannot substitute for product assertions. Its deterministic, nonempty output
must measure the relevant real environment; a constant, target URL or resource
name is not sufficient outside a labelled test simulation. No credentials in its
output. An independent reviewer must assess collector coverage and the claim that
the product check does not depend on HEAD, branch, diff, history or build revision.
Unobserved mutable dependencies mean reuse is ineligible.

Run the environment check immediately before the original product check. Both
must observe the same exact subject; freshness is bounded (1–600 seconds). The
runner captures complete output hashes, collector definition/assertion identity,
original dependency fingerprints, contract and plan epoch. Failed/interrupted
checks never become reuse sources.

After a HEAD-only or approved narrative change:

1. Freeze the new exact candidate.
2. Run only the inexpensive environment check again for that frozen candidate.
3. Call `reuse` with product check `id` and the **original observed**
   `source_receipt_id`. Reused receipts cannot become sources. Later failures
   block older evidence reuse; unknown snapshots require an ordinary check.
4. If excluded content changed, additionally supply `narrative_review` with the
   actual independent reviewer, source_ref, narrative-only finding and exact
   `changes:{"path":{"before":"observed hash","after":"observed hash"}}`.
   Hashes are available from receipt `reuse_evidence.narratives` and current
   `file_hash`. Review the actual delta: a path approval is not permanent permission
   to change behavior/criteria there. If it changes either, replan/rerun affected
   proof; do not sign a narrative-only attestation.

No directories/globs, executable/symlink files, AGENTS.md, SKILL.md or assertion
files may be excluded. The controller checks identities; it cannot determine prose
meaning or authenticate reviewers. This remains an explicit engineering judgment,
not automatic proof that a Markdown file has no runtime use.

The new linked receipt has provenance `explicit_evidence_reuse`, original source
ID and `executed_at`, new `reused_at`, fresh environment receipt ID and new candidate
binding. It is **not** a new product execution. Original receipts stay unchanged.
Each named check still has to cover its registered assertions; reuse does not
create new case mappings or migrate evidence between plan epochs/contracts.

## Review and release identity

An independent `review` may register exact `reuse_narrative_paths` for its reviewed
scope. It receives an ID and immutable dependency snapshot. After freezing, the
explicit `review-reuse` operation takes `source_review_id`, binding `source_ref`,
and the same exact independent narrative-delta attestation when needed. Only the
latest original accepted review can bind; new code, changed scope or rejected
findings require appropriate fresh review. HEAD-only changes need no repeated
whole-code review. For real code repairs, ask the independent reviewer to inspect
changed findings and causal impact rather than restart unrelated analysis; record
their actual fresh result, not invented retained acceptance.

`release`, `production` and `environment` checks are never reusable. Exact deployed
revision, provider target/health and required live qualification remain freshly
observed. A prose-only commit can reuse product evidence after equivalence, but
cannot claim that its new SHA was deployed because an older SHA was deployed.

## Safe rollout

Keep active packages pinned. Install a separately versioned release and ask owners
to adopt at clean stopped checkpoints; do not edit their worktrees or replace old
skill files. Existing receipts lack the new snapshots and are not retrofitted.
Owners can adopt rules immediately without claiming the new mechanic ran; enable
reuse only with an honest current plan, reviewed observer and new original proof.
Preserve v0.8 scoped coordination and active claim ownership during adoption.
Catalog/default routing is separate from changing a pinned run's package.
