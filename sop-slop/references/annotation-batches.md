# Annotation Batches

Read this reference when a user appends several annotations, review comments, screenshots, or observed issues to one task.

Use the annotation ledger format in [output-patterns.md](output-patterns.md) for the compact user-facing list.

## Mental model

Annotations are evidence. Problems are units of work.

One annotation may contain several observations, and several annotations may describe the same underlying problem. Never equate annotation count with task count.

```text
source annotations -> atomic observations -> problem clusters -> durable tasks -> child SOP SLOP runs
                                      \-> non-actionable dispositions
```

The annotation batch is one parent review mission. Each accepted problem is one durable canonical task and one sequential child run through the smallest valid SOP SLOP route. Keep all child runs in the parent Codex task unless a cluster is a true side quest outside the batch's focus boundary.

## Build the problem ledger

Before editing:

1. Assign stable source IDs such as `A01`, `A02`, and preserve the original annotation text or link.
2. Split compound annotations into atomic observation IDs such as `A03.1` and `A03.2` without changing their meaning.
3. For each observation, record the affected surface, observed behavior, desired outcome if clear, user impact, evidence or reproduction status, and confidence. Use `unknown` instead of guessing.
4. Cluster observations by shared underlying problem and desired outcome. Do not cluster only because they are nearby in the UI or suggest the same implementation.
5. Map every observation to exactly one primary problem or one explicit non-actionable disposition. A problem may cite many observations.
6. Quantify the batch: source annotations, atomic observations, underlying problems, supporting duplicates, affected surfaces or roles, impact, confidence, and reproduction status.
7. Order accepted problems by dependency first, then user impact and safe delivery sequence.

Each problem record must include:

- stable problem ID and concise problem statement
- source annotation and observation IDs
- actual versus desired behavior
- user impact, affected scope, confidence, and reproduction evidence
- whether root cause is observed, hypothesized, or verified
- dependency and ordering constraints
- clarification state and any decision receipts
- canonical general-task-list ID and URI
- smallest valid lane, tier, completion target, and verification proof
- status: `ready`, `in_progress`, `completed`, `blocked`, or `failed`
- linked child run and evidence references once execution starts

Mark duplicates as supporting evidence, never as completed tasks. Mark genuinely informational comments with an explicit non-actionable reason.

## Materialize durable tasks

After the ledger is clear and before implementation:

1. Resolve the workspace's canonical general task list from repository instructions and existing configuration.
2. Search it for an equivalent open or completed task using the problem identity and source references.
3. Reuse the canonical task when equivalent; otherwise create exactly one task for the accepted problem.
4. Use an idempotency key derived from the batch and problem IDs so retries cannot duplicate tasks.
5. Store the task system, canonical task ID, URI, and creation-or-reuse receipt in the problem ledger.
6. Synchronize `ready`, `in_progress`, `completed`, `blocked`, or `failed` after controller-validated graph evidence. Map these to the task system's native statuses without changing their meaning.

Do not create one task per supporting annotation, mirror the same work into a second tracker, or mark a durable task complete from an executor's prose claim. If the canonical task list or bounded write authority is unavailable, block at the task bridge and name the missing configuration or authority.

## Clarify only material intent

Resolve facts from the app, repository, canonical documents, and existing behavior before asking the user.

An annotation is clear when the affected behavior, desired outcome, focus boundary, and proof of success can be stated without choosing a material product or domain interpretation for the user. Do not ask about reversible implementation details.

When material intent remains unclear:

1. Select the highest-dependency ambiguous problem.
2. Load `/grill-me` and ask one focused Codex picker question with a recommendation.
3. Record the answer as decision evidence and update only the dependent problem records.
4. Repeat only while a material ambiguity blocks execution.

Continue clear independent problems while another problem is ambiguous. When no ready problem has precedence, route one ambiguous problem to `clarify_annotation_problem`. If its decision remains unanswered, keep the parent there; do not silently infer an answer.

## Execute and close

For each ready problem:

1. Bind a child mission anchor from the problem record.
2. Pass only that problem record and its canonical references into the child run. Do not feed the full annotation batch back into intake.
3. Select the earliest missing stage and skip unnecessary gates with evidence.
4. Run through the ordinary SOP SLOP graph to the problem's requested completion target.
5. Validate the child run receipt, then update the parent ledger, canonical durable task, and visible checklist.
6. Select the next ready problem without asking `continue?`.

Only one problem may own active writes at a time. Read-only exploration may be delegated in parallel when inputs are frozen.

The parent batch is complete only when coverage is 100 percent and every accepted problem has a validated completed receipt at its requested level. If no ready problem remains and any accepted problem is blocked or failed, close the parent with that effective status and preserve the per-problem evidence.
