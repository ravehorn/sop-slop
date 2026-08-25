#!/usr/bin/env python3
"""Validate SOP SLOP diagnostic proposals and run-replay documents."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from validate_workflow_graph import DuplicateKeyError, _unique_object, load_graph


ROOT = Path(__file__).resolve().parents[1]
GRAPH_PATH = ROOT / "references" / "workflow-graph.json"
PROPOSAL_PATH = ROOT / "references" / "forward-test-fixture-0.6.0.json"
SCENARIO_KEYS = ("historical_replay", "forward_test", "run")
PROMOTION_STATUSES = {
    "replay_validated_pending_independent_forward_test",
    "forward_test_validated_pending_promotion",
    "promoted",
}
PASS_RESULTS = {"pass", "passed", "accepted", "success", "succeeded", "completed"}
CANDIDATE_BRANCHES = {"review_candidate", "exercise_candidate", "run_required_checks"}
DELIBERATION_SUCCESS_RESULTS = PASS_RESULTS | {"accepted_after_revision", "accept_with_concern"}
DELIBERATION_READ_ONLY_TOOLS = {
    "browser_read", "document_read", "repository_read", "screenshot_read", "source_read", "test_read", "web_search",
}


def load_document(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        document = json.load(handle, object_pairs_hook=_unique_object)
    if not isinstance(document, dict):
        raise ValueError("document must be a JSON object")
    return document


def present(value: Any) -> bool:
    return value not in (None, "", [], {})


def canonical_digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def proposal_content_digest(proposal: dict[str, Any]) -> str:
    return canonical_digest({
        field: proposal.get(field)
        for field in (
            "proposal", "acceptance_mapping", "hard_invariant_check", "evidence_refs", "retained_concerns",
        )
    })


def validate_run_cleanup(
    graph: dict[str, Any], replay: dict[str, Any], evidence: dict[str, Any]
) -> list[str]:
    if "reconcile_run_resources" not in replay.get("selected_stages", []):
        return []

    errors: list[str] = []
    manifests = [item for item in evidence.get("run_resource_manifest", []) if isinstance(item, dict)]
    receipts = [item for item in evidence.get("run_cleanup_receipt", []) if isinstance(item, dict)]
    if len(manifests) != 1:
        return ["cleanup requires exactly one run_resource_manifest"]
    if not receipts:
        return ["cleanup requires at least one run_cleanup_receipt"]

    manifest = manifests[0]
    run_id = replay.get("run_id")
    graph_version = graph.get("graph", {}).get("version")
    if manifest.get("run_id") != run_id or manifest.get("graph_version") != graph_version:
        errors.append("cleanup manifest must bind the current run and graph version")
    resources = manifest.get("resources")
    exact_targets = manifest.get("exact_targets")
    if not isinstance(resources, list) or not all(isinstance(item, dict) for item in resources):
        return errors + ["cleanup manifest resources must be a list of typed objects"]
    resource_ids = [item.get("resource_id") for item in resources]
    targets = [item.get("target") for item in resources]
    resource_by_id = {
        item.get("resource_id"): item
        for item in resources
        if isinstance(item.get("resource_id"), str)
    }
    if (
        not all(isinstance(item, str) and item for item in resource_ids + targets)
        or len(resource_ids) != len(set(resource_ids))
        or len(targets) != len(set(targets))
    ):
        errors.append("cleanup manifest resources need unique non-empty ids and exact targets")
    if not isinstance(exact_targets, list) or exact_targets != targets:
        errors.append("cleanup manifest exact_targets must match the ordered resource target list")
    broad_targets = {"/", "~", "$HOME", "${HOME}", "workspace_root", "filesystem_root", "home_root"}
    for target in targets:
        if isinstance(target, str) and (target in broad_targets or any(token in target for token in ("*", "?", "$(", "${"))):
            errors.append(f"cleanup target is broad or unresolved: {target}")

    manifest_digest = canonical_digest(manifest)
    allowed_classifications = {
        "release_without_data_deletion", "destructive_cleanup_requires_confirmation", "preserve_with_reason",
    }
    decision_receipts = {
        item.get("decision_id"): item
        for item in evidence.get("decision_receipt", [])
        if isinstance(item, dict) and present(item.get("decision_id"))
    }
    destructive_actions = {"delete", "remove_files", "remove_worktree", "remove_environment", "purge_cache"}
    required_worktree_checks = {
        "run_owned", "not_primary_workspace", "clean", "no_untracked_files", "commit_pushed",
        "branch_merged_or_disposal_explicitly_confirmed", "no_active_run_lease",
    }
    card_fields = {
        "what", "targets", "count", "size", "location", "why", "recoverable",
        "what_would_be_lost", "alternatives",
    }

    for index, receipt in enumerate(receipts):
        label = f"cleanup receipt {index}"
        if (
            receipt.get("run_id") != run_id
            or receipt.get("graph_version") != graph_version
            or receipt.get("resource_manifest_digest") != manifest_digest
        ):
            errors.append(f"{label} must bind the current run, graph version, and exact manifest digest")
        inventory = receipt.get("inventory")
        classifications = receipt.get("classifications")
        actions = receipt.get("actions")
        preserved = receipt.get("preserved_resources")
        if inventory != resource_ids:
            errors.append(f"{label} inventory must cover every manifest resource exactly once")
        if not isinstance(classifications, dict) or set(classifications) != set(resource_ids) or not set(classifications.values()) <= allowed_classifications:
            errors.append(f"{label} classifications must cover every resource with the closed classification set")
            destructive_targets: list[str] = []
        else:
            target_by_resource = dict(zip(resource_ids, targets))
            destructive_targets = [
                target_by_resource[resource_id]
                for resource_id in resource_ids
                if classifications[resource_id] == "destructive_cleanup_requires_confirmation"
            ]
        if not isinstance(actions, list) or not isinstance(preserved, list):
            errors.append(f"{label} actions and preserved_resources must be lists")
            continue

        result = receipt.get("result")
        card = receipt.get("deletion_card")
        if result == "confirmation_required":
            if not isinstance(card, dict) or not card_fields <= set(card) or card.get("targets") != destructive_targets:
                errors.append(f"{label} needs an exact recoverability card for the current targets")
            if receipt.get("decision_ref") is not None or actions:
                errors.append(f"{label} cannot execute destructive cleanup before confirmation")
            continue
        if result == "blocked":
            blocker = receipt.get("blocker")
            if not isinstance(blocker, dict) or not {"resource_id", "reason", "owner", "unblocker"} <= set(blocker):
                errors.append(f"{label} must identify the exact cleanup blocker and unblocker")
            continue
        if result != "reconciled":
            errors.append(f"{label} has invalid cleanup result")
            continue

        action_by_resource = {
            item.get("resource_id"): item
            for item in actions
            if isinstance(item, dict) and present(item.get("resource_id"))
        }
        preserved_by_resource = {
            item.get("resource_id"): item
            for item in preserved
            if isinstance(item, dict) and present(item.get("resource_id"))
        }
        for resource_id in resource_ids:
            if (resource_id in action_by_resource) == (resource_id in preserved_by_resource):
                errors.append(f"{label} must release or preserve resource {resource_id} exactly once")
                continue
            if resource_id in preserved_by_resource and not present(preserved_by_resource[resource_id].get("reason")):
                errors.append(f"{label} preservation for {resource_id} needs a concrete reason")
            if resource_id in preserved_by_resource and classifications.get(resource_id) != "preserve_with_reason":
                errors.append(f"{label} preserved resource {resource_id} must use preserve_with_reason")
            action = action_by_resource.get(resource_id)
            if action is None:
                continue
            if action.get("target") != resource_by_id.get(resource_id, {}).get("target"):
                errors.append(f"{label} action for {resource_id} changed the exact manifest target")
            if str(action.get("result", "")).lower() not in PASS_RESULTS:
                errors.append(f"{label} action for {resource_id} lacks successful verification")
            if action.get("action") in destructive_actions:
                decision = decision_receipts.get(receipt.get("decision_ref"))
                scope = decision.get("scope") if isinstance(decision, dict) else None
                if (
                    classifications.get(resource_id) != "destructive_cleanup_requires_confirmation"
                    or not isinstance(decision, dict)
                    or str(decision.get("selection", "")).strip().lower() not in {"yes", "do it"}
                    or not isinstance(scope, dict)
                    or scope.get("resource_manifest_digest") != manifest_digest
                    or scope.get("exact_targets") != destructive_targets
                ):
                    errors.append(f"{label} destructive action for {resource_id} lacks exact explicit confirmation")
            elif classifications.get(resource_id) != "release_without_data_deletion":
                errors.append(f"{label} non-destructive action for {resource_id} has the wrong classification")
            if action.get("action") == "remove_worktree":
                checks = action.get("checks")
                if not isinstance(checks, dict) or not all(checks.get(key) is True for key in required_worktree_checks):
                    errors.append(f"{label} worktree removal for {resource_id} lacks every safety proof")

    return errors


def validate_deliberations(
    graph: dict[str, Any], replay: dict[str, Any], evidence: dict[str, Any]
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    diagnostics: list[str] = []
    records = replay.get("deliberations", [])
    if not isinstance(records, list):
        return ["deliberations must be a list"], diagnostics
    typed_ids = {
        "deliberation_request", "deliberation_round", "deliberation_joint_proposal",
        "deliberation_consent_receipt", "deliberation_return_receipt",
    }
    has_typed_evidence = any(evidence.get(evidence_id) for evidence_id in typed_ids)
    if not records:
        if has_typed_evidence:
            errors.append("typed deliberation evidence requires a deliberations index")
        return errors, diagnostics

    profiles = {item["id"]: item for item in graph.get("deliberation_profiles", [])}
    templates = {item["id"]: item for item in graph.get("dynamic_subgraph_templates", [])}
    template = templates.get("bounded_peer_deliberation", {})
    template_edges = {
        (item.get("from"), item.get("to"))
        for item in template.get("edges", [])
        if isinstance(item, dict)
    }
    closed_dispositions = set(template.get("outcome_table", {}).get("domain", []))
    mission_anchor_fields = (
        "primary_outcome", "observable_proof", "non_goals", "requested_completion", "authority_source",
    )
    route_cards = [item for item in evidence.get("route_card", []) if isinstance(item, dict)]
    mission_anchor_digest = None
    if len(route_cards) == 1 and all(field in route_cards[0] for field in mission_anchor_fields):
        mission_anchor_digest = canonical_digest({field: route_cards[0].get(field) for field in mission_anchor_fields})
    requests: dict[str, dict[str, Any]] = {}
    for item in evidence.get("deliberation_request", []):
        if not isinstance(item, dict) or not present(item.get("request_id")):
            continue
        if item["request_id"] in requests:
            errors.append(f"deliberation {item['request_id']} must have exactly one typed request")
        else:
            requests[item["request_id"]] = item
    rounds_by_request: dict[str, list[dict[str, Any]]] = {}
    proposals_by_request: dict[str, list[dict[str, Any]]] = {}
    consent_by_request: dict[str, list[dict[str, Any]]] = {}
    returns: dict[str, dict[str, Any]] = {}
    for item in evidence.get("deliberation_return_receipt", []):
        if not isinstance(item, dict) or not present(item.get("request_id")):
            continue
        if item["request_id"] in returns:
            errors.append(f"deliberation {item['request_id']} must have exactly one typed return receipt")
        else:
            returns[item["request_id"]] = item
    for evidence_id, target in (
        ("deliberation_round", rounds_by_request),
        ("deliberation_joint_proposal", proposals_by_request),
        ("deliberation_consent_receipt", consent_by_request),
    ):
        for item in evidence.get(evidence_id, []):
            if isinstance(item, dict) and present(item.get("request_id")):
                target.setdefault(item["request_id"], []).append(item)

    envelopes: dict[str, dict[str, Any]] = {}
    for item in replay.get("delegations", []):
        if not isinstance(item, dict) or not present(item.get("execution_id")):
            continue
        if item["execution_id"] in envelopes:
            errors.append(f"delegation envelope {item['execution_id']} must be unique")
        else:
            envelopes[item["execution_id"]] = item
    receipts: dict[str, dict[str, Any]] = {}
    for item in evidence.get("delegation_receipt", []):
        if not isinstance(item, dict) or not present(item.get("execution_id")):
            continue
        if item["execution_id"] in receipts:
            errors.append(f"delegation receipt {item['execution_id']} must be unique")
        else:
            receipts[item["execution_id"]] = item
    verification_receipts_by_id: dict[str, list[dict[str, Any]]] = {}
    for item in evidence.get("verification_receipt", []):
        if isinstance(item, dict) and present(item.get("receipt_id")):
            verification_receipts_by_id.setdefault(item["receipt_id"], []).append(item)
    decision_receipts_by_id: dict[str, list[dict[str, Any]]] = {}
    for item in evidence.get("decision_receipt", []):
        if isinstance(item, dict) and present(item.get("decision_id")):
            decision_receipts_by_id.setdefault(item["decision_id"], []).append(item)
    record_ids = [
        item.get("request_id")
        for item in records
        if isinstance(item, dict) and present(item.get("request_id"))
    ]
    if len(record_ids) != len(set(record_ids)):
        errors.append("deliberations index must contain each request exactly once")
    seen_pairs: set[tuple[str, str]] = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict) or not present(record.get("request_id")):
            errors.append(f"deliberations[{index}] must name request_id")
            continue
        request_id = record["request_id"]
        if record.get("template_id") != "bounded_peer_deliberation":
            errors.append(f"deliberation {request_id} must use the shared bounded_peer_deliberation template")
        internal_transitions = record.get("internal_transitions")
        current_internal = "prepare_deliberation"
        revision_count = 0
        evidence_cycle_count = 0
        human_decision_count = 0
        if not isinstance(internal_transitions, list) or not internal_transitions:
            errors.append(f"deliberation {request_id} needs an auditable internal call-return path")
        else:
            for transition in internal_transitions:
                if not isinstance(transition, str) or transition.count("->") != 1:
                    errors.append(f"deliberation {request_id} has malformed internal transition")
                    continue
                source, target = transition.split("->")
                if source != current_internal or (source, target) not in template_edges:
                    errors.append(f"deliberation {request_id} has illegal internal transition {transition}")
                if (source, target) == ("validate_deliberation", "discuss_with_peers"):
                    revision_count += 1
                if (source, target) == ("validate_deliberation", "resolve_deliberation_evidence"):
                    evidence_cycle_count += 1
                if (source, target) == ("validate_deliberation", "ask_material_human_decision"):
                    human_decision_count += 1
                current_internal = target
            if current_internal != "return_to_invoking_node":
                errors.append(f"deliberation {request_id} did not close at its call-return boundary")
            if evidence_cycle_count > 1 or human_decision_count > 1:
                errors.append(f"deliberation {request_id} exceeded its evidence or material-human-decision budget")
        request = requests.get(request_id)
        returned = returns.get(request_id)
        if request is None:
            errors.append(f"deliberation {request_id} is missing deliberation_request")
            continue
        caller = request.get("invoking_node_id")
        profile = profiles.get(request.get("profile_id"))
        if request.get("invoking_run_id") != replay.get("run_id") or caller not in replay.get("selected_stages", []):
            errors.append(f"deliberation {request_id} is not bound to this run and selected caller")
        if not isinstance(profile, dict) or caller not in profile.get("eligible_callers", []):
            errors.append(f"deliberation {request_id} uses an ineligible caller/profile pair")
            continue
        seen_pairs.add((caller, request["profile_id"]))
        if request.get("profile_version") != profile.get("version"):
            errors.append(f"deliberation {request_id} profile version is stale")
        if request.get("mission_anchor_digest") != mission_anchor_digest:
            errors.append(f"deliberation {request_id} is not bound to the run's stable mission anchor")
        frozen_input_refs = request.get("frozen_input_refs")
        if (
            not isinstance(frozen_input_refs, list)
            or not frozen_input_refs
            or not all(isinstance(ref, str) and ref.strip() for ref in frozen_input_refs)
            or len(frozen_input_refs) != len(set(frozen_input_refs))
            or request.get("input_digest") != canonical_digest(frozen_input_refs)
        ):
            errors.append(f"deliberation {request_id} input digest does not match its frozen canonical references")
            frozen_input_ref_set: set[str] = set()
        else:
            frozen_input_ref_set = {ref for ref in frozen_input_refs if isinstance(ref, str)}
        if request.get("return_node_id") != caller or request.get("return_contract") != "resume_exact_invoking_node_after_controller_validation":
            errors.append(f"deliberation {request_id} request does not bind exact caller return")
        if request.get("model") != "gpt-5.6-luna" or request.get("reasoning_effort") != "max":
            errors.append(f"deliberation {request_id} request must select gpt-5.6-luna at max effort")
        roster = request.get("participant_roster")
        if not isinstance(roster, list) or len(roster) != 3 or len(set(roster)) != 3:
            errors.append(f"deliberation {request_id} must have three distinct specialists")
            roster = []
        if set(request.get("specialist_lenses", [])) != set(profile.get("lenses", [])):
            errors.append(f"deliberation {request_id} lenses do not match its profile")
        if request.get("round_budget") != 2 or request.get("contribution_budget") != {"min": 1, "max": 2}:
            errors.append(f"deliberation {request_id} exceeds the bounded discussion contract")
        if not request.get("hard_invariants") or "deliberation_return_receipt" not in request.get("expected_return_evidence", []):
            errors.append(f"deliberation {request_id} must freeze hard invariants and expected return evidence")

        evidence_cycle_receipt_ids = record.get("evidence_cycle_receipt_ids", [])
        human_decision_receipt_ids = record.get("human_decision_receipt_ids", [])
        if (
            not isinstance(evidence_cycle_receipt_ids, list)
            or len(evidence_cycle_receipt_ids) != evidence_cycle_count
            or len(evidence_cycle_receipt_ids) != len(set(evidence_cycle_receipt_ids))
        ):
            errors.append(f"deliberation {request_id} must bind one request-bound evidence receipt per evidence cycle")
            evidence_cycle_receipt_ids = []
        if (
            not isinstance(human_decision_receipt_ids, list)
            or len(human_decision_receipt_ids) != human_decision_count
            or len(human_decision_receipt_ids) != len(set(human_decision_receipt_ids))
        ):
            errors.append(f"deliberation {request_id} must bind one request-bound human decision receipt per picker cycle")
            human_decision_receipt_ids = []
        resolution_evidence_refs: set[str] = set()
        for receipt_id in evidence_cycle_receipt_ids:
            matching = verification_receipts_by_id.get(receipt_id, [])
            if len(matching) != 1:
                errors.append(f"deliberation {request_id} evidence cycle receipt must resolve exactly once")
                continue
            receipt = matching[0]
            if (
                receipt.get("request_id") != request_id
                or receipt.get("subject_digest") != request.get("input_digest")
                or str(receipt.get("result", "")).lower() not in PASS_RESULTS
                or (isinstance(returned, dict) and str(receipt.get("created_at", "")) > str(returned.get("returned_at", "")))
            ):
                errors.append(f"deliberation {request_id} evidence cycle receipt is stale, failed, or unbound")
            else:
                resolution_evidence_refs.add(receipt_id)
        for decision_id in human_decision_receipt_ids:
            matching = decision_receipts_by_id.get(decision_id, [])
            if len(matching) != 1:
                errors.append(f"deliberation {request_id} human decision receipt must resolve exactly once")
                continue
            decision = matching[0]
            options = decision.get("options")
            selection = decision.get("selection")
            options_valid = (
                isinstance(options, list)
                and len(options) in {2, 3}
                and all(isinstance(option, str) and option.strip() for option in options)
                and len(options) == len(set(options))
            )
            selected_option = selection.get("option") if isinstance(selection, dict) else selection
            selection_valid = options_valid and selected_option in options
            if selected_option == "Other":
                selection_valid = isinstance(selection, dict) and present(selection.get("value"))
            actor = str(decision.get("actor", "")).strip().lower()
            if (
                decision.get("request_id") != request_id
                or decision.get("input_digest") != request.get("input_digest")
                or decision.get("scope") != request_id
                or decision.get("decision_channel") != "codex_multiple_choice_picker"
                or not present(decision.get("question"))
                or actor in {"", "controller", "agent", "model"}
                or (isinstance(returned, dict) and str(decision.get("decided_at", "")) > str(returned.get("returned_at", "")))
            ):
                errors.append(f"deliberation {request_id} human decision must be a bound Codex picker receipt from a human")
            elif not selection_valid:
                errors.append(f"deliberation {request_id} human decision must select exactly one offered picker option")
            else:
                resolution_evidence_refs.add(decision_id)

        request_rounds = rounds_by_request.get(request_id, [])
        round_numbers = [item.get("round_number") for item in request_rounds]
        if not all(isinstance(number, int) for number in round_numbers) or sorted(round_numbers) not in ([1], [1, 2]):
            errors.append(f"deliberation {request_id} must record one or two unique bounded rounds")
        if revision_count != max(0, len(round_numbers) - 1):
            errors.append(f"deliberation {request_id} round count does not match its bounded revision path")
        peer_response_seen = False
        position_reporters: set[str] = set()
        request_execution_ids: set[str] = set()
        request_contribution_ids: set[str] = set()
        for round_receipt in sorted(request_rounds, key=lambda item: item.get("round_number", 0)):
            for field in ("invoking_run_id", "invoking_node_id", "input_digest", "profile_id", "profile_version"):
                if round_receipt.get(field) != request.get(field):
                    errors.append(f"deliberation {request_id} round changed frozen field {field}")
            if set(round_receipt.get("participant_roster", [])) != set(roster):
                errors.append(f"deliberation {request_id} round roster changed")
            contributions = round_receipt.get("contributions", [])
            counts = {specialist: 0 for specialist in roster}
            independent = set()
            contribution_owners: dict[str, str] = {}
            for contribution in contributions if isinstance(contributions, list) else []:
                if not isinstance(contribution, dict):
                    errors.append(f"deliberation {request_id} contribution must be an object")
                    continue
                specialist = contribution.get("specialist_id")
                if specialist in counts:
                    counts[specialist] += 1
                    if contribution.get("independent") is True:
                        independent.add(specialist)
                contribution_id = contribution.get("contribution_id")
                if not present(contribution_id) or contribution_id in request_contribution_ids:
                    errors.append(f"deliberation {request_id} contributions need unique IDs")
                else:
                    contribution_owners[contribution_id] = specialist
                    request_contribution_ids.add(contribution_id)
                for field in ("CLAIM", "WHY", "EVIDENCE", "QUESTION_FOR", "OBJECTION", "CHANGE_MY_MIND_IF"):
                    if not present(contribution.get(field)):
                        errors.append(f"deliberation {request_id} contribution is missing {field}")
            if any(count not in {1, 2} for count in counts.values()):
                errors.append(f"deliberation {request_id} must keep one or two contributions per specialist per round")
            if round_receipt.get("round_number") == 1 and independent != set(roster):
                errors.append(f"deliberation {request_id} first round lacks independent observations")
            broadcasts = round_receipt.get("broadcasts", [])
            broadcast_refs: dict[str, set[str]] = {specialist: set() for specialist in roster}
            for broadcast in broadcasts if isinstance(broadcasts, list) else []:
                if not isinstance(broadcast, dict) or broadcast.get("recipient") not in broadcast_refs:
                    errors.append(f"deliberation {request_id} broadcast names an unknown recipient")
                    continue
                if broadcast.get("delivery") != "lossless" or not isinstance(broadcast.get("statement_refs"), list):
                    errors.append(f"deliberation {request_id} broadcasts must preserve lossless typed statements")
                    continue
                broadcast_refs[broadcast["recipient"]].update(broadcast["statement_refs"])
            if set(broadcast_refs) != set(roster):
                errors.append(f"deliberation {request_id} did not broadcast peer statements to every specialist")
            for specialist in roster:
                expected_peer_refs = {
                    contribution_id
                    for contribution_id, owner in contribution_owners.items()
                    if owner != specialist
                }
                if broadcast_refs.get(specialist) != expected_peer_refs:
                    errors.append(f"deliberation {request_id} did not broadcast every peer statement to {specialist}")
            questions = round_receipt.get("named_questions", [])
            responses = round_receipt.get("responses", [])
            question_map: dict[str, dict[str, Any]] = {}
            for question in questions if isinstance(questions, list) else []:
                question_id = question.get("question_id") if isinstance(question, dict) else None
                if not present(question_id) or question_id in question_map:
                    errors.append(f"deliberation {request_id} named questions need unique IDs")
                    continue
                if question.get("from") not in roster or question.get("to") not in roster or question.get("from") == question.get("to"):
                    errors.append(f"deliberation {request_id} named question is outside the roster")
                if not present(question.get("question")):
                    errors.append(f"deliberation {request_id} named peer question must contain actual question text")
                question_map[question_id] = question
            response_map: dict[str, dict[str, Any]] = {}
            for response in responses if isinstance(responses, list) else []:
                response_id = response.get("question_id") if isinstance(response, dict) else None
                if not present(response_id) or response_id in response_map:
                    errors.append(f"deliberation {request_id} named responses need unique question IDs")
                    continue
                if not present(response.get("response")):
                    errors.append(f"deliberation {request_id} named peer response must contain actual response text")
                response_map[response_id] = response
            if not question_map or set(question_map) != set(response_map):
                errors.append(f"deliberation {request_id} has unanswered named peer questions")
            for question_id, question in question_map.items():
                if response_map.get(question_id, {}).get("responder") != question.get("to"):
                    errors.append(f"deliberation {request_id} named question was not answered by its named peer")
            peer_response_seen = peer_response_seen or bool(response_map)
            for position in round_receipt.get("position_changes", []):
                if isinstance(position, dict) and position.get("specialist_id") in roster and present(position.get("change")):
                    position_reporters.add(position["specialist_id"])
            for objection in round_receipt.get("objections", []):
                if not isinstance(objection, dict) or objection.get("specialist_id") not in roster or not (
                    present(objection.get("requirement"))
                    or present(objection.get("violated_requirement"))
                    or present(objection.get("missing_evidence"))
                ):
                    errors.append(f"deliberation {request_id} objection must identify a requirement or missing evidence")
            envelope_ids = set(round_receipt.get("delegation_envelopes", []))
            receipt_ids = set(round_receipt.get("delegation_receipts", []))
            if envelope_ids != receipt_ids or len(envelope_ids) != len(roster):
                errors.append(f"deliberation {request_id} round must bind one envelope and receipt per specialist")
            request_execution_ids.update(envelope_ids)
            execution_ids = envelope_ids | receipt_ids
            for execution_id in execution_ids:
                envelope, receipt = envelopes.get(execution_id), receipts.get(execution_id)
                if envelope is None or receipt is None:
                    errors.append(f"deliberation {request_id} is missing envelope or receipt for {execution_id}")
                    continue
                for item, label in ((envelope, "envelope"), (receipt, "receipt")):
                    if item.get("model") != "gpt-5.6-luna" or item.get("reasoning_effort") != "max":
                        errors.append(f"deliberation {request_id} {label} {execution_id} is not Luna/max")
                    if (
                        item.get("role_id") != "reviewer"
                        or item.get("request_id") != request_id
                        or item.get("parent_run_id") != replay.get("run_id")
                        or item.get("graph_version") != graph.get("graph", {}).get("version")
                        or item.get("node_id") != caller
                    ):
                        errors.append(f"deliberation {request_id} {label} {execution_id} is outside its reviewer scope")
                    if item.get("specialist_id") not in roster or item.get("lens") not in profile.get("lenses", []):
                        errors.append(f"deliberation {request_id} {label} {execution_id} does not bind a rostered specialist lens")
                    allowed_tools = item.get("allowed_tools")
                    if (
                        item.get("permissions") != "read-only"
                        or not isinstance(allowed_tools, list)
                        or not allowed_tools
                        or not all(isinstance(tool, str) for tool in allowed_tools)
                        or not set(allowed_tools) <= DELIBERATION_READ_ONLY_TOOLS
                    ):
                        errors.append(f"deliberation {request_id} {label} {execution_id} must stay read-only")
                if envelope.get("specialist_id") != receipt.get("specialist_id") or envelope.get("lens") != receipt.get("lens"):
                    errors.append(f"deliberation {request_id} envelope and receipt disagree for {execution_id}")
                bounded_fields = (
                    "ownership_scope", "allowed_tools", "permissions", "input_refs", "expected_output",
                    "verification_criteria", "stop_condition", "isolation",
                )
                for field in bounded_fields:
                    if not present(envelope.get(field)) or not present(receipt.get(field)):
                        errors.append(f"deliberation {request_id} {execution_id} is missing bounded delegation field {field}")
                if any(envelope.get(field) != receipt.get(field) for field in ("allowed_tools", "permissions", "input_refs", "isolation")):
                    errors.append(f"deliberation {request_id} envelope and receipt disagree on bounded scope for {execution_id}")
                if envelope.get("input_refs") != frozen_input_refs or receipt.get("input_refs") != frozen_input_refs:
                    errors.append(f"deliberation {request_id} {execution_id} did not receive the exact frozen input references")
                if envelope.get("fresh_thread") is not True or envelope.get("isolation") != "fresh_agent_thread" or receipt.get("isolation") != "fresh_agent_thread":
                    errors.append(f"deliberation {request_id} {execution_id} must be a fresh agent thread")
                if receipt.get("result") not in DELIBERATION_SUCCESS_RESULTS or receipt.get("controller_validation") != "accepted":
                    errors.append(f"deliberation {request_id} {execution_id} lacks a successful controller-accepted receipt")
        execution_pairs = {
            (envelopes[item].get("specialist_id"), envelopes[item].get("lens"))
            for item in request_execution_ids
            if item in envelopes
        }
        if {item[0] for item in execution_pairs} != set(roster) or {item[1] for item in execution_pairs} != set(profile.get("lenses", [])):
            errors.append(f"deliberation {request_id} does not map every named specialist to one profile lens")
        if not peer_response_seen:
            errors.append(f"deliberation {request_id} contains no real peer response")
        if position_reporters != set(roster):
            errors.append(f"deliberation {request_id} must record each specialist's changed or retained position")

        proposals = proposals_by_request.get(request_id, [])
        consents = consent_by_request.get(request_id, [])
        if not proposals or not consents:
            errors.append(f"deliberation {request_id} is missing joint proposal or consent evidence")
        proposals_by_digest: dict[str, dict[str, Any]] = {}
        for proposal in proposals:
            for field in ("input_digest", "profile_id", "profile_version"):
                if proposal.get(field) != request.get(field):
                    errors.append(f"deliberation {request_id} proposal changed frozen field {field}")
            proposal_digest = proposal.get("proposal_digest")
            if not present(proposal_digest) or proposal_digest in proposals_by_digest:
                errors.append(f"deliberation {request_id} proposals need unique digests")
            else:
                proposals_by_digest[proposal_digest] = proposal
            if proposal_digest != proposal_content_digest(proposal):
                errors.append(f"deliberation {request_id} proposal digest does not match its content")
            if proposal.get("round_number") not in round_numbers:
                errors.append(f"deliberation {request_id} proposal is not bound to a recorded round")
            if proposal.get("owner_lens") not in profile.get("lenses", []):
                errors.append(f"deliberation {request_id} proposal owner is outside the profile")
            owner_envelope = proposal.get("owner_delegation_envelope")
            owner_receipt = proposal.get("owner_delegation_receipt")
            if owner_envelope != owner_receipt or owner_receipt not in request_execution_ids:
                errors.append(f"deliberation {request_id} proposal owner must be one rostered execution")
            if (
                owner_envelope not in envelopes
                or owner_receipt not in receipts
                or envelopes[owner_envelope].get("model") != "gpt-5.6-luna"
                or envelopes[owner_envelope].get("reasoning_effort") != "max"
                or receipts[owner_receipt].get("model") != "gpt-5.6-luna"
                or receipts[owner_receipt].get("reasoning_effort") != "max"
                or envelopes[owner_envelope].get("lens") != proposal.get("owner_lens")
                or receipts[owner_receipt].get("lens") != proposal.get("owner_lens")
            ):
                errors.append(f"deliberation {request_id} proposal owner lacks a Luna/max receipt")
        consents_by_digest: dict[str, dict[str, Any]] = {}
        for consent in consents:
            if consent.get("profile_id") != request.get("profile_id") or consent.get("profile_version") != request.get("profile_version"):
                errors.append(f"deliberation {request_id} consent changed the frozen profile")
            proposal_digest = consent.get("proposal_digest")
            if proposal_digest not in proposals_by_digest or proposal_digest in consents_by_digest:
                errors.append(f"deliberation {request_id} consent must bind exactly one recorded proposal")
            else:
                consents_by_digest[proposal_digest] = consent
            if set(consent.get("allowed_values", [])) != {"accept", "accept_with_concern", "object"}:
                errors.append(f"deliberation {request_id} consent values are invalid")
            responses = consent.get("specialist_responses", [])
            statuses = {
                item.get("specialist_id"): item.get("status")
                for item in responses
                if isinstance(item, dict)
            }
            if len(responses) != len(roster) or set(statuses) != set(roster) or not set(statuses.values()) <= {"accept", "accept_with_concern", "object"}:
                errors.append(f"deliberation {request_id} consent must contain one allowed response per specialist")
            consent_objections = consent.get("objections", [])
            objectors = {specialist for specialist, status in statuses.items() if status == "object"}
            recorded_objectors: set[str] = set()
            for objection in consent_objections if isinstance(consent_objections, list) else []:
                if not isinstance(objection, dict) or objection.get("specialist_id") not in roster or not (
                    present(objection.get("violated_requirement")) or present(objection.get("missing_evidence"))
                ):
                    errors.append(f"deliberation {request_id} consent objection must cite a violated requirement or missing evidence")
                    continue
                recorded_objectors.add(objection["specialist_id"])
            if recorded_objectors != objectors:
                errors.append(f"deliberation {request_id} objecting specialists must supply evidence-based objections")
            if set(consent.get("delegation_envelopes", [])) != request_execution_ids or set(consent.get("delegation_receipts", [])) != request_execution_ids:
                errors.append(f"deliberation {request_id} consent must bind every rostered Luna/max execution")

        if returned is None:
            diagnostics.append(f"missing_deliberation_return:{request_id}")
            continue
        for field in ("invoking_run_id", "mission_anchor_digest", "invoking_node_id", "input_digest", "profile_id", "profile_version"):
            if returned.get(field) != request.get(field):
                errors.append(f"deliberation {request_id} return changed frozen field {field}")
        if returned.get("return_node_id") != caller:
            errors.append(f"deliberation {request_id} did not return to the exact caller")
        if returned.get("controller_validation") != "accepted":
            diagnostics.append(f"unvalidated_deliberation_return:{request_id}")
        disposition = returned.get("disposition")
        if disposition not in closed_dispositions:
            errors.append(f"deliberation {request_id} returned an unknown closed disposition")
        if record.get("closed_outcome") not in {"accepted", "blocked", "fatal"} or record.get("closed_outcome") != disposition:
            errors.append(f"deliberation {request_id} index does not match its final closed return")
        if record.get("revision_rounds", 0) != revision_count:
            errors.append(f"deliberation {request_id} index does not match its revision count")
        if disposition == "accepted":
            accepted_ref = returned.get("accepted_proposal_ref")
            accepted_proposal = proposals_by_digest.get(accepted_ref)
            accepted_consent = consents_by_digest.get(accepted_ref)
            if accepted_proposal is None or accepted_consent is None:
                errors.append(f"deliberation {request_id} accepted without a bound proposal and consent")
            else:
                final_statuses = {
                    item.get("specialist_id"): item.get("status")
                    for item in accepted_consent.get("specialist_responses", [])
                    if isinstance(item, dict)
                }
                if "object" in final_statuses.values() or accepted_proposal.get("hard_invariant_check") != "pass":
                    errors.append(f"deliberation {request_id} accepted despite an objection or failed invariant")
                acceptance_mapping = accepted_proposal.get("acceptance_mapping")
                proposal_evidence_refs = accepted_proposal.get("evidence_refs")
                known_evidence_refs = request_contribution_ids | frozen_input_ref_set | resolution_evidence_refs
                if (
                    not isinstance(acceptance_mapping, dict)
                    or set(acceptance_mapping) != set(request.get("acceptance_criteria", []))
                    or not all(present(value) for value in acceptance_mapping.values())
                    or not isinstance(proposal_evidence_refs, list)
                    or not proposal_evidence_refs
                    or not all(isinstance(ref, str) and ref in known_evidence_refs for ref in proposal_evidence_refs)
                    or not resolution_evidence_refs <= set(proposal_evidence_refs)
                ):
                    errors.append(f"deliberation {request_id} accepted without mapping every criterion to evidence")
                if "accept_with_concern" in final_statuses.values() and not present(returned.get("dissent")):
                    errors.append(f"deliberation {request_id} dropped a minority concern from its return receipt")
        if disposition == "accepted" and returned.get("hard_invariant_check") != "pass":
            diagnostics.append(f"deliberation_hard_invariant_unproven:{request_id}")
        if disposition in {"blocked", "fatal"} and returned.get("hard_invariant_check") not in {"pass", "failed"}:
            diagnostics.append(f"deliberation_hard_invariant_unproven:{request_id}")

    if replay.get("deliberation_forward_test") is True and len(seen_pairs) < 2:
        errors.append("deliberation forward test must exercise at least two distinct caller/profile pairs")
    return errors, diagnostics


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


def run_deliberation_self_tests(
    graph: dict[str, Any], replay: dict[str, Any]
) -> tuple[list[str], int]:
    if not replay.get("deliberations"):
        return ["deliberation self-test requires a replay with deliberation evidence"], 0

    cases: list[tuple[str, dict[str, Any], str]] = []

    wrong_model = copy.deepcopy(replay)
    wrong_model["delegations"][0]["model"] = "gpt-5.6-terra"
    cases.append(("wrong specialist model", wrong_model, "is not Luna/max"))

    missing_peer_statement = copy.deepcopy(replay)
    missing_peer_statement["evidence"]["deliberation_round"][0]["broadcasts"][0]["statement_refs"].pop()
    cases.append(("missing peer broadcast", missing_peer_statement, "did not broadcast every peer statement"))

    unanswered_peer = copy.deepcopy(replay)
    unanswered_peer["evidence"]["deliberation_round"][0]["responses"] = []
    cases.append(("unanswered named peer", unanswered_peer, "unanswered named peer questions"))

    empty_peer_exchange = copy.deepcopy(replay)
    empty_peer_exchange["evidence"]["deliberation_round"][0]["named_questions"][0]["question"] = ""
    empty_peer_exchange["evidence"]["deliberation_round"][0]["responses"][0]["response"] = ""
    cases.append(("empty peer exchange", empty_peer_exchange, "must contain actual question text"))

    accepted_objection = copy.deepcopy(replay)
    accepted_objection["evidence"]["deliberation_consent_receipt"][-1]["specialist_responses"][0]["status"] = "object"
    cases.append(("accepted objection", accepted_objection, "objecting specialists must supply evidence-based objections"))

    wrong_return = copy.deepcopy(replay)
    wrong_return["evidence"]["deliberation_return_receipt"][0]["return_node_id"] = "review_engineering"
    cases.append(("wrong caller return", wrong_return, "did not return to the exact caller"))

    duplicate_return = copy.deepcopy(replay)
    forged_return = copy.deepcopy(duplicate_return["evidence"]["deliberation_return_receipt"][0])
    forged_return["return_node_id"] = "review_engineering"
    duplicate_return["evidence"]["deliberation_return_receipt"].insert(0, forged_return)
    cases.append(("duplicate typed return", duplicate_return, "must have exactly one typed return receipt"))

    wrong_mission = copy.deepcopy(replay)
    wrong_mission["evidence"]["deliberation_request"][0]["mission_anchor_digest"] = "0" * 64
    cases.append(("wrong mission binding", wrong_mission, "not bound to the run's stable mission anchor"))

    alternate_mission = copy.deepcopy(replay)
    alternate_card = copy.deepcopy(alternate_mission["evidence"]["route_card"][0])
    for field in ("primary_outcome", "observable_proof", "requested_completion", "authority_source"):
        alternate_card[field] = f"alternate-{field}"
    alternate_card["non_goals"] = ["alternate-mission"]
    alternate_mission["evidence"]["route_card"].append(alternate_card)
    alternate_digest = canonical_digest({
        field: alternate_card[field]
        for field in ("primary_outcome", "observable_proof", "non_goals", "requested_completion", "authority_source")
    })
    alternate_mission["evidence"]["deliberation_request"][0]["mission_anchor_digest"] = alternate_digest
    alternate_mission["evidence"]["deliberation_return_receipt"][0]["mission_anchor_digest"] = alternate_digest
    cases.append(("competing mission route card", alternate_mission, "exactly one canonical route_card"))

    stale_frozen_input = copy.deepcopy(replay)
    stale_frozen_input["evidence"]["deliberation_request"][0]["frozen_input_refs"].append("unbound:new-input")
    cases.append(("stale frozen input", stale_frozen_input, "input digest does not match"))

    specialist_wrong_input = copy.deepcopy(replay)
    execution_id = specialist_wrong_input["delegations"][0]["execution_id"]
    specialist_wrong_input["delegations"][0]["input_refs"] = ["different://unfrozen-input"]
    next(item for item in specialist_wrong_input["evidence"]["delegation_receipt"] if item["execution_id"] == execution_id)["input_refs"] = ["different://unfrozen-input"]
    cases.append(("specialist wrong frozen input", specialist_wrong_input, "did not receive the exact frozen input references"))

    stale_proposal = copy.deepcopy(replay)
    stale_proposal["evidence"]["deliberation_joint_proposal"][0]["proposal"] += " Unbound change."
    cases.append(("stale proposal digest", stale_proposal, "proposal digest does not match"))

    empty_acceptance_proof = copy.deepcopy(replay)
    proposal = empty_acceptance_proof["evidence"]["deliberation_joint_proposal"][0]
    old_digest = proposal["proposal_digest"]
    proposal["acceptance_mapping"] = {key: "" for key in proposal["acceptance_mapping"]}
    proposal["evidence_refs"] = ["does-not-exist"]
    new_digest = proposal_content_digest(proposal)
    proposal["proposal_digest"] = new_digest
    for consent in empty_acceptance_proof["evidence"]["deliberation_consent_receipt"]:
        if consent.get("proposal_digest") == old_digest:
            consent["proposal_digest"] = new_digest
    for returned in empty_acceptance_proof["evidence"]["deliberation_return_receipt"]:
        if returned.get("accepted_proposal_ref") == old_digest:
            returned["accepted_proposal_ref"] = new_digest
    cases.append(("empty acceptance proof", empty_acceptance_proof, "accepted without mapping every criterion to evidence"))

    missing_resolution_receipts = copy.deepcopy(replay)
    missing_resolution_receipts["deliberations"][0]["internal_transitions"] = [
        "prepare_deliberation->observe_independently",
        "observe_independently->discuss_with_peers",
        "discuss_with_peers->draft_joint_proposal",
        "draft_joint_proposal->check_deliberation_consent",
        "check_deliberation_consent->validate_deliberation",
        "validate_deliberation->resolve_deliberation_evidence",
        "resolve_deliberation_evidence->draft_joint_proposal",
        "draft_joint_proposal->check_deliberation_consent",
        "check_deliberation_consent->validate_deliberation",
        "validate_deliberation->ask_material_human_decision",
        "ask_material_human_decision->draft_joint_proposal",
        "draft_joint_proposal->check_deliberation_consent",
        "check_deliberation_consent->validate_deliberation",
        "validate_deliberation->return_to_invoking_node",
    ]
    missing_resolution_receipts["deliberations"][0]["evidence_cycle_receipt_ids"] = []
    missing_resolution_receipts["deliberations"][0]["human_decision_receipt_ids"] = []
    cases.append(("missing resolution receipts", missing_resolution_receipts, "must bind one request-bound evidence receipt"))

    off_menu_picker_selection = copy.deepcopy(replay)
    off_menu_picker_selection["deliberations"][0]["internal_transitions"] = [
        "prepare_deliberation->observe_independently",
        "observe_independently->discuss_with_peers",
        "discuss_with_peers->draft_joint_proposal",
        "draft_joint_proposal->check_deliberation_consent",
        "check_deliberation_consent->validate_deliberation",
        "validate_deliberation->ask_material_human_decision",
        "ask_material_human_decision->draft_joint_proposal",
        "draft_joint_proposal->check_deliberation_consent",
        "check_deliberation_consent->validate_deliberation",
        "validate_deliberation->return_to_invoking_node",
    ]
    off_menu_picker_selection["deliberations"][0]["human_decision_receipt_ids"] = ["decision-off-menu"]
    request = off_menu_picker_selection["evidence"]["deliberation_request"][0]
    off_menu_picker_selection["evidence"]["decision_receipt"] = [{
        "decision_id": "decision-off-menu",
        "request_id": request["request_id"],
        "input_digest": request["input_digest"],
        "decision_channel": "codex_multiple_choice_picker",
        "question": "Choose one offered option.",
        "options": ["A", "B"],
        "recommendation": "A",
        "selection": "Z-not-offered",
        "actor": "synthetic-human",
        "scope": request["request_id"],
        "decided_at": "2026-01-02T00:07:00Z",
    }]
    cases.append(("off-menu picker selection", off_menu_picker_selection, "select exactly one offered picker option"))

    unbounded_round = copy.deepcopy(replay)
    third_round = copy.deepcopy(unbounded_round["evidence"]["deliberation_round"][-1])
    third_round["round_number"] = 3
    unbounded_round["evidence"]["deliberation_round"].append(third_round)
    cases.append(("unbounded round", unbounded_round, "one or two unique bounded rounds"))

    parallel_writer = copy.deepcopy(replay)
    execution_id = parallel_writer["delegations"][0]["execution_id"]
    parallel_writer["delegations"][0]["permissions"] = "modify_repository"
    parallel_writer["delegations"][0]["allowed_tools"] = ["apply_patch"]
    writer_receipt = next(item for item in parallel_writer["evidence"]["delegation_receipt"] if item["execution_id"] == execution_id)
    writer_receipt["permissions"] = "modify_repository"
    writer_receipt["allowed_tools"] = ["apply_patch"]
    cases.append(("deliberation writer", parallel_writer, "must stay read-only"))

    failed_specialist_receipt = copy.deepcopy(replay)
    execution_id = failed_specialist_receipt["delegations"][0]["execution_id"]
    failed_receipt = next(item for item in failed_specialist_receipt["evidence"]["delegation_receipt"] if item["execution_id"] == execution_id)
    failed_receipt["result"] = "failed"
    failed_receipt["controller_validation"] = "rejected"
    cases.append(("failed specialist receipt", failed_specialist_receipt, "lacks a successful controller-accepted receipt"))

    hard_gate_waived = copy.deepcopy(replay)
    hard_gate_waived["evidence"]["deliberation_joint_proposal"][0]["hard_invariant_check"] = "failed"
    cases.append(("accepted failed invariant", hard_gate_waived, "accepted despite an objection or failed invariant"))

    dropped_concern = copy.deepcopy(replay)
    dropped_concern["evidence"]["deliberation_return_receipt"][0]["dissent"] = []
    cases.append(("dropped minority concern", dropped_concern, "dropped a minority concern"))

    evidence_budget = copy.deepcopy(replay)
    evidence_budget["deliberations"][0]["internal_transitions"] = [
        "prepare_deliberation->observe_independently",
        "observe_independently->discuss_with_peers",
        "discuss_with_peers->draft_joint_proposal",
        "draft_joint_proposal->check_deliberation_consent",
        "check_deliberation_consent->validate_deliberation",
        "validate_deliberation->resolve_deliberation_evidence",
        "resolve_deliberation_evidence->draft_joint_proposal",
        "draft_joint_proposal->check_deliberation_consent",
        "check_deliberation_consent->validate_deliberation",
        "validate_deliberation->resolve_deliberation_evidence",
        "resolve_deliberation_evidence->draft_joint_proposal",
        "draft_joint_proposal->check_deliberation_consent",
        "check_deliberation_consent->validate_deliberation",
        "validate_deliberation->return_to_invoking_node",
    ]
    cases.append(("unbounded evidence cycles", evidence_budget, "exceeded its evidence or material-human-decision budget"))

    human_budget = copy.deepcopy(replay)
    human_budget["deliberations"][0]["internal_transitions"] = [
        "prepare_deliberation->observe_independently",
        "observe_independently->discuss_with_peers",
        "discuss_with_peers->draft_joint_proposal",
        "draft_joint_proposal->check_deliberation_consent",
        "check_deliberation_consent->validate_deliberation",
        "validate_deliberation->ask_material_human_decision",
        "ask_material_human_decision->draft_joint_proposal",
        "draft_joint_proposal->check_deliberation_consent",
        "check_deliberation_consent->validate_deliberation",
        "validate_deliberation->ask_material_human_decision",
        "ask_material_human_decision->draft_joint_proposal",
        "draft_joint_proposal->check_deliberation_consent",
        "check_deliberation_consent->validate_deliberation",
        "validate_deliberation->return_to_invoking_node",
    ]
    cases.append(("unbounded material human decisions", human_budget, "exceeded its evidence or material-human-decision budget"))

    parent_hard_gate = copy.deepcopy(replay)
    parent_hard_gate["selected_stages"].append("resolve_candidate")
    parent_hard_gate["observed_transitions"].append({
        "from": "resolve_candidate",
        "to": "record_run_receipt",
        "edge_id": "candidate_to_receipt",
        "outcome": "accepted_complete",
        "join_id": "negative-failed-join",
    })
    parent_hard_gate["evidence"]["fork_manifest"] = [{
        "fork_id": "negative-candidate-fork",
        "subject_digest": "negative-failed-subject",
        "dispatched_branches": sorted(CANDIDATE_BRANCHES),
        "isolation": "frozen_subject",
        "created_at": "2026-01-02T00:22:00Z",
    }]
    parent_hard_gate["evidence"]["verification_receipt"] = [
        {
            "receipt_id": f"negative-receipt-{branch}",
            "check_id": f"negative-{branch}",
            "fork_id": "negative-candidate-fork",
            "branch_id": branch,
            "subject_digest": "negative-failed-subject",
            "result": "fail" if branch == "run_required_checks" else "pass",
            "details_uri": f"fixture://negative/{branch}",
            "issuer": "synthetic-controller",
            "created_at": "2026-01-02T00:22:10Z",
        }
        for branch in sorted(CANDIDATE_BRANCHES)
    ]
    parent_hard_gate["evidence"]["join_receipt"] = [{
        "join_id": "negative-failed-join",
        "fork_id": "negative-candidate-fork",
        "subject_digest": "negative-failed-subject",
        "received_branches": sorted(CANDIDATE_BRANCHES),
        "branch_receipt_ids": {
            branch: f"negative-receipt-{branch}" for branch in sorted(CANDIDATE_BRANCHES)
        },
        "result": "accepted",
        "created_at": "2026-01-02T00:22:30Z",
    }]
    parent_hard_gate["evidence"]["verification_receipt"].append({
        "receipt_id": "negative-late-pass",
        "check_id": "negative-late-pass",
        "fork_id": "negative-candidate-fork",
        "branch_id": "run_required_checks",
        "subject_digest": "negative-failed-subject",
        "result": "pass",
        "details_uri": "fixture://negative/late-pass",
        "issuer": "synthetic-controller",
        "created_at": "2026-01-02T00:23:00Z",
    })
    cases.append(("forged accepted parent candidate gate", parent_hard_gate, "candidate join cannot accept failed or missing branch evidence"))

    failures: list[str] = []
    for name, candidate, expected in cases:
        candidate.pop("expected_diagnostics", None)
        case_errors, case_diagnostics = validate_replay(graph, candidate)
        if not any(expected in item for item in case_errors + case_diagnostics):
            failures.append(f"self-test {name!r} did not detect {expected!r}")
    return failures, len(cases)


def run_cleanup_self_tests(
    graph: dict[str, Any], replay: dict[str, Any]
) -> tuple[list[str], int]:
    evidence = replay.get("evidence", {})
    manifests = evidence.get("run_resource_manifest", []) if isinstance(evidence, dict) else []
    receipts = evidence.get("run_cleanup_receipt", []) if isinstance(evidence, dict) else []
    if not manifests or not receipts or not manifests[0].get("resources"):
        return [], 0

    cases: list[tuple[str, dict[str, Any], str]] = []

    broad_target = copy.deepcopy(replay)
    broad_target["evidence"]["run_resource_manifest"][0]["resources"][0]["target"] = "/"
    broad_target["evidence"]["run_resource_manifest"][0]["exact_targets"][0] = "/"
    cases.append(("broad cleanup target", broad_target, "broad or unresolved"))

    stale_digest = copy.deepcopy(replay)
    stale_digest["evidence"]["run_cleanup_receipt"][-1]["resource_manifest_digest"] = "0" * 64
    cases.append(("stale cleanup digest", stale_digest, "exact manifest digest"))

    inferred_consent = copy.deepcopy(replay)
    decision_ref = inferred_consent["evidence"]["run_cleanup_receipt"][-1]["decision_ref"]
    next(item for item in inferred_consent["evidence"]["decision_receipt"] if item["decision_id"] == decision_ref)["selection"] = "ok"
    cases.append(("inferred cleanup consent", inferred_consent, "lacks exact explicit confirmation"))

    unsafe_worktree = copy.deepcopy(replay)
    unsafe_worktree["evidence"]["run_cleanup_receipt"][-1]["actions"][0]["checks"]["clean"] = False
    cases.append(("unsafe worktree removal", unsafe_worktree, "lacks every safety proof"))

    missing_disposition = copy.deepcopy(replay)
    missing_disposition["evidence"]["run_cleanup_receipt"][-1]["actions"] = []
    cases.append(("missing resource disposition", missing_disposition, "release or preserve resource"))

    failures: list[str] = []
    for name, candidate, expected in cases:
        case_errors = validate_run_cleanup(graph, candidate, candidate["evidence"])
        if not any(expected in item for item in case_errors):
            failures.append(f"cleanup self-test {name!r} did not detect {expected!r}")
    return failures, len(cases)


def validate_replay(graph: dict[str, Any], replay: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    diagnostics: set[str] = set()
    evidence_types = {item["id"]: item for item in graph["evidence_types"]}
    nodes = {item["id"]: item for item in graph["nodes"]}
    edges = {item["id"]: item for item in graph["edges"]}
    outcome_tables = {item["node"]: item for item in graph.get("outcome_tables", [])}

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

    route_cards = [item for item in evidence.get("route_card", []) if isinstance(item, dict)]
    if len(route_cards) != 1:
        errors.append("replay must contain exactly one canonical route_card")
    elif route_cards[0].get("run_id") != replay.get("run_id"):
        errors.append("canonical route_card must bind the replay run_id")

    errors.extend(validate_run_cleanup(graph, replay, evidence))

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

    deliberation_errors, deliberation_diagnostics = validate_deliberations(graph, replay, evidence)
    errors.extend(deliberation_errors)
    diagnostics.update(deliberation_diagnostics)

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
        if source not in nodes or target not in nodes:
            errors.append(f"observed transition names an unknown node: {source}->{target}")
            continue
        if source not in selected_set or target not in selected_set:
            errors.append(f"observed transition is outside selected_stages: {source}->{target}")
        edge_id = transition.get("edge_id")
        edge = edges.get(edge_id)
        if edge is None or edge.get("from") != source or edge.get("to") != target:
            diagnostics.add(f"illegal_transition:{source}->{target}")
        table = outcome_tables.get(source)
        if table is not None:
            outcome = transition.get("outcome")
            matching_cases = [
                case
                for case in table.get("cases", [])
                if isinstance(case, dict) and case.get("value") == outcome and case.get("edge") == edge_id
            ]
            if len(matching_cases) != 1:
                errors.append(f"observed transition does not match the closed outcome table: {source}->{target}")
        incoming.add(target)

    if candidate_stages.intersection(selected_stages):
        fork_manifests = [item for item in evidence.get("fork_manifest", []) if isinstance(item, dict)]
        verification_receipts = [item for item in evidence.get("verification_receipt", []) if isinstance(item, dict)]
        join_receipts = [item for item in evidence.get("join_receipt", []) if isinstance(item, dict)]
        receipt_ids = [item.get("receipt_id") for item in verification_receipts if present(item.get("receipt_id"))]
        join_ids = [item.get("join_id") for item in join_receipts if present(item.get("join_id"))]
        if len(receipt_ids) != len(set(receipt_ids)):
            errors.append("verification receipt IDs must be unique")
        if len(join_ids) != len(set(join_ids)):
            errors.append("candidate join IDs must be unique")
        receipts_by_id = {item.get("receipt_id"): item for item in verification_receipts}
        joins_by_id = {item.get("join_id"): item for item in join_receipts}
        join_passes: dict[str, bool] = {}

        for join in join_receipts:
            join_id = join.get("join_id")
            matching_forks = [
                item for item in fork_manifests
                if item.get("fork_id") == join.get("fork_id")
                and item.get("subject_digest") == join.get("subject_digest")
            ]
            valid = len(matching_forks) == 1
            if not valid:
                errors.append("candidate join must bind exactly one fork manifest for the same subject")
                join_passes[str(join_id)] = False
                continue

            fork = matching_forks[0]
            dispatched = fork.get("dispatched_branches")
            received = join.get("received_branches")
            branch_receipt_ids = join.get("branch_receipt_ids")
            if not isinstance(dispatched, list) or set(dispatched) != CANDIDATE_BRANCHES or len(dispatched) != len(CANDIDATE_BRANCHES):
                errors.append("candidate fork must dispatch every required verification branch exactly once")
                valid = False
            if (
                not isinstance(received, list)
                or not isinstance(dispatched, list)
                or set(received) != set(dispatched)
                or len(received) != len(dispatched)
            ):
                errors.append("candidate join must receive every dispatched branch for the frozen subject")
                valid = False
            if (
                not isinstance(branch_receipt_ids, dict)
                or set(branch_receipt_ids) != CANDIDATE_BRANCHES
                or not all(isinstance(value, str) and value for value in branch_receipt_ids.values())
                or len(set(branch_receipt_ids.values())) != len(CANDIDATE_BRANCHES)
            ):
                errors.append("candidate join must bind one exact receipt ID per required branch")
                valid = False

            failed_or_missing: list[str] = []
            if isinstance(branch_receipt_ids, dict):
                for branch in CANDIDATE_BRANCHES:
                    receipt = receipts_by_id.get(branch_receipt_ids.get(branch))
                    if (
                        receipt is None
                        or receipt.get("fork_id") != fork.get("fork_id")
                        or receipt.get("branch_id") != branch
                        or receipt.get("subject_digest") != fork.get("subject_digest")
                        or str(receipt.get("created_at", "")) > str(join.get("created_at", ""))
                    ):
                        failed_or_missing.append(branch)
                        valid = False
                    elif str(receipt.get("result", "")).lower() not in PASS_RESULTS:
                        failed_or_missing.append(branch)
            join_claims_pass = str(join.get("result", "")).lower() in PASS_RESULTS
            if failed_or_missing and join_claims_pass:
                errors.append(
                    "candidate join cannot accept failed or missing branch evidence: "
                    + ", ".join(sorted(failed_or_missing))
                )
            join_passes[str(join_id)] = valid and not failed_or_missing and join_claims_pass

        for transition in transitions:
            if transition.get("from") != "resolve_candidate":
                continue
            join_id = transition.get("join_id")
            if not present(join_id) or join_id not in joins_by_id:
                errors.append("candidate resolution must bind the exact join receipt it used")
                continue
            if not join_passes.get(str(join_id), False) and transition.get("edge_id") not in {
                "candidate_to_repair", "candidate_fatal_to_receipt",
            }:
                errors.append("failed candidate gate cannot be deliberated into completion or release")
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
        or not evidence.get("run_cleanup_receipt")
        or not evidence.get("run_review_receipt")
    ):
        diagnostics.add("terminal_unproven")
    for evidence_id in ("run_receipt", "run_cleanup_receipt", "run_review_receipt"):
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
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="also prove invalid deliberation and cleanup receipts are rejected",
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

    self_test_count = 0
    if args.self_test:
        for key, replay, _ in results:
            if replay.get("deliberations"):
                failures, count = run_deliberation_self_tests(graph, replay)
                errors.extend(f"{key}: {failure}" for failure in failures)
                self_test_count += count
            failures, count = run_cleanup_self_tests(graph, replay)
            errors.extend(f"{key}: {failure}" for failure in failures)
            self_test_count += count

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
    if args.self_test:
        print(f"SELF-TEST: {self_test_count} invalid deliberation or cleanup receipts rejected")
    if args.require_closure and any(diagnostics for _, _, diagnostics in results):
        print("CLOSURE BLOCKED: unresolved run diagnostics")
        return 2
    if isinstance(proposal, dict):
        print(f"PROMOTION: {proposal['promotion_status']}; active graph unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
