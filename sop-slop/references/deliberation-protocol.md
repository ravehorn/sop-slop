# Bounded Deliberation Protocol

Use this reference only when an eligible SOP SLOP node contains material competing judgment that repository evidence or an established pattern does not already resolve. Routine and deterministic work skips deliberation.

The active contract is the `bounded_peer_deliberation` call/return template in `workflow-graph.json`. This document explains how to operate it; it does not redefine topology.

## Mental model

Deliberation is a temporary child call, not a new mission or a manager collecting three reports.

```text
eligible caller -- frozen request --> shared peer protocol -- validated receipt --> exact caller
       ^                                                                            |
       +---------------- controller retains mission and transition authority --------+
```

The invoking node pauses. The controller freezes one typed request, dispatches three fresh reviewer executions, routes their statements and named questions, validates the result, and returns to the exact invoking run and node. The child cannot choose a downstream parent edge.

## Profiles

Profiles are versioned data over one shared protocol. They do not create duplicated subgraphs.

| Profile | Lenses | Eligible callers |
| --- | --- | --- |
| `design` | interaction/user flow; visual hierarchy/design system; accessibility/edge cases | `review_experience` |
| `product_domain` | customer/operator reality; product/economic scope; domain/data truth | product alignment and product-direction reviews |
| `specification` | behavior; scope/non-goals; acceptance/contradictions | `specify_product` |
| `engineering` | simplicity/maintainability; reliability/security; operations/cost | `review_engineering` |
| `review_adjudication` | correctness; security/risk; maintainability | candidate review and resolution |
| `qa_triage` | user impact; reproduction/evidence; probable ownership/root cause | candidate exercise and resolution |
| `learning_retro` | outcome correctness; process failure; autonomy/time/cost | `review_run` |

“Design Council” is the `design` profile, not a separate graph.

## Invocation guard

Invoke only when all are true:

1. the current node and selected profile are an allowlisted pair
2. the decision contains material competing judgment
3. current canonical evidence or an established pattern does not settle it
4. peer challenge is likely to change or validate the decision

Skip when the answer is routine, deterministic, already specified, or better resolved by direct inspection. Factual uncertainty routes to inspection, a prototype, a check, or a reversible experiment rather than more debate.

## Frozen request

Create one `deliberation_request` containing:

- invoking run, stable mission-anchor digest, node, exact question, and reason
- profile ID/version, three named participants, and profile lenses
- canonical input references plus the SHA-256 digest of that frozen reference list
- `gpt-5.6-luna` with reasoning effort `max`
- acceptance criteria, non-debatable hard invariants, round and contribution budgets
- authority envelope, expected evidence, exact return node, and return contract

Every specialist and proposal-owner envelope and receipt records Luna/max. Each execution starts as a fresh thread with bounded ownership, read-only or test-only permissions, expected output, verification criteria, and a stop condition. Canonical artifacts—not private agent memory—carry continuity.

## Shared protocol

1. **Independent observation.** Each specialist sees the same frozen request and records problems, constraints, evidence, and named peer questions before seeing peer positions. No final proposal exists yet.
2. **Lossless broadcast.** The controller broadcasts every typed peer contribution to every participant.
3. **Named discussion.** Follow-up turns route non-empty named questions and responses. Every contribution exposes `CLAIM`, `WHY`, `EVIDENCE`, `QUESTION_FOR`, `OBJECTION`, and `CHANGE_MY_MIND_IF`.
4. **Bounded challenge.** Specialists address objections and state what changed their position or why they retained it. The maximum is two rounds and one or two contributions per specialist per round.
5. **Joint proposal.** The controller selects the dominant-lens reviewer as proposal owner. That reviewer synthesizes the discussion; the controller validates rather than inventing a preferred design.
6. **Consent.** Every participant returns exactly `accept`, `accept_with_concern`, or `object`. An objection must identify a violated requirement or missing evidence, not taste. There is no majority vote, and minority concerns remain in the receipt.
7. **Controller validation.** The controller selects one closed disposition and validates binding, evidence, acceptance criteria, and hard invariants.

## Closed dispositions

- `accepted`: bind the accepted proposal and return to the exact caller
- `revision_required`: run one bounded peer revision while budget remains
- `evidence_or_experiment_required`: inspect, prototype, test, or run the cheapest reversible experiment
- `material_human_decision_required`: ask Max one native Codex picker question after factual evidence is exhausted
- `blocked`: preserve dissent and the smallest unblocker when budget, evidence, or authority is exhausted
- `fatal`: preserve the non-recoverable hard-invariant, safety, truth, or authority conflict

## Return and invalidation

The run contains exactly one run-bound route card. The `deliberation_return_receipt` binds its stable mission-anchor digest, invoking node, input digest, profile version, content-digested accepted proposal, dissent, invariant check, invalidated artifacts, and exact return node. The proposal digest covers the proposal, acceptance mapping, invariant result, evidence references, and retained concerns; every cited reference must exist.

If the result changes upstream behavior or assumptions, mark affected artifacts stale and let the invoking node route through their normal owning stages. Deliberation cannot waive hard safety, data truth, tenant/security, release authority, required verification, or a failed ship/deploy gate. Evidence/experiment resolution and the material-human picker are each limited to one cycle, require a request-bound receipt, and must be cited by the accepted proposal. Reviewer envelopes and accepted receipts use the exact frozen input list and the closed read-only tool/permission contract.

After acceptance, implementation remains single-writer. Parallel review and QA may stay read-only against frozen inputs.

## Executable proof

Run both fixtures:

```bash
python3 scripts/validate_run_replay.py --scenario forward_test --require-closure
python3 scripts/validate_run_replay.py references/deliberation-forward-test-fixture-0.5.0.json --scenario forward_test --require-closure
```

The deliberation fixture proves reuse from design and engineering callers, Luna/max enforcement, peer influence, objection-driven revision, exact return binding, bounded rounds, and zero writers.
