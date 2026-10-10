# RU01 execution improvements — v0.8.2

## Approved scope

Max requested implementation of the reviewed RU01 process findings on 2026-10-08.
The audit is planning evidence, not fresh SAGE acceptance. The source was SAGE's
`docs/plans/2026-09-20-sage-architecture/10-ru01-final-sprint.md` and acceptance
inventory. The prior proposal remained report-only; this increment changes SOP,
not SAGE product code, provider authority or the active RU01 package pin.

## Bounded change

- Existing guidance now prioritizes an authentic existing-data journey, actual
  case/layer/assertion mapping, the same oracle in focused probes, measured
  environment admission, compatible committed rollback and one current summary.
- Plans reject nonexistent assertion files before execution. Optional `requires`
  and freshness declarations gate checks; optional `freeze_requires` gates freeze.
  These enforce declared dependencies, not semantic correctness or test adequacy.
- Failed/blocked declared continuations inherit repair usage with an immutable
  link and nonincreasing cap. They do not inherit evidence, claims or authority.
  Exact-contract resets are rejected; prose-renamed missions are not inferred.
- Eligible evidence can bind during build, avoiding a readiness/reuse ordering
  loop. Conservative whole-repository dependencies remain default. Optional exact
  reviewed closures need independent original scope and outside-delta review.
  All assertions, fresh environment identity and exact release proof remain gates.

No dependency inference, daemon, scheduler, new acceptance catalog, general fixture
recorder, provider trials or live-database operations. No retrofitted historical
fingerprints. The exact 0.8.1 graph is archived for explicit owner adoption only.

## Verification contract

`tests/test_execution_gates.py` covers early atomic rejection, prerequisite
failure/freshness/ancestry, readiness, budget continuity and scoped build reuse.
Its initial ten-test run had nine intended assertion failures before implementation.
`tests/test_execution_gate_edges.py` covers reviewed failure-recovery, revision
bypass, parent integrity, implicit cycles, path aliases, exact delta review,
unchanged full-scope candidate review and archived-version adoption. Five of its
initial seven probes failed on the corresponding missing guards before repair.
A further intended-red probe caught the frozen-candidate/receipt-only commit
ordering loop; identity refresh and guarded reuse now permit readiness to refreeze
without spending a repair, while seal stays blocked until that refreeze.

The final committed candidate must pass `scripts/verify-package.sh`, including
legacy controller, coordination, reuse, replay and installer compatibility tests.
Use the final supervisor receipt/commit as execution evidence; this document does
not preclaim a result. Deterministic disposable-repository proof is not evidence
that RU01 or a paid-provider journey has passed in production.

## Field-guidance consolidation — 2026-10-10

Max authorized incorporating the subsequent sprint feedback, testing, pushing and
merging while preserving active pins. The guidance is consolidated in the existing
verification reference; the controller/graph is unchanged from v0.8.2. No new
approval ritual, daemon, tracker, cross-model requirement or product-policy change.
Reported SAGE results motivate the guidance; this release does not independently
requalify them or publish their private artifacts.

| Finding family | Maintained guidance |
| --- | --- |
| Invalid setup, duplicate installers, lost Task identity, scheduler/lease interference, expiry ordering | Fixture causality and lifetime |
| Missing/ordered migrations, global registries, invented RPCs, undiscovered tests, extracted globals | Dependency and API composition |
| Real packet/reader mismatch, stale revision owners, incomplete copy grammar, TTL retry and legacy plaintext writers | Actual producer → consumer |
| Naming/locale, changing locators, duplicate keys, focus/closing animation, accessible positive/negative scopes | Rendered behavior |
| Late authorization loss, redirect barriers, unready contenders, guessed lock order | Async effects and races |
| Native types, restore/ACL equivalence, process I/O, wrong-domain collectors, output/cache/redaction collisions | Installed interfaces and collection |
| Repeated setup failures, lost first causes, inferred holds, mutation after failed registration | Diagnose narrowly, retain useful evidence |
| Slow aggregate splitting, assertion-count drift, partial case credit, unnecessary requalification | Qualify the bounded outcome; existing explicit reuse rules |

Validation uses the existing package suite plus an independent scenario-based
guidance evaluation and coverage review. No wording-match tests or new runtime
mechanism are justified by these documentation changes. Pinned packages, active
run state and historical receipts are not rewritten; reuse is never retrofitted.
