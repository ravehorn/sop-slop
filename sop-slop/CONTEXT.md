# SOP SLOP Workflow Graph

This context defines the language used to design and operate the SOP SLOP workflow graph.

## Language

**Workflow Run**:
One coherent product or strategy outcome carried from intake to an explicit terminal result. A long-running program is coordinated as multiple workflow runs.
_Avoid_: Session, project

**Primary Mission**:
The one requested outcome a workflow run must preserve until the user explicitly replaces it, including its observable completion target and non-goals.
_Avoid_: Latest interesting request

**Mission Anchor**:
The compact route-card record of the primary mission, focus boundary, current node, requested completion, and authority source. It survives compaction, executor returns, retries, and side quests.
_Avoid_: Chat recap

**Side Quest**:
An independently useful request that is not required to unblock the primary mission. It becomes a linked Codex task and never changes the parent route or completion target.
_Avoid_: Implicit scope expansion

**Alignment Lock**:
The recorded point at which accepted outcome, behavior, scope, non-goals, and authority boundaries are settled. After it, reversible technical and release-mechanics choices belong to the controller.
_Avoid_: Permission to ignore safety

**Requested Completion**:
The observable terminal level selected at intake. An explicit implementation-through-production request defaults to verified production unless the user narrows it.
_Avoid_: Whatever the current executor happened to finish

**Outcome Stage**:
A bounded unit of workflow defined by the result and evidence it must produce, independent of the agent, skill, or tool that performs it.
_Avoid_: Skill node, agent node

**Executor**:
A skill, agent, or deterministic tool assigned to perform an outcome stage and return evidence. An executor does not own global graph transitions.
_Avoid_: Controller

**Controller**:
The single logical authority that evaluates guards, advances a workflow run, and dispatches eligible executors. It may use parallel workers without giving them global transition authority.
_Avoid_: Lead agent, swarm leader

**Worker**:
A bounded executor that receives a staged context handoff and returns evidence for one outcome stage or explicit fork branch.
_Avoid_: Peer controller

**Specialist Role**:
A reusable execution profile that defines purpose, access ceiling, default model class, and stop behavior. The graph role persists; each execution is a fresh agent thread.
_Avoid_: Permanent agent personality, private memory

**Delegation Envelope**:
The bounded assignment sent to one fresh specialist execution: node and run identity, ownership scope, concrete model and reasoning effort, allowed tools and permissions, input references, expected output, verification criteria, stop condition, and isolation mode.
_Avoid_: Open-ended prompt

**Delegation Receipt**:
The specialist's typed return record plus the controller's validation. It is supporting evidence only and never completes a graph node or selects an edge by itself.
_Avoid_: Subagent done claim

**Fresh Agent Execution**:
One newly spawned execution with no assumed durable private state. Continuity comes from canonical graph artifacts and reviewed shared memory supplied in the delegation envelope.
_Avoid_: Always-running personal agent

**Guard**:
A named, pure yes-or-no predicate over logical run state that permits or denies an edge. A guard never performs work or asks a question.
_Avoid_: Agent judgment, prompt condition

**Branch Outcome**:
One value from a closed, exactly-one outcome set owned by a branching stage. Each value maps to one guard and one outgoing edge.
_Avoid_: Uncoordinated Boolean flags

**Completion Predicate**:
The declared test that proves an outcome stage finished, using typed evidence bound to the relevant artifact, revision, or external action.
_Avoid_: Done claim, confidence score

**Evidence Receipt**:
A typed, independently inspectable result bound to an exact subject or revision and retained when it becomes stale.
_Avoid_: Status message

**Slice Delivery Receipt**:
A durable local proof bound to one slice ID, approved plan digest, and delivered commit. Later slices do not stale it; final candidate verification proves integration.
_Avoid_: Current-HEAD receipt

**Review Disposition**:
Exactly one gating-review result: `accepted`, `revision_required`, or `fatal`. Recording the review completes the node; the disposition selects the legal edge.
_Avoid_: Review completed means review passed

**Authority Envelope**:
The per-run set of allowed actions, forbidden actions, environments, and operating limits derived from the request and applicable repository rules.
_Avoid_: Blanket permission

**Capability Policy**:
A versioned rule that may promote or demote automatic authority within a pre-approved repository, action, environment, and change-risk scope.
_Avoid_: Universal trust

**Agent Reputation**:
A cross-run reliability signal that may contribute to a capability policy but cannot authorize an action by itself.
_Avoid_: Agent authority

**Explicit Fork**:
A declared fan-out in which multiple independent, safe branches may run concurrently against the same frozen inputs.
_Avoid_: Peer swarm

**Join**:
The synchronization point that evaluates the evidence returned by every required branch of an explicit fork before the workflow can advance.

**Run Receipt**:
The final audit record of a workflow run's decisions, transitions, evidence, authority use, and outcome, intended to support later policy learning.
_Avoid_: Product source of truth

**Run Review**:
The required post-run evaluation of a run receipt against the ordered workflow goals. It classifies the root cause as no issue, executor issue, graph issue, or policy issue.
_Avoid_: Weekly retrospective

**Effective Status**:
The terminal status selected by the run-review receipt. It normally equals the immutable delivery status, but a confirmed hard-invariant breach may downgrade it to failed; a reviewer error may not change it.
_Avoid_: Rewriting the delivery receipt

**Improvement Proposal**:
A versioned candidate change to an executor, graph, or capability policy, linked to repeatable run evidence. It cannot change active behavior until its promotion gate passes.
_Avoid_: Self-edit, learned rule

**Promotion Gate**:
The evidence and authority check that decides whether an improvement proposal may become an active version. Validation does not itself grant promotion authority.
_Avoid_: Automatic merge

**Policy Ceiling**:
The human-approved outer boundary within which a capability policy may promote low-risk changes automatically. It can never expand itself.
_Avoid_: Agent discretion

**Run Ledger**:
The append-only contract for durable run receipts, reviews, and proposal lineage. Buzz may later host or project this contract only after conformance testing.
_Avoid_: Product source of truth, chat history
