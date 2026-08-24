#!/usr/bin/env python3
"""Validate SOP SLOP diagnostic proposals and run-replay documents."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from validate_workflow_graph import DuplicateKeyError, _unique_object, load_graph


ROOT = Path(__file__).resolve().parents[1]
GRAPH_PATH = ROOT / "references" / "workflow-graph.json"
PROPOSAL_PATH = ROOT / "references" / "forward-test-fixture-0.3.1.json"
SCENARIO_KEYS = ("historical_replay", "forward_test", "run")
PROMOTION_STATUSES = {
    "replay_validated_pending_independent_forward_test",
    "forward_test_validated_pending_promotion",
    "promoted",
}


def load_document(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        document = json.load(handle, object_pairs_hook=_unique_object)
    if not isinstance(document, dict):
        raise ValueError("document must be a JSON object")
    return document


def present(value: Any) -> bool:
    return value not in (None, "", [], {})


def validate_proposal(
    graph: dict[str, Any], proposal: dict[str, Any], graph_digest: str, run_ids: set[str]
) -> list[str]:
    errors: list[str] = []
    evidence_types = {item["id"]: item for item in graph["evidence_types"]}
    for field in evidence_types["improvement_proposal"]["required_fields"]:
        if not present(proposal.get(field)):
            errors.append(f"proposal missing {field}")
    if proposal.get("base_graph_version") != graph["graph"]["version"]:
        errors.append("proposal base_graph_version does not match the active graph")
    if proposal.get("base_graph_digest") != graph_digest:
        errors.append("proposal base_graph_digest does not match the active graph")
    if proposal.get("change_class") != "diagnostics_only":
        errors.append("proposal must remain diagnostics_only")
    if proposal.get("root_cause_class") not in graph["policies"]["learning"]["root_cause_classes"]:
        errors.append("proposal root_cause_class is invalid")

    status = proposal.get("promotion_status")
    if status not in PROMOTION_STATUSES:
        errors.append(f"unsupported promotion_status: {status}")
    if status == "promoted":
        promotion = proposal.get("promotion")
        if not isinstance(promotion, dict):
            errors.append("promoted proposal requires a promotion receipt")
        else:
            for field in (
                "authority_ref",
                "forward_test_run_id",
                "promoted_at",
                "activated_files",
                "graph_digest",
            ):
                if not present(promotion.get(field)):
                    errors.append(f"promotion receipt missing {field}")
            if promotion.get("forward_test_run_id") not in run_ids:
                errors.append("promotion receipt forward_test_run_id is not present in this document")
            if promotion.get("graph_digest") != graph_digest:
                errors.append("promotion receipt graph_digest does not match the active graph")
    return errors


def validate_replay(graph: dict[str, Any], replay: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    diagnostics: set[str] = set()
    evidence_types = {item["id"]: item for item in graph["evidence_types"]}
    nodes = {item["id"]: item for item in graph["nodes"]}
    edges = {(item["from"], item["to"]) for item in graph["edges"]}

    if not present(replay.get("run_id")):
        errors.append("replay missing run_id")
    if replay.get("graph_version") != graph["graph"]["version"]:
        errors.append("replay graph_version does not match the active graph")

    selected_stages = replay.get("selected_stages")
    if not isinstance(selected_stages, list) or not selected_stages:
        errors.append("replay selected_stages must be a non-empty list")
        selected_stages = []
    elif len(selected_stages) != len(set(selected_stages)):
        errors.append("replay selected_stages must be unique")
    for stage in selected_stages:
        if stage not in nodes:
            errors.append(f"unknown selected stage: {stage}")

    evidence = replay.get("evidence")
    if not isinstance(evidence, dict):
        errors.append("replay evidence must be an object")
        evidence = {}
    for evidence_id, receipts in evidence.items():
        if evidence_id not in evidence_types:
            errors.append(f"unknown evidence type: {evidence_id}")
            continue
        if not isinstance(receipts, list):
            errors.append(f"evidence {evidence_id} must be a list")
            continue
        required_fields = evidence_types[evidence_id]["required_fields"]
        for index, receipt in enumerate(receipts):
            if not isinstance(receipt, dict):
                errors.append(f"evidence {evidence_id}[{index}] must be an object")
                continue
            for field in required_fields:
                if field not in receipt:
                    errors.append(f"evidence {evidence_id}[{index}] missing {field}")

    for stage in selected_stages:
        node = nodes.get(stage)
        if node is None:
            continue
        for evidence_id in node["completion"]["evidence"]:
            if not evidence.get(evidence_id):
                diagnostics.add(f"missing_evidence:{evidence_id}")

    candidate_stages = {
        "candidate_verification_fork",
        "review_candidate",
        "exercise_candidate",
        "run_required_checks",
        "candidate_evidence_join",
        "resolve_candidate",
    }
    if candidate_stages.intersection(selected_stages) and not evidence.get("fork_manifest"):
        diagnostics.add("candidate_freeze_unproven")

    planned_slices = replay.get("planned_slice_ids", [])
    if not isinstance(planned_slices, list):
        errors.append("planned_slice_ids must be a list")
        planned_slices = []
    elif len(planned_slices) != len(set(planned_slices)):
        errors.append("planned_slice_ids must be unique")
    delivered_slices = {
        receipt.get("slice_id")
        for receipt in evidence.get("slice_delivery_receipt", [])
        if isinstance(receipt, dict)
    }
    for slice_id in planned_slices:
        if slice_id not in delivered_slices:
            diagnostics.add(f"missing_slice_receipt:{slice_id}")

    delegations = replay.get("delegations", [])
    if not isinstance(delegations, list):
        errors.append("delegations must be a list")
        delegations = []
    delegation_receipts = {
        receipt.get("execution_id")
        for receipt in evidence.get("delegation_receipt", [])
        if isinstance(receipt, dict)
    }
    for delegation in delegations:
        if not isinstance(delegation, dict) or not present(delegation.get("execution_id")):
            errors.append("each delegation must name execution_id")
            continue
        if delegation["execution_id"] not in delegation_receipts:
            diagnostics.add(f"missing_delegation_receipt:{delegation['execution_id']}")

    transitions = replay.get("observed_transitions", [])
    if not isinstance(transitions, list):
        errors.append("observed_transitions must be a list")
        transitions = []
    incoming: set[str] = set()
    selected_set = set(selected_stages)
    for transition in transitions:
        if not isinstance(transition, dict):
            errors.append("each observed transition must be an object")
            continue
        source, target = transition.get("from"), transition.get("to")
        pair = (source, target)
        if source not in nodes or target not in nodes:
            errors.append(f"observed transition names an unknown node: {source}->{target}")
            continue
        if source not in selected_set or target not in selected_set:
            errors.append(f"observed transition is outside selected_stages: {source}->{target}")
        if pair not in edges:
            diagnostics.add(f"illegal_transition:{source}->{target}")
        incoming.add(target)
    if graph["graph"]["start"] not in selected_set:
        diagnostics.add(f"missing_stage:{graph['graph']['start']}")
    for stage in selected_stages:
        if stage != graph["graph"]["start"] and stage not in incoming:
            diagnostics.add(f"missing_transition:{stage}")

    terminals = set(graph["graph"]["terminals"])
    terminal_stages = terminals.intersection(selected_set)
    if (
        len(terminal_stages) != 1
        or not evidence.get("run_receipt")
        or not evidence.get("run_review_receipt")
    ):
        diagnostics.add("terminal_unproven")
    for evidence_id in ("run_receipt", "run_review_receipt"):
        if not evidence.get(evidence_id):
            diagnostics.add(f"missing_evidence:{evidence_id}")

    expected = replay.get("expected_diagnostics")
    if expected is not None:
        if not isinstance(expected, list) or not all(isinstance(item, str) for item in expected):
            errors.append("expected_diagnostics must be a list of strings")
        elif len(expected) != len(set(expected)):
            errors.append("expected_diagnostics must be unique")
        elif sorted(expected) != sorted(diagnostics):
            errors.append(
                "replay diagnostics differ from expectation: "
                f"expected={sorted(expected)!r} actual={sorted(diagnostics)!r}"
            )

    return errors, sorted(diagnostics)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("document", nargs="?", type=Path, default=PROPOSAL_PATH)
    parser.add_argument("--graph", type=Path, default=GRAPH_PATH)
    parser.add_argument("--scenario", choices=SCENARIO_KEYS)
    parser.add_argument(
        "--require-closure",
        action="store_true",
        help="exit 2 when the selected replay has unresolved diagnostics",
    )
    args = parser.parse_args()

    try:
        graph = load_graph(args.graph)
        document = load_document(args.document)
    except (OSError, json.JSONDecodeError, DuplicateKeyError, ValueError) as error:
        print(f"INVALID: {error}")
        return 1

    errors: list[str] = []
    if document.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    scenarios = [
        (key, document[key])
        for key in SCENARIO_KEYS
        if key in document and (args.scenario is None or key == args.scenario)
    ]
    if args.scenario and args.scenario not in document:
        errors.append(f"scenario not present: {args.scenario}")
    if not scenarios:
        errors.append("document must contain historical_replay, forward_test, or run")
    for key, replay in scenarios:
        if not isinstance(replay, dict):
            errors.append(f"{key} must be an object")

    graph_digest = hashlib.sha256(args.graph.read_bytes()).hexdigest()
    run_ids = {
        replay.get("run_id")
        for key in SCENARIO_KEYS
        if isinstance((replay := document.get(key)), dict) and present(replay.get("run_id"))
    }
    proposal = document.get("proposal")
    if proposal is not None:
        if not isinstance(proposal, dict):
            errors.append("proposal must be an object")
        else:
            errors.extend(validate_proposal(graph, proposal, graph_digest, run_ids))

    results: list[tuple[str, dict[str, Any], list[str]]] = []
    for key, replay in scenarios:
        if not isinstance(replay, dict):
            continue
        replay_errors, diagnostics = validate_replay(graph, replay)
        errors.extend(f"{key}: {error}" for error in replay_errors)
        results.append((key, replay, diagnostics))

    if errors:
        print("INVALID")
        for error in errors:
            print(f"- {error}")
        return 1

    if isinstance(proposal, dict):
        print(f"VALID PROPOSAL: {proposal['proposal_id']} (base graph {proposal['base_graph_version']})")
    for key, replay, diagnostics in results:
        print(f"REPLAY MATCHED: {key}={replay['run_id']} ({len(diagnostics)} diagnostics)")
        for diagnostic in diagnostics:
            print(f"- {diagnostic}")
    if args.require_closure and any(diagnostics for _, _, diagnostics in results):
        print("CLOSURE BLOCKED: unresolved run diagnostics")
        return 2
    if isinstance(proposal, dict):
        print(f"PROMOTION: {proposal['promotion_status']}; active graph unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
