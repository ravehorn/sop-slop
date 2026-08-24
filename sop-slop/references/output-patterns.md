# Output Patterns

## Route card

At the start, state only:

1. run ID, lane, and tier
2. canonical artifact or source of truth
3. selected stages and deliberate skips
4. current stage
5. next material gate

Do not wait for approval of the route card unless the classification itself changes product scope, external writes, or authority.

## Stage handoff

For each completed stage, retain:

1. stage name
2. artifact or evidence path
3. decisions settled
4. review disposition when the stage is a gate
5. unresolved blockers
6. next stage

Use the task plan for transient orchestration. Put durable product truth only in the repository's canonical artifacts.

## Annotation problem ledger

Before implementation, show:

1. batch totals: source annotations, atomic observations, underlying problems, supporting duplicates, clear problems, and problems needing clarification
2. one row per underlying problem: problem ID, concise actual-versus-desired behavior, source annotation IDs, impact, confidence or reproduction state, canonical task link, route, and status
3. one coverage line proving every source annotation is mapped to a problem or explicit non-actionable disposition
4. the selected next problem or one material clarification question

Do not print every repeated annotation in full when stable IDs and links preserve traceability.

## Decision artifact

For strategy-decision work, produce the workspace's canonical decision format with:

1. decision
2. why now
3. evidence and assumptions
4. alternatives rejected
5. risks
6. next action and owner
7. review date or invalidation signal when relevant

## Specification output

Use Matt's `/to-spec` structure, adapted to the repository's source of truth:

1. problem statement
2. solution
3. numbered user stories or observable behaviors
4. implementation decisions
5. agreed test seams and verification
6. out of scope
7. further notes

## Builder handoff

Before implementation, identify:

1. one bounded vertical slice and its receipt identity: slice ID, approved plan digest, delivered commit
2. canonical spec
3. accepted product, design, and engineering review evidence
4. agreed test seams
5. explicit out-of-scope items
6. required release gates

## Delegation envelope and receipt

Before spawning a specialist, record:

1. run ID, graph version, and node ID
2. role, concrete model, and reasoning effort
3. bounded ownership scope
4. allowed tools, permissions, and isolation mode
5. canonical input references
6. expected output and verification criteria
7. stop condition

On return, retain result and evidence references plus the controller's validation. The controller decides whether the returned evidence satisfies the node's actual completion predicate; the specialist never selects the next edge.

## Deliberation call and return

At invocation, retain:

1. invoking run, stable mission-anchor digest, node, exact question, reason, profile ID/version, and frozen-input-reference digest
2. named roster and lenses, each pinned to `gpt-5.6-luna` at `max`
3. acceptance criteria, hard invariants, authority, two-round budget, expected evidence, and exact return contract

During discussion, retain independent observations, lossless broadcasts, named questions and responses, required contribution fields, objections, and position changes. At return, show the joint proposal, each specialist's consent status, retained dissent, controller validation, invalidated artifacts, and exact caller. Never summarize isolated reports as a council result or use majority vote.

## Completion report

Report:

1. graph version, immutable delivery status, and effective terminal status when they differ
2. requested completion level
3. stages run
4. stages skipped and why
5. strongest verification or release evidence
6. run-review classification and proposal, if any
7. remaining blocker or next gate, if any

Never report a listed stage as completed without evidence that it ran.

## Blocked report

State the exact failed, missing, or unknown guard; the missing fact or authority; who can resolve it; and the smallest safe proposed unblocker. Do not let a sibling edge silently win.

## Revision report

State the failed evidence or `revision_required` disposition, owning stage, bounded back-edge, remaining budget, and which downstream receipts became stale. Preserve stale receipts for audit; do not stale an earlier slice receipt merely because a later slice moved repository HEAD.
