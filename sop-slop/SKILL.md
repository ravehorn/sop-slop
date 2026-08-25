---
name: sop-slop
description: Carry substantial product or domain changes from alignment through verified production while keeping the primary mission focused, turning annotation batches into deduplicated problem queues, optionally running bounded peer deliberation for unresolved material judgment, forking side quests into separate Codex tasks, and running only the necessary product, engineering, design, QA, ship, and deploy gates. Also use for bounded product reviews or strategy decisions when explicitly requested. Do not use for isolated bugs or small, already-clear code changes.
---

# SOP SLOP

Compose Matt Pocock's alignment and implementation skills with gstack's product, engineering, design, QA, and release skills. Keep both upstream skill sets unchanged and updateable.

## Core rule

Bind one primary mission and completion target at intake. Run the earliest missing stage, not every stage. Auto-advance after a stage is evidenced and no material decision remains. A nested skill's final response is stage evidence, not permission for this controller to stop. Stop only at a real material decision, missing authority, failed verification, or an upstream safety stop.

This is an in-task orchestrator, not a background workflow engine. Advance within the active Codex task and resume later from canonical artifacts, the task plan, git state, and verification evidence.

Repository instructions and canonical artifacts override this generic workflow. Never create a second source of product or task truth just because an upstream skill defaults to an issue tracker.

## Graph contract

[references/workflow-graph.json](references/workflow-graph.json) is the exact active topology: node IDs, edges, reusable call/return templates, closed outcome tables, named guards, evidence types, completion predicates, authority boundaries, retry budgets, trace scenarios, and terminal states. [references/artifact-and-gate-map.md](references/artifact-and-gate-map.md) explains their product meaning and the target architecture without redefining exact edges.

Treat nodes as outcome stages and skills, people, agents, or deterministic tools as executors. One logical controller owns transitions. Executors return evidence; they never advance the graph by claiming they are done.

Graph v0 is supervised. Show the selected route, material decisions, blockers, back-edges, and final receipts. Keep routine machine transitions compact. An explicit request to use SOP SLOP for implementation through production pre-authorizes the repository's routine non-destructive commit, push, PR, merge, deploy, production-verification, and documented bounded-recovery path. Mere review, planning, or ambiguous product discussion does not grant release authority. Repository rules and the safety exclusions below still override that envelope.

Before activating a graph edit, run:

```bash
python3 scripts/validate_workflow_graph.py --self-test
```

## Start

1. Inspect the repository, its instructions, canonical product documents, current plan or spec, task tracker, and relevant code before asking avoidable questions.
2. Read [references/modes-and-tiering.md](references/modes-and-tiering.md) and classify the lane and tier.
3. Read [references/artifact-and-gate-map.md](references/artifact-and-gate-map.md) for stage meaning, then derive the earliest incomplete node from [references/workflow-graph.json](references/workflow-graph.json).
4. Create or update the task plan as a human-readable projection of that route. Keep at most one stage in progress.
5. Execute the first incomplete stage immediately unless its guard is unknown or it requires a material human choice.

Do not create a separate workflow-state file. Resume from the conversation, task plan, canonical artifacts, git state, and verification evidence.

## Mission anchor and side quests

At intake, put a compact mission anchor at the top of the task plan and route card:

- primary requested outcome and observable proof
- explicit non-goals and focus boundary
- requested completion target
- current graph node
- release-authority source and safety exclusions

Preserve this anchor through context compaction, retries, and later user messages. Before acting on a new request inside an active run, classify it as exactly one of:

1. `continuation_or_dependency`: required to complete or safely unblock the primary mission; keep it in the current run.
2. `explicit_replacement`: the user clearly replaces or changes the primary mission; update the run or start a successor run with invalidation evidence.
3. `side_quest`: independently useful but not required for the primary mission; fork it and keep the current node active.

When the user or repository instructions authorize automatic linked-task creation, create a separate Codex task for detected side quests while SOP SLOP is active. Otherwise retain a ready-to-send side-quest prompt and continue the parent run. For a side quest:

1. Do not change the parent route, completion target, or current node.
2. Use Codex `list_projects` and `create_thread`. Use a worktree for same-repository write work; use a local/projectless task for non-repository work.
3. Give the new task the bounded side-quest outcome, relevant canonical references, allowed authority, expected evidence, and stop condition. Do not pass the parent's broader release authority by default.
4. Record the task link in the parent run evidence, tell the user briefly, and immediately continue the primary mission. Do not wait unless the side quest becomes a proven dependency.
5. If task creation is unavailable, retain a ready-to-send side-quest prompt and continue the primary mission; never pivot the parent run.

A question or defect is not a side quest when it blocks the active completion predicate. A new idea is not a mission replacement unless the user clearly says it replaces the original outcome.

## Annotation batch intake

When the user appends multiple UI, browser, document, or code annotations, read [references/annotation-batches.md](references/annotation-batches.md) before selecting the ordinary entry stage.

Treat the batch as evidence for one parent review mission, not as one task per comment. First create an `annotation_problem_ledger` that atomizes compound comments, clusters observations by underlying problem and desired outcome, quantifies each cluster without inventing certainty, and maps every source annotation to a disposition. Supporting or duplicate annotations strengthen one problem; they do not create duplicate work.

Materialize exactly one durable task for every accepted problem in the workspace's canonical general task list. Reuse an equivalent existing task instead of duplicating it, retain the canonical task ID in the ledger, and synchronize its status from validated child-run evidence. If no canonical task list or task-write authority exists, block at the task bridge rather than keeping completion only in chat or inventing a second tracker.

Show the grouped problem list before implementation. Start clear, independent problems without asking for confirmation even when another independent problem still needs clarification. When no ready problem has precedence, inspect the product and repository first, then use a bounded `/grill-me` decision tree and the Codex picker for one highest-dependency question at a time. Ambiguity blocks only the affected problem unless it is a dependency of the whole batch.

Execute one ready problem at a time as a linked child SOP SLOP run using its own mission anchor, smallest valid lane and tier, requested completion, and run receipt. Pass only that ledger problem into the child; do not re-trigger batch intake recursively. Keep the parent task plan as the visible projection of the durable task list. Tick a problem and its canonical task only after validating the child receipt. Do not close the parent batch until every annotation is covered and every accepted problem is completed, blocked, or failed with evidence.

## Alignment lock and question budget

The alignment stages may ask the highest-dependency unresolved product or domain question. Once the user confirms shared understanding, record an `alignment_lock` covering the accepted outcome, behavior, scope, non-goals, and authority boundaries.

After the alignment lock:

- auto-decide reversible technical, dependency, test-layer, implementation, formatting, version-tier, and routine release-mechanics choices from repository evidence and the strongest recommendation
- log the choice and rationale as decision evidence, then continue without ending the turn
- ask the user only when the answer changes locked user-facing behavior, product/domain/economic scope, tenant/data/security authority, destructive or hard-to-reverse state, meaningful external spend/communication, or the production target
- every question must state which completion predicate it blocks; if none, do not ask it
- never ask `continue?`, `use the recommended approach?`, `which version?`, `ship now?`, or `merge and deploy?` when the mission anchor already answers it

An upstream skill's ordinary preference for asking does not override this controller policy. Preserve its true one-way and safety stops.

## Default build-to-production contract

For `product-change` or `approved-build` work where the user explicitly asks SOP SLOP to implement through production, default `requested_completion` to `production_verified`. Respect a lower target when the user asks for review-, spec-, candidate-, PR-, or staging-only work, when release authority is absent, or when the repository has no deployable production path.

The invocation supplies the routine release authority listed in the Core rule for the selected repository and its existing delivery path. Bind that authority at intake so `prepare_release` advances directly when preflight is green. Do not ask for it again at `/ship` or `/land-and-deploy`.

The controller chooses the semantic version from the verified diff and repository conventions. Version queue conflicts, unexpected manual drift, destructive migrations, missing credentials, merge conflicts, failed required checks, and unhealthy deployments remain real blockers.

Do not close an implementation run at a local candidate, commit, PR, merge, or merely READY deployment when the target is `production_verified`. Wait for CI and provider state, perform production verification, record the run receipt and automatic run review, then close.

## Route by work type

### Company strategy and non-code decisions

Use `/grill-me` for company strategy, positioning, packaging, non-product pricing, hiring, fundraising, partnerships, or another decision whose durable home is not the codebase.

Use `/office-hours` after the grill only when the decision is fundamentally about a customer problem, demand, wedge, or product opportunity. Otherwise produce the decision artifact the current workspace treats as canonical and stop.

Do not run `/to-spec`, engineering or design reviews, implementation, QA, or release stages unless the resulting decision actually changes product behavior.

Pricing is a routing fork:

- Company packaging, willingness-to-pay, or go-to-market pricing stays in this lane.
- Product pricing logic, billing behavior, costing, permissions, tax handling, or pricing UX is a product/domain change and uses the full product lane.

Browse current primary sources when market, competitor, legal, financial, or platform facts affect the decision.

### Substantial product or domain change

Use this sequence, skipping a conditional stage only with a concrete reason:

1. `/wayfinder` only when the effort cannot fit in one agent session or the route is still foggy.
2. `/grill-with-docs` when terminology, domain boundaries, workflow behavior, or hard-to-reverse decisions are unresolved. Use `/grill-me` instead only when no repository documentation should change.
3. `/office-hours` when the problem, demand, wedge, or solution premise still needs challenge.
4. `/plan-ceo-review` for substantial user-facing, economic, or scope decisions.
5. `/to-spec` to synthesize the settled conversation; do not restart the interview.
6. `/plan-design-review` when a person sees or interacts with the change.
7. `/plan-eng-review` for architecture, data flow, failure modes, security, tests, and rollout. This is required for T2/T3 build work.
8. `/to-tickets` only when multiple vertical slices are needed and the configured tracker is canonical. Otherwise update the repository's existing task SSOT.
9. `/implement` for one approved vertical slice at a time. It uses `/tdd` at agreed seams and Matt's `/code-review` before committing. Bind the slice receipt to slice ID, approved plan digest, and delivered commit; do not invalidate it merely because a later slice moves repository HEAD.
10. gstack `/review` for the independent pre-landing production-risk pass.
11. gstack `/qa` when there is a runnable UI or service flow. For non-browser work, run the repository's strongest equivalent runtime verification instead.
12. gstack `/ship` as one compound executor that may verify, commit, push, and open the PR. Start it only when the authority envelope covers every action it may perform.
13. gstack `/land-and-deploy` as one compound executor that may merge, deploy, verify production, and perform its bounded recovery behavior. Start it only when the full action and recovery envelope is authorized and supported.

Design precedes engineering because user-visible behavior must be settled before architecture is locked. If design review changes product behavior, update the spec before engineering review.

### Review only

Start at the earliest missing lens:

- unclear premise or demand: `/office-hours`
- product value or scope: `/plan-ceo-review`
- user experience: `/plan-design-review`
- architecture, tests, or rollout: `/plan-eng-review`
- implemented diff: `/review`
- runnable behavior: `/qa-only` for report-only work or `/qa` when fixes were requested

Return the reviewed canonical artifact or findings and stop unless the user also asked to build or ship.

### Existing approved plan or spec

Do not re-grill settled decisions. Read the artifact and run only missing reviews. If CEO, design, and engineering review are all still missing and no Matt-spec stage must sit between them, prefer gstack `/autoplan` over manually rebuilding its pipeline.

## Source-of-truth adapter

Matt's domain and tracker conventions are defaults, not authority. Before `/grill-with-docs`, `/to-spec`, or `/to-tickets`:

1. Identify the repository's canonical product and task artifacts.
2. Use the existing domain glossary and ADR system. Create `CONTEXT.md` or `docs/adr/` only when the repository has no canonical equivalent.
3. Use Matt's synthesis and vertical-slice method, but preserve the repository's spec format and scope discipline.
4. Write to the canonical repository artifact first when repository rules require it.
5. Publish or mirror to an external tracker only when it is configured, non-duplicative, and already authorized.
6. Never run `/setup-matt-pocock-skills` merely to introduce a second tracker into a mature repository.

## Automatic stage handoff

For every selected stage:

1. Load and follow the named skill rather than paraphrasing it from memory.
2. Record its observable output: artifact path, accepted decision, test result, review result, PR, deployment, or blocker.
3. Mark the stage complete only when that evidence exists.
4. Treat the nested skill's final message as an executor return. Restore the mission anchor, validate the evidence, select the legal edge, and continue the outer run.
5. If the next stage is safe and has no open material decision, start it without asking "continue?".
6. If a finding invalidates an earlier stage, route back to the owning stage, update the artifact, and re-run affected downstream checks.

For every gating review, record exactly one disposition: `accepted`, `revision_required`, or `fatal`. A recorded review is not permission to advance. Only `accepted` may take an advance or requested-completion edge; `revision_required` takes its bounded back-edge; `fatal` closes with preserved evidence.

At every ordinary branching node, classify exactly one value from its closed outcome table before evaluating the mapped guard. Fork nodes are the only intentional multi-edge dispatch. If no outcome or more than one outcome applies, block at the node as an invalid or unknown guard state.

If a guard is unknown or cannot be evaluated, fail closed. State the missing fact, propose the smallest safe way to obtain or resolve it, and use an explicit decision node when the answer is material. Never let another outgoing edge win merely because one guard was unevaluable.

Common back-edges:

- new domain ambiguity -> `/grill-with-docs`
- weak demand or scope -> `/office-hours` or `/plan-ceo-review`
- changed behavior -> `/to-spec`, then design and engineering review again as affected
- review or QA defect -> `/implement`, then repeat the failed verification and relevant review
- failed ship or deploy check -> fix the root cause and re-run that gate

## Subagent delegation adapter

Delegation is an execution option inside an eligible outcome node, not a second graph. The controller always owns guards and transitions, and it must consolidate and validate returned evidence before evaluating node completion.

Use only these initial roles from `workflow-graph.json`:

- `explorer`: read-only code, architecture, canonical-document, or primary-source discovery
- `implementation_worker`: one approved slice or bounded repair, serialized in the active workspace or isolated with disjoint ownership
- `reviewer`: independent product, engineering, code, security-lens, or run review; never fixes the reviewed subject
- `qa_tester`: browser, runtime, and repository-check execution against a frozen candidate; writes only test artifacts

Delegate only when the task is bounded and independent enough to save time or improve independence. Before every spawn, select a concrete available model and reasoning effort using ambiguity, risk, cost, and parallelizability. Record both; role defaults are guidance, not a substitute for selection.

Every delegation envelope must state: run and node identity, bounded ownership, allowed tools and permissions, canonical input references, expected output, verification criteria, stop condition, and isolation. Each spawn is a fresh agent thread. Never assume a role has durable private memory; provide continuity through canonical graph artifacts and reviewed shared memory.

Parallelize read, review, test, and QA work against frozen inputs. Active v0 serializes `deliver_slice` and `repair_candidate`; isolated workspaces may protect those tasks but do not create implicit parallel edges. A later version may add an explicit writer fork for leased, disjoint slices. On return, retain a `delegation_receipt`, verify its evidence, and either accept it into the current node's evidence, reject it, or dispatch a bounded repair. A delegation receipt alone never completes the node.

Persistent Codex role files may later project this four-role catalog after the installed Codex schema is verified. They are configuration convenience only, not workflow authority or agent memory.

## Bounded deliberation adapter

Read [references/deliberation-protocol.md](references/deliberation-protocol.md) when an eligible node contains material competing judgment that canonical evidence or an established pattern does not settle. Routine and deterministic decisions skip it.

Invoke the single `bounded_peer_deliberation` call/return template with one allowlisted, versioned profile. Design Council is the `design` profile; product/domain, specification, engineering, review adjudication, QA triage, and learning/retro use the same protocol with different lenses. Freeze a typed request, preserve its stable mission-anchor digest, suspend the caller, and bind every result to the invoking run, node, frozen-input digest, profile version, content-digested accepted proposal, and exact return node.

Every deliberation specialist and proposal owner is a fresh `reviewer` execution using `gpt-5.6-luna` at `max` reasoning, recorded in its delegation envelope and receipt. Specialists must first observe independently, then receive peers' lossless typed statements, answer named peers, expose the required contribution fields, revise within the two-round budget, produce one joint proposal, and consent without majority voting. The controller alone validates the return and chooses the legal parent transition. Hard safety, truth, tenant/security, release authority, verification, and failed ship/deploy guards cannot be debated away; accepted work still has one implementation writer.

## Codex picker adapter

This adapter controls how all nested skills present material choices in Codex. It overrides their host-specific question presentation, not their decision logic.

When `request_user_input` is available:

- Call it for one decision at a time.
- Provide 2-3 mutually exclusive choices.
- Put the recommended choice first and suffix its label with `(Recommended)`.
- Keep labels short and explain the tradeoff in one sentence.
- Let Codex provide the free-form `Other` option.
- If more than three real choices exist, use `More choices` as the final option and show the next set only if selected.

Preserve Matt's design-tree logic, but ask only the highest-dependency unresolved decision in each picker. Find environmental facts yourself before asking.

For every answered material choice, retain decision evidence containing the question, options, recommendation, actual selection, actor, scope, and time. A changed choice invalidates dependent evidence or starts a linked successor run. An empty answer never becomes a decision receipt.

If the picker returns an empty or missing answer map, treat it as unanswered. Ask once for the same choice as typed input and stop. Do not retry the picker, infer a default, or advance the workflow.

If `request_user_input` is unavailable or errors after a question may have been shown, state that the native picker is unavailable, render the same choices once as typed input, and stop. Never automate the Codex UI to fake a picker.

## Gates and authority

Do not ask for permission at every reversible internal transition. An explicit request to use SOP SLOP for implementation through production authorizes the routine non-destructive release path in the selected repository; do not ask for push, PR, merge, deploy, or production verification again when the authority envelope records that request. Do stop for:

- a material product, domain, strategy, pricing, or scope decision
- acceptance of test seams when the user has not already approved them
- external tracker publication not already authorized
- destructive or hard-to-reverse data or schema action
- push, PR, merge, deployment, or production action when the run was not invoked for implementation-to-production or current instructions explicitly withhold that authority
- failed required verification

An empty picker answer, silence, or an ambiguous reply never satisfies a gate.

Treat `/ship` and `/land-and-deploy` as atomic at their documented executor boundaries. Before either starts, require authority for the full set of consequential actions it may perform; a prompt asking a compound executor to stop midway is not an authority boundary.

Atomic does not mean unstoppable. Preserve every documented upstream safety stop. If a compound executor reaches first-run setup, failed readiness, merge conflict, permission failure, unhealthy deployment, or another skill-defined stop, it returns `blocked` or `failed` evidence to its outer node. The authority envelope never bypasses those checks.

## Run resource cleanup

After the immutable delivery receipt and before the automatic run review, execute `reconcile_run_resources` for completed, blocked, and failed runs. Maintain one `run_resource_manifest` for worktrees, temporary workspaces, processes, ports, environments, caches, leases, and other resources created or explicitly claimed by the current run. The cleanup receipt must bind the current run, graph version, and exact manifest digest.

Automatically release only actions that do not delete data, such as stopping a run-owned process, releasing its port or lease, and pruning stale worktree metadata whose live files are already absent. Never target `/`, a home or workspace root, unresolved variables, command substitutions, globs, or a shared cache. Preserve anything dirty, untracked, unpushed, unmerged, shared, canonical, actively leased, ownership-unknown, or needed to resume or debug the run.

Removing a worktree, environment, cache, or files is destructive cleanup even when it appears regenerable. Inspect the exact target, then present one recoverability card with target list, count, size, location, reason, recovery path, what would be lost, and alternatives. Continue only from a non-empty `yes` or `do it` decision receipt bound to that manifest digest and exact target list. A worktree additionally requires proof that it belongs to this run, is not the primary workspace, is clean with no untracked files, has a pushed commit, is merged or explicitly approved for disposal, and has no active run lease.

Cleanup is reconciled when every manifest resource is either released and verified or preserved with a concrete reason it remains needed. A declined exact deletion closes the cleanup request as blocked without changing the immutable delivery status; an unanswered picker remains unanswered. Cleanup retries are bounded by `cleanup_attempts`.

## Run review and learning

Every completed, blocked, or failed workflow run must produce an immutable delivery receipt, a cleanup receipt, and then an automatic run review before closing. Review in this order:

1. hard safety and truth constraints
2. requested outcome correctness
3. human corrections and failed loops
4. autonomy, time, and cost

Use [references/behavioral-baseline.md](references/behavioral-baseline.md) as the public baseline for focus, autonomy, and closure regressions. Compare at least the next five runs against its success criteria before proposing another semantic policy change.

The edge entering `record_run_receipt` must explicitly set delivery status to `completed`, `blocked`, or `failed`; never infer it from a node label or narrative. The subsequent reviewer records an effective status without mutating that delivery receipt.

Classify the result as `no_issue`, `executor_issue`, `graph_issue`, or `policy_issue`. Emit an improvement proposal only for a repeatable root cause supported by linked evidence. A proposal must name its graph base version, risk class, expected effect, evidence, and validation plan. Preserve the immutable delivery status separately from the review receipt's effective status. A successful review that proves a hard-invariant breach downgrades effective status to `failed`; a reviewer error preserves delivery status, records the error, and emits no proposal.

Graph v0 never edits or promotes itself. A proposal enters a linked successor run. Before executable historical scenario replay and an independent semantic evaluator exist, future auto-promotion is limited to presentation-only and diagnostic-only changes within a human-approved ceiling. Nodes, edges, guards, evidence requirements, and other semantic changes remain human-approved. Semantic auto-promotion may become eligible only after replay, independent evaluation, and a separately approved semantic ceiling. No promotion may expand authority, weaken hard invariants, remove required evidence, change production or data boundaries, or enlarge its own ceiling.

### Run-ledger diagnostic

Before claiming formal graph closure for a T2 or T3 run, materialize a temporary `run` document from the typed receipts already held in the task and run:

```bash
python3 scripts/validate_run_replay.py <document.json> --scenario run --require-closure
```

The temporary document is diagnostic input, not a new source of workflow truth. Exit `2` means delivery may still be factually complete, but graph closure is unproven; report the delivery result and missing evidence or transitions separately. This check never grants authority or changes the active graph.

Every observed transition names its exact `edge_id`; transitions from a closed-outcome node also record the selected `outcome`. A source/target pair alone is insufficient because multiple guarded edges may share the same nodes. A `resolve_candidate` transition additionally names the exact `join_id`, whose receipt binds the frozen subject and exact branch receipt IDs.

Use [references/forward-test-fixture-0.6.0.json](references/forward-test-fixture-0.6.0.json) as the public synthetic annotation-batch and cleanup forward-test fixture for this diagnostic.

## Completion

Report the graph version, lane, primary mission, stages run and skipped, linked side-quest tasks, evidence for the requested completion target, cleanup disposition, run-review result, and the exact next gate if blocked. Never imply that downstream stages ran merely because they were listed. For an implementation run targeting `production_verified`, a local candidate, commit, PR, merge, or ready deployment is progress, not completion.
