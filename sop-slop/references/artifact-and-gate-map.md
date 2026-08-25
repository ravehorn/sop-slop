# SOP SLOP Graph Specification

## Problem

A long prose checklist can name good skills while still leaving critical behavior implicit: which stage is actually next, what proves completion, how failures return upstream, what needs human authority, and whether a later agent may silently reinterpret the route. The result is either ceremony at every step or unsafe automation.

## Solution

Use a supervised outcome graph. Nodes describe results, not agents. Named guards choose edges. Typed evidence proves completion. One controller advances the run while bounded executors perform stages. The exact active topology lives only in `workflow-graph.json`; this document owns intent, human experience, testing, and target-state policy.

```text
intake -> alignment -> spec and reviews -> vertical slices
       -> candidate fork/join -> release gates -> delivery receipt
       -> bounded resource cleanup -> run review -> terminal
                                         -> proposal?
```

Annotation-heavy reviews enter through a bounded parent queue before the ordinary lifecycle:

```text
annotations -> observations -> problem ledger -> canonical durable tasks
                                              -> one child SOP SLOP run at a time
                                              -> validated task status + parent receipt
```

A proposal never rewrites the active run. It becomes the input to a linked successor run.

```text
user intent + repository rules + canonical evidence
                         |
                         v
               single logical controller
              / route / guards / authority \
             v                            ^
      bounded executor ---------> typed evidence receipt
             |                            |
             +---- cannot advance --------+
```

```text
frozen candidate digest
          |
          +---- review_candidate ---------+
          +---- exercise_candidate -------+--> all_dispatched join --> resolution
          +---- run_required_checks ------+

Any changed candidate digest makes all three branch receipts stale.
```

Material competing judgment may temporarily call one reusable peer protocol without changing the lifecycle graph:

```text
eligible caller + frozen request
              |
              v
 bounded_peer_deliberation(profile)
 observe -> discuss -> revise? -> joint proposal -> consent -> controller validation
              |
              +---- exact typed return to the same run and caller
```

## User stories

1. As the operator, I want material choices presented one at a time with a recommendation, so that I can align the system without answering a questionnaire.
2. As the operator, I want routine stages to advance from evidence, so that I am not asked to approve reversible internal transitions.
3. As the operator, I want authority gates separated from completion, so that finishing analysis never grants permission to merge or deploy.
4. As a controller, I want named deterministic guards and explicit terminals, so that unknown state blocks instead of being guessed.
5. As an executor, I want a bounded stage, staged context, and an evidence contract, so that I can work flexibly without owning the workflow.
6. As a reviewer, I want evidence bound to an exact revision and stale evidence retained, so that I can audit why a run advanced.
7. As the operator, I want each run reviewed against ordered goals, so that the SOP improves without optimizing speed over correctness.
8. As the operator, I want proposed low-risk improvements tested and promoted in stages, so that the graph can learn without silently expanding its own power.
9. As the operator, I want unrelated side quests moved into linked Codex tasks, so that the primary mission keeps running without losing the new idea.
10. As the operator, I want reversible technical, version, and routine release choices auto-decided after alignment, so that the run stops only for consequential decisions or real blockers.
11. As the operator, I want an explicit implementation-through-production request to reach verified production by default, so that local completion and nested skill endings cannot silently shorten the mission.
12. As the operator, I want a large annotation batch reduced to its real underlying problems, so that repeated observations strengthen one diagnosis instead of creating duplicate work.
13. As the operator, I want every accepted annotation problem to exist in the canonical general task list and be checked off only from validated delivery evidence, so that work remains durable outside the conversation.
14. As the operator, I want material product, design, engineering, review, QA, or learning judgments challenged by specialists who respond to one another, so that the result reflects real peer influence without creating a second controller or losing the parent mission.
15. As the operator, I want each run to release its own temporary resources before closure, while preserving user work and requiring exact confirmation before any destructive cleanup.

## Core decisions

- One coherent requested outcome is one workflow run. T3 programs coordinate multiple linked runs.
- An annotation batch is one parent review mission. Compound annotations become atomic observations, observations cluster by underlying problem and desired outcome, and every observation retains exactly one primary problem or non-actionable disposition.
- Each accepted annotation problem receives exactly one idempotent durable task in the workspace's canonical general task list. Equivalent tasks are reused; duplicate annotations remain supporting evidence.
- Clear annotation problems start without reconfirmation. Only the affected ambiguous problem pauses for one inspect-first `/grill-me` decision at a time unless its dependency blocks the whole batch.
- Annotation problems execute sequentially as linked child SOP SLOP runs. The parent ledger and canonical task status update only after the controller validates each child receipt.
- Exactly one route card is bound to the run and anchors requested outcome and proof, non-goals, current node, requested completion, and authority source. Competing cards or later messages cannot silently replace it.
- Every new in-run request is classified as a required continuation/dependency, an explicit mission replacement, or a side quest. Side quests become linked Codex tasks and the parent resumes the same node; parent release authority does not transfer.
- The graph is hierarchical: a stable lifecycle graph contains bounded lane or alignment subgraphs.
- Only the named pre-build alignment and review hosts may instantiate the `prebuild_material_decision` child template. It suspends and resumes the same host, permits one active child, and requires a complete decision receipt. Lifecycle, implementation, and release topology stays static and versioned.
- One versioned `bounded_peer_deliberation` call/return template serves every allowlisted caller/profile pair. Design Council is only the `design` profile; profiles are data, not duplicated graphs.
- Deliberation is optional and requires material competing judgment unresolved by canonical evidence or an established pattern. Routine or deterministic decisions skip it.
- A deliberation request freezes the caller, run, stable mission-anchor digest, question, SHA-256 digest of canonical input references, profile version, roster, Luna/max runtime, acceptance criteria, hard invariants, budgets, authority, expected evidence, and exact return contract.
- Specialists observe independently, receive peers' lossless typed statements, answer named questions, expose claims and objections, revise within two rounds, and consent to one content-digested joint proposal without majority voting. Evidence/experiment resolution and a material-human picker are each limited to one cycle. Minority concerns remain auditable.
- The controller alone validates one closed deliberation disposition and returns to the exact caller. The child cannot choose a parent edge, change the mission, or debate away hard safety, truth, tenant/security, release, or verification guards.
- Guards are named pure predicates. Unknown or unevaluable means blocked plus a proposed unblocker; it never means false-by-default.
- Every ordinary branching stage classifies exactly one value from a closed outcome table. Each value maps to one guard and one edge; missing or multiple values are invalid. Explicit forks are the only multi-edge dispatch.
- Ordinary branching is XOR. Parallel work uses explicit forks and `all_dispatched` joins only for read-only work against a frozen revision or isolated writers with leases.
- Candidate joins bind the exact fork, subject, branch receipt IDs, and receipt snapshot they validated; candidate-resolution transitions name that exact join. Later or unbound evidence cannot retroactively turn a failed gate into acceptance.
- Revision, retry, and recovery edges have named budgets supplied by the authority envelope. Budget exhaustion blocks the run.
- Completion evidence is typed, inspectable, and bound to the subject it proves. A slice receipt binds slice ID, approved plan digest, and delivered commit; only the assembled candidate gate binds the frozen combined revision.
- A changed dependency makes evidence stale without deleting it. Only affected downstream stages reopen.
- Gating reviews complete by recording exactly one disposition: `accepted`, `revision_required`, or `fatal`. Only accepted advances; revision takes a bounded back-edge to the owning artifact; fatal closes with evidence.
- The controller owns transitions. Skills, humans, agents, and deterministic tools are allowlisted executor kinds.
- Subagent delegation is an execution overlay on eligible outcome nodes. It does not add lifecycle edges, create peer controllers, or let a delegation receipt satisfy node completion.
- Every specialist execution is fresh. Persistent role configuration may project a stable role definition, but continuity comes only from canonical graph artifacts and reviewed shared memory passed into the task.
- The controller selects a named role, concrete currently available model, and reasoning effort using ambiguity, risk, cost, and parallelizability, then validates the returned evidence itself.
- Read, review, test, and QA work may run in parallel against frozen inputs. Writers are serialized unless isolated workspaces and leases prove disjoint slice ownership.
- Active v0 release nodes match real executor boundaries: `/ship` and `/land-and-deploy` are compound nodes and require their complete authority envelopes before invocation.
- Compound means the outer graph cannot pretend to pause an executor between its documented steps. It does not bypass executor-local safety stops; first-run setup, readiness failures, conflicts, permission failures, or unhealthy deployment return blocked or failed evidence to the compound node.
- A run can complete at decision, spec, candidate, PR, merged, staging, or production level, according to the requested completion target.
- An explicit implementation-through-production request defaults to `production_verified` and binds routine non-destructive commit, push, PR, merge, deploy, verify, and bounded recovery authority for the repository's existing release path. The user may explicitly narrow the target; repository rules and safety stops always override it.
- Once an alignment lock exists, the controller auto-decides reversible technical, implementation, testing, version-tier, and routine release-mechanics choices. Human questions remain only for locked behavior or scope changes, authority/security/data expansion, destructive or hard-to-reverse actions, meaningful spend or external communication, and production-target changes.
- A nested skill's final response is evidence returned to the controller, not a workflow terminal.
- Every edge entering `record_run_receipt` explicitly sets delivery status to `completed`, `blocked`, or `failed`; no terminal meaning is inferred from prose or node names.
- Every delivery receipt flows through one run-resource reconciler before learning review. Cleanup is limited to exact resources created or claimed by the current run and binds its receipt to the manifest digest.
- Dirty, untracked, unpushed, unmerged, shared, canonical, leased, ownership-unknown, recovery, and debug resources are preserved with reasons. Broad roots, unresolved variables, substitutions, globs, and unconfirmed shared caches are forbidden targets.
- Process, port, and lease release may proceed when it does not delete data. File, worktree, environment, or cache deletion requires one exact recoverability card and a digest-bound explicit `yes` or `do it`; standing preferences and empty picker results do not count.
- Worktree removal additionally proves run ownership, a non-primary workspace, clean and tracked state, pushed commit durability, merge or exact disposal consent, and no active lease. Cleanup retry is bounded.
- Human overrides are scoped, expiring exceptions. Hard safety, truth, tenant, data-loss, and authority invariants are not overridable.

## Delegation execution

The smallest stable role catalog covers the real independent workloads:

| Role | Typical eligible work | Access ceiling |
| --- | --- | --- |
| `explorer` | program mapping, code or architecture discovery, primary-source research | read-only |
| `implementation_worker` | one approved vertical slice or bounded candidate repair | one isolated disjoint slice, or serialized writes |
| `reviewer` | product, design, engineering, code, security-lens, and post-run review | read-only |
| `qa_tester` | browser/runtime QA and repository checks against a frozen candidate | read, execute checks, and test artifacts only |

The controller prepares a delegation envelope, spawns a fresh execution, receives a delegation receipt, validates the referenced evidence, and only then evaluates the node's normal completion predicate. Missing, stale, out-of-scope, or unverified results are rejected or routed to a bounded repair; they never advance the graph.

Ordinary model choice is resolved at dispatch from the currently available catalog, so model IDs do not become stale graph constants. Prefer the fastest suitable model for low-ambiguity, low-risk, cost-sensitive work; a balanced model for ordinary exploration and QA; and the strongest suitable coding or reasoning model for high-risk implementation, architecture, security, or ambiguous review. Raise reasoning effort as ambiguity and consequence rise. Every receipt records the concrete model and effort actually used. Deliberation is the explicit exception: every specialist and proposal owner is pinned by contract to `gpt-5.6-luna` at `max` reasoning and must record both in its envelope and receipt.

Parallelizability changes scheduling, not authority. Read-only and test branches may run concurrently on one frozen digest. Active v0 serializes implementation and repair because it has no writer fork. A future explicit writer fork may run multiple writers only when their workspaces, leases, files, and acceptance seams are disjoint.

## Human interaction

Codex shows a compact route card and mission anchor at intake, then surfaces only material decision nodes, blockers, revision edges, genuinely missing authority, linked side-quest tasks, and the final run and review receipts. Every material choice uses the native multiple-choice picker when available and records question, choices, recommendation, actual answer, actor, scope, and time. Empty or missing answers remain unanswered.

The visible information order is:

1. what stage or gate the run is at
2. what changed or why the run needs the user
3. the evidence, consequence, and exact next action

| State | What the user sees | What happens next |
| --- | --- | --- |
| Route | lane, tier, canonical source, selected and skipped stages, current stage, next material gate | run starts unless classification itself needs a decision |
| Annotation batch | source count, observation count, grouped problems, duplicates, impact/confidence, durable task links, and per-problem status | clear problems enter the sequential child-run queue; only material ambiguity pauses its problem |
| Working | current material stage and expected evidence; routine internal transitions stay compact | controller advances on valid evidence |
| Deliberation | frozen question, profile and roster, current bounded round, objections, retained concerns, and exact caller | controller routes peer turns, validates one closed disposition, and resumes only the invoking node |
| Side quest | brief linked-task notice while the parent mission and current node stay visible | new task owns the bounded tangent; parent resumes immediately |
| Decision | one question, 2-3 choices, recommendation, and one-sentence tradeoffs | selected answer becomes decision evidence; empty remains unanswered |
| Revision | failed evidence, owning stage, invalidated downstream evidence, and bounded back-edge | repair runs against the same requested outcome |
| Blocked | exact failed or unknown guard, missing fact or authority, owner, and proposed smallest unblocker | run waits or closes blocked without guessing |
| Failed | non-recoverable reason, preserved evidence, and available recovery boundary | run closes failed after review |
| Cleanup | exact run-owned inventory, resources released, resources preserved with reasons, and one recoverability card only if deletion is required | controller verifies reconciliation or asks once for the exact destructive target list |
| Completed | requested completion level, strongest evidence, stages skipped, run-review result, and proposal if any | run closes; a proposal may start a linked successor run |

The journey should feel oriented at intake, in control at decisions, informed during revision, able to act when blocked, and confident at completion. Status meaning must be present in text, never color alone. Picker labels stay short, keyboard-accessible through the native Codex control, and equivalent typed choices appear once when the picker is unavailable.

Buzz is a target control-room projection and decision relay, not a transition authority. A future Buzz-backed run ledger must pass the same append-only, idempotency, ordering, correlation, access-control, and replay conformance tests as any other backend.

## Run review and improvement

Every terminal attempt passes through `record_run_receipt`, `reconcile_run_resources`, and `review_run`.

The review uses an ordered objective rather than a blended score:

1. preserve hard safety and truth constraints
2. achieve the requested outcome correctly
3. reduce human corrections, retries, and invalidated work
4. then reduce intervention, elapsed time, and cost

The review classifies the root cause as `no_issue`, `executor_issue`, `graph_issue`, or `policy_issue`. “Review every run” does not mean “change after every run.” A versioned proposal is created only when evidence supports a repeatable cause.

The immutable run receipt retains delivery status. The run-review receipt records both delivery status and effective status. If a successful review proves a hard-invariant breach, preserve the delivery receipt and set effective status to `failed`. If the reviewer itself fails, emit a degraded receipt with `review_status=error`, `root_cause_class=policy_issue`, the error, and no proposal; effective status remains the original delivery status.

### Promotion stages

1. validate the candidate graph structurally
2. replay representative prior run receipts
3. run an independent forward test on unseen work
4. compare against the ordered objective and hard invariants
5. apply the promotion gate
6. activate a new immutable graph version or reject the proposal

V0 is proposal-only. Before executable historical scenario replay and an independent semantic evaluator exist, future auto-promotion is limited to presentation-only and diagnostic-only changes inside a human-approved ceiling. Node semantics, topology, guards, and evidence requirements remain human-approved. Low-risk semantic promotion becomes eligible only after replay, independent evaluation, and a separately human-approved semantic ceiling. No promotion may expand authority, weaken a hard invariant, remove required evidence, change production or tenant/data boundaries, or enlarge its own ceiling.

## Strategy-decision lane

`grill-me -> office-hours? -> canonical decision artifact`

- Use `office-hours` only for demand, wedge, customer problem, or product opportunity.
- Stop after the decision artifact unless the decision creates product behavior.
- Current market, legal, financial, and platform claims require primary-source research.

## Product-change lane

`wayfinder? -> grill-with-docs? -> office-hours? -> plan-ceo-review -> to-spec -> plan-design-review? -> plan-eng-review -> task SSOT/to-tickets? -> implement -> review -> qa? -> ship -> land-and-deploy -> resource cleanup -> run review`

| Stage | Required input | Completion evidence | Skip rule |
| --- | --- | --- | --- |
| `wayfinder` | T3 or multi-session ambiguity | Decision map with a clear frontier | Skip when one session can hold the route |
| `grill-with-docs` | Unsettled domain or hard decision | Shared understanding plus updates to the repository's canonical glossary/ADRs where warranted | Skip when canonical language and behavior are already settled |
| `office-hours` | Unsettled problem, demand, wedge, or premise | `accepted`, `revision_required`, or `fatal` review disposition | Skip when these are evidenced in the canonical plan |
| `plan-ceo-review` | Substantial scope, value, or economics | Typed review disposition plus reviewed scope evidence | Skip for non-product or narrowly technical work |
| `to-spec` | Settled intent and vocabulary | Canonical spec with behavior, seams, scope, and verification | Never use it to restart the interview |
| `plan-design-review` | Human-facing behavior | Typed disposition plus reviewed states, flows, accessibility, and interaction decisions | Skip only when no person sees or interacts with the change |
| `plan-eng-review` | Canonical spec and settled UX | Typed disposition plus reviewed architecture, data flow, failures, security, tests, and rollout | Required for T2/T3 build work |
| task bridge | Reviewed spec | Canonical vertical slices and dependencies | Use `to-tickets` only when its tracker is canonical and non-duplicative |
| `implement` | Approved slice and test seams | Slice receipt bound to slice ID, plan digest, delivered commit, and focused checks | One vertical slice at a time |
| gstack `review` | Non-empty diff against a fixed point | Findings fixed or explicitly resolved | Required before landing a substantial change |
| gstack `qa` | Runnable UI or service | Exercised user flow and re-verification | Use strongest repo runtime check when browser QA is not applicable |
| gstack `ship` | Clean verified candidate and full commit/push/PR authority | Compound execution receipt, pushed branch, accurate PR, and verification | Atomic v0 node; do not split with prompt instructions |
| gstack `land-and-deploy` | Merge-ready PR, supported deploy path, and full merge/deploy/verify/recovery authority | Compound execution receipt covering merge, deployment, verification, and recovery result | Atomic v0 node; split only after stoppable adapters exist |

## Review-only lane

Select the earliest disputed lens and stop after its output:

`office-hours? -> plan-ceo-review? -> plan-design-review? -> plan-eng-review? -> review/qa-only?`

Do not turn review authority into implementation authority.

## Gate policy

### Human decision gate

Before alignment, block on material strategy, scope, domain, behavior, pricing, or taste choices. After alignment, block only when a choice changes the locked behavior or scope, expands authority/security/data boundaries, is destructive or hard to reverse, causes meaningful spend or external communication, or changes the production target. Reversible test seams and technical choices are controller-owned after alignment. Use the Codex picker adapter for remaining material choices.

### Evidence gate

Advance automatically when the required artifact or verification exists and no unresolved decision remains.

For gating reviews, evidence that a review occurred is not evidence that it passed. The typed disposition owns the edge: accepted advances, revision-required returns to the owning stage within budget, and fatal closes.

### Authority gate

Block on external publication, destructive actions, push, PR, merge, deployment, or production actions unless already authorized by the request and repository rules. An explicit request to use SOP SLOP for implementation through production supplies routine non-destructive release authority for the selected repository's existing path; record it once in the authority envelope and never reconfirm it at ship or deploy. Because active `/ship` and `/land-and-deploy` executors are compound, collect their entire scoped action and recovery envelope before invoking either one.

### Back-edge gate

When a downstream finding invalidates upstream truth, return to the owning stage, update the canonical artifact, and re-run only affected downstream stages.

## Testing decisions

The executable seam is the graph contract, not every upstream skill. The standard-library validators check duplicate IDs, references, executor kinds, reachability, terminal reachability, evidence and predicate references, fork/join pairing, bounded cycles, decision receipts, durable slice bindings, compound release authority, the mandatory run-review path, every closed outcome table, exact replay edge IDs and outcomes, and delegation role, receipt, authority, freshness, mission/input/proposal binding, peer exchange, consent, and writer-isolation rules. Trace fixtures must follow real edges and select the table value mapped to each branching transition.

After validation, supervise representative traces containing these behaviors:

1. a material Codex picker decision produces immutable decision evidence
2. a failed candidate check returns through `repair_candidate`, invalidating only revision-bound downstream evidence
3. missing release authority stops before the external action and still produces run and review receipts
4. full production release invokes the two compound release executors only after complete authority
5. a confirmed late hard-invariant breach preserves the delivery receipt and closes failed
6. a fresh specialist returns bounded evidence that the controller validates without delegating the transition
7. an unrelated request creates a linked side-quest task and the parent resumes the same node
8. an aligned implementation run auto-decides its version and reaches production verification without repeat ship or deploy confirmation
9. an annotation batch maps every observation, groups duplicate evidence, creates or reuses one canonical task per problem, executes two problems sequentially, and closes only after both child receipts synchronize task status
10. design and engineering callers reuse one deliberation template; peers receive and answer one another, an evidence-based objection causes bounded revision, Luna/max is enforced, and both results return to their exact callers
11. run cleanup inventories only current-run resources, preserves unsafe or still-needed work, rejects broad targets and inferred consent, and removes a worktree only after exact confirmation plus every cleanliness, durability, and lease proof

Upstream skills retain their own tests. A predicate evaluator, workflow runtime, distributed lease manager, and persistent ledger are out of scope for v0.

```text
STRUCTURAL CHECKS                              SUPERVISED TRACE
[tested] valid contract                        [required] picker -> decision receipt
[tested] duplicate keys and IDs                [required] failed check -> repair -> reverify
[tested] references and executor kinds         [required] missing authority -> no external action
[tested] reachability and terminal reachability
[tested] fork/join pairing and bounded cycles
[tested] predicate definitions and review path
[tested] dynamic-decision host boundary
[tested] degraded-review safety
[tested] closed outcome-table coverage and trace continuity
[tested] durable slice evidence binding
[tested] compound release boundary and authority policy
[tested] late hard-invariant downgrade
[tested] delegation role, receipt, freshness, controller, and writer-isolation policy
[tested] generic deliberation registry, Luna/max, bounded discussion, hard guards, and exact return binding
[tested] current-run cleanup scope, exact target binding, preservation guards, explicit destructive confirmation, and bounded retry
```

## Failure modes

| Failure | Detection | Handling | Visible result |
| --- | --- | --- | --- |
| malformed or inconsistent graph | validator | reject activation | exact contract errors |
| guard cannot be evaluated | controller | block at originating node and propose smallest unblocker | blocked state with owner and missing fact |
| picker returns empty | decision completion remains false | one typed fallback, then wait | unanswered decision, no inferred default |
| evidence belongs to an older digest | completion or join predicate | retain as stale and reopen only dependents | revision state naming invalidated evidence |
| revision or recovery budget is exhausted | bounded-edge policy | close blocked or failed | remaining budget and terminal cause |
| external action completes | compound result enum is exactly one of succeeded, blocked, or failed | only succeeded advances; blocked and failed close through the receipt path | exact compound action and verification evidence |
| post-run reviewer fails | learning policy | emit proposal-free degraded review receipt | delivery status preserved; learning error visible |
| specialist exceeds scope or returns unverified evidence | delegation receipt and controller validation | reject the return, preserve evidence, and repair or block within budget | rejected delegation with no graph transition |
| post-run review proves hard-invariant breach | ordered reviewer plus evidence | preserve delivery receipt; set effective status to failed | original and effective statuses both visible |
| later slice moves repository HEAD | durable slice receipt check | keep earlier receipt valid when slice ID, plan digest, and delivered commit remain valid | no unnecessary rework; final candidate re-verifies integration |
| candidate branch never returns | join cannot complete | block after the authority-envelope limit | missing branch named; no partial join success |
| unrelated request arrives mid-run | focus classifier plus mission anchor | create a bounded linked task without changing the parent route, target, or current node | side-quest link followed by immediate parent continuation |
| nested skill returns a final message | controller still owns the nonterminal node | validate evidence and select the next legal edge | no premature outer-run stop |
| annotations are treated as tasks | ledger counts or task idempotency receipts do not reconcile | atomize, cluster by underlying problem, and reuse equivalent canonical tasks | fewer durable tasks than source annotations when evidence overlaps |
| ambiguous annotation blocks the batch | unrelated ready problems remain in the ledger | pause only the affected problem and continue dependency-safe ready work | one focused question without losing clear work |
| durable task is checked off from prose | child receipt or controller validation is missing | keep the task in progress or blocked until evidence is validated | task status matches proven delivery state |
| independent reports masquerade as deliberation | no lossless peer broadcast, named response, or position-change evidence | reject the return and resume the bounded discussion if budget remains | no joint proposal accepted from isolated summaries |
| deliberation tries to replace its caller | run, node, input digest, profile version, or return node differs from the request | reject the return and preserve the parent mission and suspended caller | invalid return receipt; no parent transition |
| objection is treated as a vote | objection lacks a violated requirement or missing evidence, or majority count selects the result | route to revision, evidence, one material human decision, or block | dissent remains visible and no vote grants acceptance |
| deliberation reaches a hard gate | proposal conflicts with safety, truth, tenant/security, release authority, required verification, or failed ship/deploy evidence | return fatal or blocked; never waive the gate | exact invariant conflict and caller remain visible |
| cleanup scopes by category or location | target lacks current-run ownership and an exact resolved identity | preserve it and reject the receipt | no broad or cross-run deletion |
| cleanup mistakes dirty or unmerged work for waste | git/workspace proof fails a preservation guard | retain the resource with the exact reason | delivery evidence stays available for resume or recovery |
| destructive cleanup relies on standing intent or an empty picker | decision receipt does not bind the current manifest digest and exact targets with `yes` or `do it` | stop at one recoverability card | no inferred deletion authority |
| cleanup action or verification fails | exact run-owned resource remains unresolved | preserve it, record the blocker, and close effective status as blocked or failed according to the delivery and safety evidence | immutable delivery status remains separate from cleanup closure |

## Implementation strategy

Keep graph-contract writes serialized because the JSON, validator, instructions, vocabulary, and human specification are one tightly coupled version. Independent read-only semantic review and replay may run in parallel against the frozen candidate.

## Rollout and rollback

Activate v0 in supervised mode after the validator and representative trace pass. The graph becomes the canonical route, but existing authority gates remain unchanged and transitions are decision-focused in the UI. Preserve a backup of the prior skill before installation. Restore that backup if skill validation, graph validation, or the trace fails.

## Target architecture, not active v0

- A cheap deterministic controller may later persist runs in a conforming Run Ledger.
- Buzz may provide projections, alerts, decision relay, and operator views after ledger conformance.
- Hermes, Codex, and other agents remain bounded executors or clients; none becomes a peer transition authority.
- A Boolean predicate DSL is justified only after repeated guard composition makes named predicates unmaintainable.
- Fine-grained publish, PR, merge, deploy, verify, canary, and recovery nodes require real stoppable adapters. Until then, the active graph keeps `/ship` and `/land-and-deploy` compound.
- Distributed workers require leases, idempotent dispatch, frozen inputs, and revision-bound joins.
- Delayed customer or production outcomes are collected in linked observation runs rather than keeping delivery runs open.
- Semantic graph auto-promotion requires executable historical scenario replay, an independent semantic evaluator, and a separately approved semantic policy ceiling.

## Out of scope for v0

- a durable background workflow engine
- direct Buzz, Hermes, or Nostr integration
- unscoped release authority outside an explicit SOP SLOP implementation-through-production request
- automatic graph mutation or promotion
- arbitrary OR splits, unbounded peer swarms, or majority-vote transition authority
- a new product, task, or domain source of truth

## Design review result

- Information architecture: 9/10 -> 10/10 after the visible information order was specified.
- Interaction states: 6/10 -> 10/10 after route, working, decision, revision, blocked, failed, and completed states were defined.
- User journey: 8/10 -> 10/10 after the intended confidence and control arc was defined.
- AI-slop risk: 10/10 because v0 adds no custom visual surface.
- Design-system alignment: 10/10 because it reuses Codex's native picker and task plan.
- Responsive and accessibility: 9/10 -> 10/10 after plain-text meaning and typed fallback were required.
- Unresolved design decisions: none.

## Engineering review result

Verdict: accepted for supervised v0; no unresolved activation blocker in the graph contract.

- Executor atomicity: split release stages were replaced by compound `/ship` and `/land-and-deploy` nodes with full pre-invocation authority envelopes and preserved executor-local safety stops.
- Review safety: every opportunity, CEO, design, and engineering gate records `accepted`, `revision_required`, or `fatal`; only accepted dispositions advance.
- Branch determinism: every non-fork branching node has a closed exactly-one outcome table, and representative traces are executable structural fixtures.
- Evidence lifetime: slice receipts bind slice ID, approved plan digest, and delivered commit; final candidate verification alone binds the assembled frozen revision.
- Terminal truth: every receipt edge explicitly sets delivery status, while review effective status may only downgrade a confirmed hard-invariant breach to failed.
- Learning safety: v0 is proposal-only; pre-unlock future auto-promotion is limited to presentation and diagnostics. Semantic graph promotion remains human-approved until executable replay and an independent evaluator exist.
- Deliberation safety: one generic profile-driven child protocol returns only to its exact caller; Luna/max peers challenge one another within two rounds, while the controller and hard guards retain authority.
- Cleanup safety: one manifest-bound finalizer covers completed, blocked, and failed runs; it preserves uncertain or valuable state, forbids broad targets, and requires exact explicit confirmation before destructive cleanup.
- Verification: the standard-library graph validator, negative self-tests, annotation replay, two-profile deliberation replay, skill validation, and independent semantic forward test are required before activation.

Deferred target capabilities are not active-v0 blockers: a durable workflow runtime, Buzz/Hermes wiring, stoppable fine-grained release adapters, historical semantic replay, and semantic auto-promotion.
