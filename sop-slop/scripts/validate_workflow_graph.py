#!/usr/bin/env python3
"""Validate the SOP SLOP workflow graph with Python's standard library."""

from __future__ import annotations

import argparse
import copy
import json
from collections import defaultdict, deque
from pathlib import Path
from typing import Any


GRAPH_PATH = Path(__file__).resolve().parents[1] / "references" / "workflow-graph.json"
EDGE_TYPES = {"advance", "decision", "iteration", "revision", "fork", "join", "complete", "recovery"}
NODE_KINDS = {"outcome", "decision", "fork", "join", "terminal"}


class DuplicateKeyError(ValueError):
    pass


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_graph(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle, object_pairs_hook=_unique_object)


def _indexed(items: Any, label: str, errors: list[str]) -> dict[str, dict[str, Any]]:
    if not isinstance(items, list):
        errors.append(f"{label} must be a list")
        return {}
    result: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(items):
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            errors.append(f"{label}[{index}] must have a string id")
            continue
        item_id = item["id"]
        if item_id in result:
            errors.append(f"duplicate {label} id: {item_id}")
        result[item_id] = item
    return result


def validate(graph: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if graph.get("schema_version") != 1:
        errors.append("schema_version must be 1")

    meta = graph.get("graph")
    policies = graph.get("policies")
    if not isinstance(meta, dict):
        return errors + ["graph metadata must be an object"]
    if not isinstance(policies, dict):
        return errors + ["policies must be an object"]

    nodes = _indexed(graph.get("nodes"), "node", errors)
    edges = _indexed(graph.get("edges"), "edge", errors)
    predicates = _indexed(graph.get("predicates"), "predicate", errors)
    evidence = _indexed(graph.get("evidence_types"), "evidence type", errors)
    specialist_roles = _indexed(graph.get("specialist_roles"), "specialist role", errors)
    deliberation_profiles = _indexed(graph.get("deliberation_profiles"), "deliberation profile", errors)
    dynamic_templates = _indexed(graph.get("dynamic_node_templates"), "dynamic node template", errors)
    dynamic_subgraphs = _indexed(graph.get("dynamic_subgraph_templates"), "dynamic subgraph template", errors)
    predicate_definitions = graph.get("predicate_definitions")
    executor_kinds = set(graph.get("executor_kinds", []))
    terminals = set(meta.get("terminals", []))
    start = meta.get("start")

    if start not in nodes:
        errors.append(f"unknown start node: {start}")
    for terminal in terminals:
        if terminal not in nodes:
            errors.append(f"unknown terminal node: {terminal}")
        elif nodes[terminal].get("kind") != "terminal":
            errors.append(f"terminal {terminal} must have kind terminal")

    for evidence_id, evidence_type in evidence.items():
        fields = evidence_type.get("required_fields")
        if not isinstance(fields, list) or not fields or not all(isinstance(field, str) for field in fields):
            errors.append(f"evidence type {evidence_id} needs required_fields")

    route_fields = set(evidence.get("route_card", {}).get("required_fields", []))
    required_route_fields = {
        "run_id", "graph_version", "lane", "tier", "primary_outcome", "observable_proof", "non_goals", "requested_completion",
        "current_node", "authority_source", "entry_stage", "selected_stages", "skipped_stages", "skip_reasons",
    }
    if not required_route_fields <= route_fields:
        errors.append("route_card must bind the complete mission anchor and route")
    lock_fields = set(evidence.get("alignment_lock_receipt", {}).get("required_fields", []))
    required_lock_fields = {
        "accepted_outcome", "accepted_behavior", "accepted_scope", "non_goals", "authority_boundaries",
        "subject_revision", "actor", "locked_at",
    }
    if not required_lock_fields <= lock_fields:
        errors.append("alignment_lock_receipt must bind accepted alignment to an exact subject revision")
    verification_fields = set(evidence.get("verification_receipt", {}).get("required_fields", []))
    if "receipt_id" not in verification_fields:
        errors.append("verification_receipt must have a stable receipt_id for exact join binding")
    join_fields = set(evidence.get("join_receipt", {}).get("required_fields", []))
    if "branch_receipt_ids" not in join_fields:
        errors.append("join_receipt must bind the exact branch receipt IDs it validated")

    cleanup_policy = policies.get("cleanup")
    if not isinstance(cleanup_policy, dict):
        errors.append("cleanup policy must be an object")
        cleanup_policy = {}
    if cleanup_policy.get("timing") != "after_immutable_delivery_receipt_before_run_review":
        errors.append("cleanup must run after the delivery receipt and before run review")
    if cleanup_policy.get("scope") != "resources_created_or_claimed_by_current_run":
        errors.append("cleanup must be limited to resources created or claimed by the current run")
    if cleanup_policy.get("ownership_binding") != "run_id_and_exact_resolved_target":
        errors.append("cleanup ownership must bind the run id and exact resolved target")
    if set(cleanup_policy.get("classifications", [])) != {
        "release_without_data_deletion", "destructive_cleanup_requires_confirmation", "preserve_with_reason",
    }:
        errors.append("cleanup must classify release, destructive confirmation, or preservation exactly")
    if cleanup_policy.get("destructive_confirmation") != "exact_recoverability_card_plus_explicit_yes_or_do_it":
        errors.append("destructive cleanup must require an exact recoverability card and explicit yes or do it")
    if cleanup_policy.get("confirmation_binding") != "resource_manifest_digest_and_exact_target_list":
        errors.append("cleanup confirmation must bind the manifest digest and exact target list")
    if not {
        "run_owned", "not_primary_workspace", "clean", "no_untracked_files", "commit_pushed",
        "branch_merged_or_disposal_explicitly_confirmed", "no_active_run_lease",
    } <= set(cleanup_policy.get("worktree_removal_requires", [])):
        errors.append("worktree cleanup must prove ownership, cleanliness, remote durability, merge or consent, and no active lease")
    if not {
        "dirty", "untracked", "unpushed", "unmerged", "shared", "canonical", "active_lease",
        "ownership_unknown", "needed_for_resume_or_debug",
    } <= set(cleanup_policy.get("preserve_when", [])):
        errors.append("cleanup must preserve dirty, untracked, unpushed, unmerged, shared, canonical, leased, unknown, or needed resources")
    if not {
        "filesystem_root", "home_root", "workspace_root", "unresolved_environment_variable", "unresolved_glob",
        "shared_cache_without_exact_confirmation",
    } <= set(cleanup_policy.get("forbidden_targets", [])):
        errors.append("cleanup must forbid broad roots, unresolved targets, and unconfirmed shared caches")
    if cleanup_policy.get("retry_budget") != "cleanup_attempts":
        errors.append("cleanup retries must use the cleanup_attempts budget")
    if cleanup_policy.get("closure") != "every_manifest_resource_released_or_preserved_with_reason_and_cleanup_receipt_recorded":
        errors.append("cleanup closure must reconcile every manifest resource")

    manifest_fields = set(evidence.get("run_resource_manifest", {}).get("required_fields", []))
    if not {
        "run_id", "graph_version", "resources", "ownership", "exact_targets", "creation_receipts",
        "disposal_intent", "issuer", "created_at", "updated_at",
    } <= manifest_fields:
        errors.append("run_resource_manifest must bind exact run-owned resources and creation evidence")
    cleanup_fields = set(evidence.get("run_cleanup_receipt", {}).get("required_fields", []))
    if not {
        "run_id", "graph_version", "resource_manifest_digest", "inventory", "classifications", "actions",
        "preserved_resources", "deletion_card", "decision_ref", "result", "verification", "blocker", "actor", "created_at",
    } <= cleanup_fields:
        errors.append("run_cleanup_receipt must bind inventory, decisions, actions, preservation, and verification")
    cleanup_node_id = meta.get("cleanup_node")
    cleanup_node = nodes.get(cleanup_node_id, {})
    if cleanup_node_id != "reconcile_run_resources" or cleanup_node.get("executor") != {
        "kind": "deterministic", "id": "run_resource_reconciler",
    }:
        errors.append("graph cleanup_node must use the deterministic run_resource_reconciler")
    cleanup_completion = cleanup_node.get("completion", {})
    if cleanup_completion.get("predicate") != "run_cleanup_recorded" or set(cleanup_completion.get("evidence", [])) != {
        "run_resource_manifest", "run_cleanup_receipt",
    }:
        errors.append("cleanup node must complete from the typed resource manifest and cleanup receipt")
    cleanup_decision = nodes.get("request_cleanup_authority", {})
    if cleanup_decision.get("kind") != "decision" or cleanup_decision.get("executor") != {
        "kind": "human", "id": "codex_picker",
    }:
        errors.append("destructive cleanup must use one explicit Codex picker decision")
    if "run_cleanup_receipt" not in nodes.get(meta.get("review_node"), {}).get("inputs", []):
        errors.append("run review must evaluate the cleanup receipt")

    required_roles = {"explorer", "implementation_worker", "reviewer", "qa_tester"}
    if set(specialist_roles) != required_roles:
        errors.append("specialist roles must be exactly explorer, implementation_worker, reviewer, and qa_tester")
    role_fields = {
        "purpose",
        "access_mode",
        "default_model_class",
        "default_reasoning_effort",
        "permission_ceiling",
        "stop_condition",
    }
    for role_id, role in specialist_roles.items():
        for field in sorted(role_fields):
            if not isinstance(role.get(field), str) or not role[field].strip():
                errors.append(f"specialist role {role_id} needs {field}")
        if role.get("access_mode") not in {"read_only", "isolated_write", "test_only"}:
            errors.append(f"specialist role {role_id} has invalid access_mode")
        if role.get("default_reasoning_effort") not in {"low", "medium", "high", "xhigh", "max", "ultra"}:
            errors.append(f"specialist role {role_id} has invalid default reasoning effort")
    if specialist_roles.get("implementation_worker", {}).get("access_mode") != "isolated_write":
        errors.append("implementation_worker must use isolated_write access")
    for role_id in {"explorer", "reviewer"}:
        if specialist_roles.get(role_id, {}).get("access_mode") != "read_only":
            errors.append(f"{role_id} must stay read_only")
    if specialist_roles.get("qa_tester", {}).get("access_mode") != "test_only":
        errors.append("qa_tester must stay test_only")

    delegation_policy = policies.get("delegation")
    if not isinstance(delegation_policy, dict):
        errors.append("delegation policy must be an object")
        delegation_policy = {}
    if policies.get("controller") != "single_logical_controller" or delegation_policy.get("transition_authority") != "controller_only":
        errors.append("delegation must preserve controller-only graph transition authority")
    if delegation_policy.get("execution_lifecycle") != "fresh_agent_thread":
        errors.append("delegated executions must be fresh agent threads")
    if set(delegation_policy.get("continuity_sources", [])) != {"canonical_graph_artifacts", "reviewed_shared_memory"}:
        errors.append("delegation continuity must use canonical graph artifacts and reviewed shared memory")
    if set(delegation_policy.get("selection_factors", [])) != {"ambiguity", "risk", "cost", "parallelizability"}:
        errors.append("delegation selection must consider ambiguity, risk, cost, and parallelizability")
    if set(delegation_policy.get("selection_output", [])) != {"role_id", "model", "reasoning_effort"}:
        errors.append("delegation selection must record role, model, and reasoning effort")
    if delegation_policy.get("model_resolution") != "current_available_model_catalog":
        errors.append("delegation models must resolve from the current available catalog")
    if delegation_policy.get("result_handling") != "controller_consolidates_and_validates":
        errors.append("the controller must consolidate and validate delegated evidence")
    if delegation_policy.get("delegation_receipt_completes_node") is not False:
        errors.append("a delegation receipt cannot complete a graph node")
    if delegation_policy.get("parallel_read_review_test") is not True:
        errors.append("parallel read, review, and test delegation must be enabled")
    if delegation_policy.get("parallel_write") != "isolated_disjoint_slice_or_serialized":
        errors.append("parallel writers must use isolated disjoint slices or serialize")
    if delegation_policy.get("persistent_role_config") != "optional_projection_not_private_memory":
        errors.append("persistent role configuration must not imply private durable agent memory")
    if delegation_policy.get("task_states") != ["prepared", "dispatched", "returned", "validated", "rejected"]:
        errors.append("delegation task states must be prepared, dispatched, returned, validated, rejected")

    focus_policy = policies.get("focus")
    if not isinstance(focus_policy, dict):
        errors.append("focus policy must be an object")
        focus_policy = {}
    if set(focus_policy.get("mission_anchor_fields", [])) != {
        "primary_outcome", "observable_proof", "non_goals", "requested_completion", "current_node", "authority_source",
    }:
        errors.append("the mission anchor must bind outcome, proof, focus, completion, node, and authority")
    if focus_policy.get("new_input_classification") != ["continuation_or_dependency", "explicit_replacement", "side_quest"]:
        errors.append("new input must classify as dependency, explicit replacement, or side quest")
    if focus_policy.get("side_quest_action") != "create_linked_codex_task_when_authorized_else_retain_prompt":
        errors.append("side quests must create linked Codex tasks when authorized and otherwise retain a prompt")
    if focus_policy.get("parent_transition") != "resume_same_node" or focus_policy.get("parent_route_change") is not False:
        errors.append("a side quest must resume the same parent node without changing its route")
    if focus_policy.get("side_quest_authority_inheritance") != "none":
        errors.append("side quests must not inherit parent release authority")
    if focus_policy.get("thread_creation_failure") != "retain_prompt_and_resume":
        errors.append("failed side-quest creation must retain the prompt and resume the parent")
    if focus_policy.get("blocking_dependency") != "keep_in_parent_run":
        errors.append("blocking dependencies must remain in the parent run")

    annotation_policy = policies.get("annotation_batch")
    if not isinstance(annotation_policy, dict):
        errors.append("annotation_batch policy must be an object")
        annotation_policy = {}
    if annotation_policy.get("parent_unit") != "one_review_mission":
        errors.append("annotation batches must preserve one parent review mission")
    if annotation_policy.get("atomicize_compound_annotations") is not True:
        errors.append("compound annotations must be atomized before clustering")
    if annotation_policy.get("coverage_rule") != "every_observation_has_exactly_one_primary_problem_or_non_actionable_disposition":
        errors.append("annotation coverage must reconcile every observation")
    if annotation_policy.get("cluster_basis") != "underlying_problem_and_desired_outcome":
        errors.append("annotations must cluster by underlying problem and desired outcome")
    if annotation_policy.get("duplicates") != "supporting_evidence_not_duplicate_work":
        errors.append("duplicate annotations must not create duplicate work")
    if annotation_policy.get("unknown_values") != "record_unknown_never_guess":
        errors.append("unknown annotation facts must never be guessed")
    if annotation_policy.get("clarification") != "inspect_first_then_bounded_grill_me_one_material_question_at_a_time":
        errors.append("annotation clarification must inspect first and ask one material grill question at a time")
    if annotation_policy.get("clarification_scope") != "affected_problem_only_unless_dependency_blocks_batch":
        errors.append("annotation ambiguity must block only the affected problem unless it is a dependency")
    if annotation_policy.get("clear_problem_action") != "start_without_reconfirmation":
        errors.append("clear annotation problems must start without reconfirmation")
    if annotation_policy.get("task_bridge") != "one_idempotent_durable_task_per_accepted_problem_in_canonical_general_task_list":
        errors.append("each accepted annotation problem must have one idempotent canonical task")
    if annotation_policy.get("task_deduplication") != "reuse_equivalent_canonical_task":
        errors.append("the annotation task bridge must reuse equivalent canonical tasks")
    if annotation_policy.get("task_status_sync") != ["ready", "in_progress", "completed", "blocked", "failed"]:
        errors.append("annotation task statuses must stay synchronized through the closed status set")
    if annotation_policy.get("missing_task_ssot_or_authority") != "block_before_execution":
        errors.append("annotation execution must block when the canonical task list or authority is missing")
    if annotation_policy.get("execution") != "one_sequential_linked_child_run_per_ready_problem":
        errors.append("annotation problems must execute as sequential linked child runs")
    if annotation_policy.get("child_input") != "one_ledger_problem_reference_not_the_annotation_batch":
        errors.append("annotation child runs must receive one ledger problem rather than recurse on the full batch")
    if annotation_policy.get("write_concurrency") != "one_active_problem_writer":
        errors.append("annotation batches must allow only one active problem writer")
    if annotation_policy.get("completion") != "all_annotations_covered_and_all_accepted_problems_have_validated_terminal_receipts":
        errors.append("annotation batch completion must require coverage and validated problem receipts")

    deliberation_policy = policies.get("deliberation")
    if not isinstance(deliberation_policy, dict):
        errors.append("deliberation policy must be an object")
        deliberation_policy = {}
    if deliberation_policy.get("mode") != "optional_bounded_peer_discussion":
        errors.append("deliberation must stay optional and bounded")
    if deliberation_policy.get("usage_guard") != "material_competing_judgment_unresolved_by_repository_evidence_or_established_pattern" or deliberation_policy.get("routine_action") != "skip":
        errors.append("routine or evidence-resolved work must skip deliberation")
    if deliberation_policy.get("template") != "bounded_peer_deliberation" or deliberation_policy.get("profile_registry") != "closed_and_versioned":
        errors.append("deliberation must use one reusable template and a closed versioned profile registry")
    if deliberation_policy.get("role_id") != "reviewer":
        errors.append("deliberation must reuse the existing reviewer role")
    if deliberation_policy.get("specialist_model") != "gpt-5.6-luna":
        errors.append("every deliberation specialist execution must use gpt-5.6-luna")
    if deliberation_policy.get("specialist_reasoning_effort") != "max":
        errors.append("every deliberation specialist execution must use max reasoning effort")
    if deliberation_policy.get("shared_input") != "frozen_deliberation_request" or deliberation_policy.get("first_round") != "independent_observation_no_final_proposal":
        errors.append("deliberation must freeze one shared request before independent observation")
    if deliberation_policy.get("peer_exchange") != "lossless_broadcast_and_named_follow_up":
        errors.append("deliberation peers must receive lossless statements and named follow-up turns")
    if deliberation_policy.get("contribution_fields") != [
        "CLAIM", "WHY", "EVIDENCE", "QUESTION_FOR", "OBJECTION", "CHANGE_MY_MIND_IF",
    ]:
        errors.append("deliberation contributions must use the complete typed peer schema")
    if deliberation_policy.get("max_discussion_rounds") != 2 or deliberation_policy.get("contributions_per_specialist_per_round") != {"min": 1, "max": 2}:
        errors.append("deliberation must be limited to two rounds and one or two contributions per specialist")
    if deliberation_policy.get("max_evidence_or_experiment_cycles") != 1 or deliberation_policy.get("max_material_human_decisions") != 1:
        errors.append("deliberation evidence and human resolution must each be limited to one cycle")
    if deliberation_policy.get("decision_rule") != "requirements_and_evidence_not_majority_vote":
        errors.append("deliberation must never use majority vote")
    if deliberation_policy.get("valid_objection") != "violated_requirement_or_missing_evidence_not_taste_alone":
        errors.append("deliberation objections must cite a requirement or missing evidence")
    if deliberation_policy.get("factual_uncertainty") != "inspection_prototype_or_experiment_not_more_debate":
        errors.append("factual disagreement must route to evidence rather than more debate")
    if deliberation_policy.get("subjective_choice") != "one_codex_picker_question":
        errors.append("irreducibly subjective deliberation choices must use one Codex picker question")
    if deliberation_policy.get("round_exhaustion") != "cheapest_reversible_experiment_or_block_with_dissent":
        errors.append("deliberation round exhaustion must experiment cheaply or block with dissent")
    if deliberation_policy.get("hard_invariants") != "immutable_and_not_debatable" or deliberation_policy.get("release_gate_override") is not False:
        errors.append("deliberation cannot waive hard, release, authority, or verification guards")
    if deliberation_policy.get("mission_anchor") != "preserved" or deliberation_policy.get("transition_authority") != "controller_only":
        errors.append("deliberation must preserve the mission while the controller alone owns transitions")
    if deliberation_policy.get("return_contract") != "exact_invoking_run_mission_node_input_digest_and_profile_version":
        errors.append("deliberation must bind and return to the exact invoking run, mission, node, input, and profile version")
    if deliberation_policy.get("canonical_state") != "typed_deliberation_artifacts":
        errors.append("deliberation state must be preserved in canonical typed artifacts")
    if deliberation_policy.get("upstream_change") != "invalidate_affected_artifacts_and_return_to_owning_stage_normally":
        errors.append("deliberation changes must invalidate upstream artifacts through normal graph ownership")
    if deliberation_policy.get("post_acceptance_write") != "one_serialized_implementation_writer":
        errors.append("deliberation acceptance must still allow only one implementation writer")
    if deliberation_policy.get("parallel_post_acceptance") != "read_only_review_and_qa_against_frozen_inputs":
        errors.append("parallel post-deliberation review and QA must stay read-only on frozen inputs")

    autonomy_policy = policies.get("autonomy")
    if not isinstance(autonomy_policy, dict):
        errors.append("autonomy policy must be an object")
        autonomy_policy = {}
    if autonomy_policy.get("alignment_lock") != "accepted_outcome_behavior_scope_non_goals_and_authority":
        errors.append("alignment lock must bind accepted outcome, behavior, scope, non-goals, and authority")
    if autonomy_policy.get("post_alignment_reversible_decisions") != "controller_auto_decides":
        errors.append("the controller must auto-decide reversible choices after alignment")
    if set(autonomy_policy.get("auto_decision_classes", [])) != {
        "technical", "dependency", "test_layer", "implementation", "formatting", "version_tier", "routine_release_mechanics",
    }:
        errors.append("post-alignment auto-decision classes are incomplete")
    if set(autonomy_policy.get("human_question_classes", [])) != {
        "locked_behavior_or_scope_change", "authority_security_tenant_or_data_expansion", "destructive_or_hard_to_reverse",
        "meaningful_spend_or_external_communication", "production_target_change",
    }:
        errors.append("post-alignment human questions must stay inside material decision classes")
    if autonomy_policy.get("question_requires_blocked_completion_predicate") is not True:
        errors.append("every human question must name a blocked completion predicate")
    if set(autonomy_policy.get("forbidden_reconfirmations", [])) != {"continue", "recommended_approach", "version", "ship", "merge_and_deploy"}:
        errors.append("continue, recommendation, version, ship, and deploy reconfirmations must be forbidden")

    release_policy = policies.get("release")
    if not isinstance(release_policy, dict):
        errors.append("release policy must be an object")
        release_policy = {}
    if release_policy.get("explicit_implementation_through_production_requested_completion") != "production_verified":
        errors.append("explicit implementation-through-production runs must target verified production")
    if release_policy.get("without_release_authority") != "respect_requested_completion":
        errors.append("runs without release authority must respect the requested completion target")
    if set(release_policy.get("invocation_authority", [])) != {
        "commit", "push", "open_pr", "merge", "deploy", "verify_production", "documented_bounded_recovery",
    }:
        errors.append("an explicit implementation-through-production request must bind the complete routine release authority")
    if release_policy.get("reconfirm_bound_authority") is not False:
        errors.append("bound release authority must not be reconfirmed")
    if release_policy.get("version_tier") != "controller_auto_decides":
        errors.append("the controller must auto-decide the version tier")
    if release_policy.get("nested_skill_final") != "executor_return_not_outer_terminal":
        errors.append("nested skill finals must return to the outer controller")
    required_safety_stops = {
        "repository_rule_conflict", "destructive_or_hard_to_reverse", "authority_or_security_expansion", "missing_credential",
        "version_queue_conflict_or_manual_drift", "merge_conflict", "failed_required_check", "unhealthy_deployment",
    }
    if not required_safety_stops <= set(release_policy.get("safety_stops", [])):
        errors.append("release policy must preserve repository, authority, data, credential, conflict, check, and health stops")

    for node_id in ("align_strategy", "align_product"):
        completion = nodes.get(node_id, {}).get("completion", {})
        if completion.get("predicate") != "alignment_locked" or set(completion.get("evidence", [])) != {"artifact_receipt", "alignment_lock_receipt"}:
            errors.append(f"{node_id} must complete from a typed alignment lock bound to its artifact")

    policy_traces_raw = graph.get("policy_trace_scenarios")
    if not isinstance(policy_traces_raw, list):
        errors.append("policy_trace_scenarios must be a list")
        policy_traces_raw = []
    policy_traces = {
        item.get("id"): item
        for item in policy_traces_raw
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    required_policy_assertions = {
        "deliberation_preserves_peer_discussion_and_caller": {
            "closed_profile_registry", "same_subgraph_for_distinct_callers",
            "reviewer_role_reused_with_profile_lenses", "every_specialist_execution_uses_luna_max",
            "all_specialists_share_one_frozen_request", "first_round_has_no_final_proposal",
            "peers_receive_and_respond_to_each_other", "typed_contributions_are_auditable",
            "no_majority_vote", "valid_objections_route_to_revision_evidence_or_user",
            "two_round_budget", "one_evidence_cycle_budget", "one_material_human_decision_budget",
            "dissent_preserved", "controller_alone_advances", "exact_mission_caller_and_input_binding",
            "hard_guards_not_debatable", "one_writer_after_acceptance",
        },
        "annotation_batch_preserves_coverage_and_tasks": {
            "every_annotation_covered", "duplicates_do_not_create_tasks", "unknown_values_not_guessed",
            "one_canonical_task_per_problem", "clear_problems_start_without_reconfirmation",
            "ambiguous_problem_only_is_paused", "task_status_requires_validated_child_receipt",
            "parent_waits_for_all_problem_receipts",
        },
        "side_quest_preserves_parent": {
            "classifies_side_quest", "creates_linked_codex_task", "parent_route_unchanged", "parent_resumes_same_node", "no_authority_inheritance",
        },
        "side_quest_without_creation_authority": {
            "classifies_side_quest", "retains_ready_to_send_prompt", "parent_route_unchanged", "parent_resumes_same_node", "no_external_action",
        },
        "aligned_release_autonomy": {
            "nested_final_returns_to_controller", "controller_selects_version", "no_release_reconfirmation",
            "production_verified_before_close", "cleanup_before_review", "run_review_before_terminal",
        },
        "run_cleanup_is_bounded_and_loss_safe": {
            "current_run_scope_only", "exact_resolved_targets_only",
            "dirty_untracked_unpushed_unmerged_shared_and_unknown_resources_preserved",
            "broad_roots_and_globs_forbidden", "destructive_cleanup_requires_digest_bound_explicit_yes",
            "empty_or_prior_consent_rejected", "worktree_removal_proves_clean_pushed_merged_and_unleased",
            "every_manifest_resource_has_disposition", "cleanup_retry_bounded", "cleanup_before_review",
        },
    }
    if set(policy_traces) != set(required_policy_assertions):
        errors.append("policy traces must cover deliberation, annotation batches, side quests, release autonomy, and bounded cleanup")
    for trace_id, required_assertions in required_policy_assertions.items():
        trace = policy_traces.get(trace_id, {})
        if not isinstance(trace.get("events"), list) or not trace.get("events"):
            errors.append(f"policy trace {trace_id} needs events")
        if not required_assertions <= set(trace.get("assertions", [])):
            errors.append(f"policy trace {trace_id} is missing required assertions")

    delegation_receipt = evidence.get("delegation_receipt", {})
    delegation_fields = set(delegation_receipt.get("required_fields", [])) if isinstance(delegation_receipt, dict) else set()
    required_delegation_fields = {
        "delegation_id", "execution_id", "parent_run_id", "graph_version", "node_id", "role_id",
        "model", "reasoning_effort", "ownership_scope", "allowed_tools", "permissions", "input_refs",
        "expected_output", "verification_criteria", "stop_condition", "isolation", "result", "evidence_refs",
        "controller_validation", "issuer", "created_at",
    }
    if not required_delegation_fields <= delegation_fields:
        errors.append("delegation_receipt must bind the bounded task, selected runtime, result, evidence, and controller validation")

    required_deliberation_evidence_fields = {
        "deliberation_request": {
            "request_id", "invoking_run_id", "mission_anchor_digest", "invoking_node_id", "decision_question", "deliberation_reason",
            "profile_id", "profile_version", "frozen_input_refs", "input_digest", "participant_roster",
            "specialist_lenses", "model", "reasoning_effort", "acceptance_criteria", "hard_invariants",
            "round_budget", "contribution_budget", "authority_envelope_ref", "expected_return_evidence",
            "return_node_id", "return_contract", "issuer", "created_at",
        },
        "deliberation_round": {
            "request_id", "invoking_run_id", "invoking_node_id", "input_digest", "profile_id", "profile_version",
            "round_number", "phase", "participant_roster", "delegation_envelopes", "delegation_receipts",
            "contributions", "broadcasts", "named_questions", "responses", "objections", "position_changes",
            "controller_validation", "created_at",
        },
        "deliberation_joint_proposal": {
            "request_id", "input_digest", "profile_id", "profile_version", "round_number", "owner_lens",
            "owner_delegation_envelope", "owner_delegation_receipt", "proposal_digest", "proposal", "acceptance_mapping",
            "hard_invariant_check", "evidence_refs", "retained_concerns", "created_at",
        },
        "deliberation_consent_receipt": {
            "request_id", "proposal_digest", "profile_id", "profile_version", "specialist_responses",
            "allowed_values", "objections", "concerns", "delegation_envelopes", "delegation_receipts", "created_at",
        },
        "deliberation_return_receipt": {
            "request_id", "invoking_run_id", "mission_anchor_digest", "invoking_node_id", "input_digest", "profile_id", "profile_version",
            "accepted_proposal_ref", "disposition", "controller_validation", "dissent", "hard_invariant_check",
            "invalidated_artifacts", "evidence_refs", "return_node_id", "returned_at",
        },
    }
    for evidence_id, required_fields in required_deliberation_evidence_fields.items():
        actual_fields = set(evidence.get(evidence_id, {}).get("required_fields", []))
        if not required_fields <= actual_fields:
            errors.append(f"{evidence_id} is missing required deliberation fields")

    annotation_ledger_fields = set(evidence.get("annotation_problem_ledger", {}).get("required_fields", []))
    required_annotation_ledger_fields = {
        "batch_id", "primary_mission", "source_revision", "annotation_ids", "annotation_count",
        "observation_records", "problem_clusters", "coverage_map", "clarification_queue", "execution_order",
        "task_refs", "status_counts", "issuer", "created_at", "updated_at",
    }
    if not required_annotation_ledger_fields <= annotation_ledger_fields:
        errors.append("annotation_problem_ledger must preserve coverage, grouping, clarification, tasks, order, and status")
    annotation_task_fields = set(evidence.get("annotation_task_receipt", {}).get("required_fields", []))
    required_annotation_task_fields = {
        "batch_id", "problem_id", "task_system", "task_id", "canonical_uri", "idempotency_key",
        "action", "previous_status", "new_status", "evidence_refs", "actor", "created_at",
    }
    if not required_annotation_task_fields <= annotation_task_fields:
        errors.append("annotation_task_receipt must bind one idempotent canonical task and its status evidence")
    annotation_run_fields = set(evidence.get("annotation_problem_run_receipt", {}).get("required_fields", []))
    required_annotation_run_fields = {
        "batch_id", "problem_id", "annotation_ids", "child_run_id", "route", "requested_completion",
        "status", "evidence_refs", "controller_validation", "closed_at",
    }
    if not required_annotation_run_fields <= annotation_run_fields:
        errors.append("annotation_problem_run_receipt must bind one problem to a validated child run")

    if not isinstance(predicate_definitions, dict):
        errors.append("predicate_definitions must be an object")
        predicate_definitions = {}
    for predicate_id in predicates:
        definition = predicate_definitions.get(predicate_id)
        if not isinstance(definition, str) or not definition.strip():
            errors.append(f"predicate {predicate_id} needs a truth-condition definition")
    for predicate_id in sorted(set(predicate_definitions) - set(predicates)):
        errors.append(f"definition exists for unknown predicate: {predicate_id}")

    outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)
    incoming: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for edge_id, edge in edges.items():
        source, target, guard = edge.get("from"), edge.get("to"), edge.get("guard")
        if source not in nodes:
            errors.append(f"edge {edge_id} has unknown source: {source}")
        else:
            outgoing[source].append(edge)
        if target not in nodes:
            errors.append(f"edge {edge_id} has unknown target: {target}")
        else:
            incoming[target].append(edge)
        if guard not in predicates or predicates.get(guard, {}).get("kind") != "guard":
            errors.append(f"edge {edge_id} has unknown guard predicate: {guard}")
        edge_type = edge.get("type")
        if edge_type not in EDGE_TYPES:
            errors.append(f"edge {edge_id} has invalid type: {edge_type}")
        if edge_type in {"iteration", "revision", "recovery"} and not edge.get("budget"):
            errors.append(f"bounded edge {edge_id} needs a budget")

    outcome_tables_raw = graph.get("outcome_tables")
    outcome_tables: dict[str, dict[str, Any]] = {}
    if not isinstance(outcome_tables_raw, list):
        errors.append("outcome_tables must be a list")
        outcome_tables_raw = []
    for index, table in enumerate(outcome_tables_raw):
        if not isinstance(table, dict) or not isinstance(table.get("node"), str):
            errors.append(f"outcome_tables[{index}] must name a node")
            continue
        node_id = table["node"]
        if node_id in outcome_tables:
            errors.append(f"duplicate outcome table for node: {node_id}")
        outcome_tables[node_id] = table

    branching_nodes = {
        node_id
        for node_id, node in nodes.items()
        if node.get("kind") != "fork" and len(outgoing[node_id]) > 1
    }
    for node_id in sorted(branching_nodes - set(outcome_tables)):
        errors.append(f"branching node {node_id} needs an outcome table")
    for node_id in sorted(set(outcome_tables) - branching_nodes):
        errors.append(f"outcome table exists for non-branching node: {node_id}")

    for node_id, table in outcome_tables.items():
        if node_id not in branching_nodes:
            continue
        if not isinstance(table.get("partition"), str) or not table["partition"].strip():
            errors.append(f"outcome table {node_id} needs a partition")
        selection = table.get("selection")
        if selection not in {"exactly_one", "exactly_one_after_answer"}:
            errors.append(f"outcome table {node_id} has invalid selection: {selection}")
        if selection == "exactly_one_after_answer" and nodes[node_id].get("kind") != "decision":
            errors.append(f"outcome table {node_id} may wait for an answer only on a decision node")
        table_evidence = table.get("evidence")
        if not isinstance(table_evidence, list) or not table_evidence:
            errors.append(f"outcome table {node_id} needs classification evidence")

        domain = table.get("domain")
        if not isinstance(domain, list) or not domain or not all(isinstance(value, str) for value in domain):
            errors.append(f"outcome table {node_id} needs a string domain")
            domain = []
        if len(domain) != len(set(domain)):
            errors.append(f"outcome table {node_id} has duplicate domain values")

        cases = table.get("cases")
        if not isinstance(cases, list):
            errors.append(f"outcome table {node_id} cases must be a list")
            cases = []
        values: list[str] = []
        case_edges: list[str] = []
        for case_index, case in enumerate(cases):
            if not isinstance(case, dict):
                errors.append(f"outcome table {node_id} case {case_index} must be an object")
                continue
            value, edge_id, guard = case.get("value"), case.get("edge"), case.get("guard")
            if not isinstance(value, str):
                errors.append(f"outcome table {node_id} case {case_index} needs a value")
                continue
            values.append(value)
            if not isinstance(edge_id, str):
                errors.append(f"outcome table {node_id} case {value} needs an edge")
                continue
            case_edges.append(edge_id)
            edge = edges.get(edge_id)
            if edge is None or edge.get("from") != node_id:
                errors.append(f"outcome table {node_id} case {value} has invalid edge: {edge_id}")
            elif edge.get("guard") != guard:
                errors.append(f"outcome table {node_id} case {value} guard does not match edge {edge_id}")
        if len(values) != len(set(values)):
            errors.append(f"outcome table {node_id} has duplicate outcome values")
        if set(values) != set(domain) or len(values) != len(domain):
            errors.append(f"outcome table {node_id} cases must cover its domain exactly")
        outgoing_ids = {edge["id"] for edge in outgoing[node_id]}
        if set(case_edges) != outgoing_ids or len(case_edges) != len(outgoing_ids):
            errors.append(f"outcome table {node_id} cases must cover its outgoing edges exactly")

    traces_raw = graph.get("trace_scenarios")
    trace_ids: set[str] = set()
    if not isinstance(traces_raw, list) or not traces_raw:
        errors.append("trace_scenarios must be a non-empty list")
        traces_raw = []
    for index, trace in enumerate(traces_raw):
        if not isinstance(trace, dict) or not isinstance(trace.get("id"), str):
            errors.append(f"trace_scenarios[{index}] must have an id")
            continue
        trace_id = trace["id"]
        if trace_id in trace_ids:
            errors.append(f"duplicate trace scenario id: {trace_id}")
        trace_ids.add(trace_id)
        current = trace.get("start")
        if current not in nodes:
            errors.append(f"trace {trace_id} has unknown start node: {current}")
            continue
        steps = trace.get("steps")
        if not isinstance(steps, list) or not steps:
            errors.append(f"trace {trace_id} needs steps")
            continue
        for step_index, step in enumerate(steps):
            if not isinstance(step, dict):
                errors.append(f"trace {trace_id} step {step_index} must be an object")
                continue
            if step.get("node") != current:
                errors.append(f"trace {trace_id} step {step_index} expected node {current}")
                break
            edge_id = step.get("edge")
            edge = edges.get(edge_id)
            if edge is None or edge.get("from") != current:
                errors.append(f"trace {trace_id} step {step_index} has invalid edge: {edge_id}")
                break
            table = outcome_tables.get(current)
            if table is not None:
                outcome = step.get("outcome")
                matching = [case for case in table.get("cases", []) if isinstance(case, dict) and case.get("value") == outcome]
                if len(matching) != 1 or matching[0].get("edge") != edge_id:
                    errors.append(f"trace {trace_id} step {step_index} does not match outcome table {current}")
                    break
            current = edge.get("to")
        if trace.get("ends_at") != current:
            errors.append(f"trace {trace_id} ends at {current}, not {trace.get('ends_at')}")

    required_traces = {
        "annotation_batch_groups_and_executes_problems",
        "annotation_problem_uses_bounded_clarification",
        "material_route_decision",
        "failed_candidate_repairs",
        "missing_release_authority_blocks_before_action",
        "compound_production_release",
        "confirmed_late_invariant_breach_fails",
        "destructive_cleanup_requires_exact_confirmation",
    }
    for trace_id in sorted(required_traces - trace_ids):
        errors.append(f"missing required trace scenario: {trace_id}")
    authority_trace = next((trace for trace in traces_raw if isinstance(trace, dict) and trace.get("id") == "missing_release_authority_blocks_before_action"), None)
    if authority_trace is not None:
        visited = [step.get("node") for step in authority_trace.get("steps", []) if isinstance(step, dict)]
        if "ship_change" in visited or "land_and_deploy_change" in visited:
            errors.append("missing-authority trace must not invoke a compound release executor")

    for node_id, node in nodes.items():
        kind = node.get("kind")
        if kind not in NODE_KINDS:
            errors.append(f"node {node_id} has invalid kind: {kind}")
        executor = node.get("executor")
        if not isinstance(executor, dict) or executor.get("kind") not in executor_kinds or not executor.get("id"):
            errors.append(f"node {node_id} has an invalid executor")
        if not isinstance(node.get("inputs"), list):
            errors.append(f"node {node_id} must declare inputs")
        if not isinstance(node.get("outcome"), str) or not node["outcome"].strip():
            errors.append(f"node {node_id} must declare an outcome")
        if not isinstance(node.get("invalidated_by"), list):
            errors.append(f"node {node_id} must declare invalidation dependencies")

        completion = node.get("completion")
        if not isinstance(completion, dict):
            errors.append(f"node {node_id} must declare completion")
            completion = {}
        else:
            predicate = completion.get("predicate")
            if predicate not in predicates or predicates.get(predicate, {}).get("kind") != "completion":
                errors.append(f"node {node_id} has unknown completion predicate: {predicate}")
            for evidence_id in completion.get("evidence", []):
                if evidence_id not in evidence:
                    errors.append(f"node {node_id} has unknown completion evidence: {evidence_id}")
            if "delegation_receipt" in completion.get("evidence", []):
                errors.append(f"node {node_id} cannot complete from a delegation receipt")

        delegation = node.get("delegation")
        if delegation is not None:
            if not isinstance(delegation, dict):
                errors.append(f"node {node_id} delegation must be an object")
                delegation = {}
            if kind != "outcome":
                errors.append(f"node {node_id} delegation is allowed only on outcome nodes")
            if delegation.get("mode") not in {"assist", "execute"}:
                errors.append(f"node {node_id} delegation has invalid mode")
            allowed_role_ids = delegation.get("allowed_roles")
            if not isinstance(allowed_role_ids, list) or not allowed_role_ids:
                errors.append(f"node {node_id} delegation needs allowed_roles")
                allowed_role_ids = []
            for role_id in allowed_role_ids:
                if role_id not in specialist_roles:
                    errors.append(f"node {node_id} delegation names unknown specialist role: {role_id}")
            parallelism = delegation.get("parallelism")
            if parallelism not in {"read_only", "explicit_fork_branch", "serialized"}:
                errors.append(f"node {node_id} delegation has invalid parallelism")
            write_policy = delegation.get("write_policy")
            if write_policy not in {"none", "test_artifacts_only", "isolated_workspace_or_serialized"}:
                errors.append(f"node {node_id} delegation has invalid write_policy")
            for role_id in allowed_role_ids:
                access_mode = specialist_roles.get(role_id, {}).get("access_mode")
                if access_mode == "read_only" and write_policy != "none":
                    errors.append(f"read-only specialist {role_id} cannot receive writes at node {node_id}")
                if access_mode == "isolated_write" and (
                    write_policy != "isolated_workspace_or_serialized"
                    or parallelism != "serialized"
                ):
                    errors.append(f"implementation delegation at {node_id} must require isolation or serialization")
                if access_mode == "test_only" and write_policy != "test_artifacts_only":
                    errors.append(f"QA delegation at {node_id} must be limited to test artifacts")
            if parallelism == "explicit_fork_branch" and not any(edge.get("type") == "fork" for edge in incoming[node_id]):
                errors.append(f"node {node_id} claims explicit-fork delegation but is not a fork branch")

        if kind == "decision" and "decision_receipt" not in (completion or {}).get("evidence", []):
            errors.append(f"decision node {node_id} must require decision_receipt")
        if node_id in terminals:
            if outgoing[node_id]:
                errors.append(f"terminal {node_id} must not have outgoing edges")
            if "run_review_receipt" not in (completion or {}).get("evidence", []):
                errors.append(f"terminal {node_id} must require run_review_receipt")
            if "run_cleanup_receipt" not in (completion or {}).get("evidence", []):
                errors.append(f"terminal {node_id} must require run_cleanup_receipt")
        elif not outgoing[node_id]:
            errors.append(f"non-terminal node {node_id} has no outgoing edge")
        if (completion or {}).get("predicate") == "external_action_recorded":
            if any(edge.get("guard") == "stage_completed" for edge in outgoing[node_id]):
                errors.append(f"external action node {node_id} must not advance on generic stage_completed")

    required_delegation_roles = {
        "map_program": {"explorer"},
        "review_engineering": {"explorer", "reviewer"},
        "deliver_slice": {"implementation_worker"},
        "repair_candidate": {"implementation_worker"},
        "review_candidate": {"reviewer"},
        "exercise_candidate": {"qa_tester"},
        "run_required_checks": {"qa_tester"},
        "review_run": {"reviewer"},
    }
    for node_id, required_role_ids in required_delegation_roles.items():
        configured = nodes.get(node_id, {}).get("delegation", {})
        actual_role_ids = set(configured.get("allowed_roles", [])) if isinstance(configured, dict) else set()
        if not required_role_ids <= actual_role_ids:
            errors.append(f"node {node_id} is missing required delegation roles: {sorted(required_role_ids - actual_role_ids)}")

    annotation_nodes = {
        "structure_annotation_batch",
        "materialize_annotation_tasks",
        "select_next_annotation_problem",
        "clarify_annotation_problem",
        "execute_annotation_problem",
    }
    if not annotation_nodes <= set(nodes):
        errors.append("annotation batch lifecycle nodes are incomplete")
    if nodes.get("structure_annotation_batch", {}).get("completion", {}) != {
        "predicate": "annotation_problem_ledger_recorded",
        "evidence": ["annotation_problem_ledger"],
    }:
        errors.append("structure_annotation_batch must complete from the reconciled problem ledger")
    task_bridge = nodes.get("materialize_annotation_tasks", {})
    if task_bridge.get("completion", {}).get("predicate") != "annotation_task_bridge_recorded":
        errors.append("materialize_annotation_tasks must complete from canonical task receipts")
    if "authority_envelope" not in task_bridge.get("inputs", []) or "annotation_task_receipt" not in task_bridge.get("completion", {}).get("evidence", []):
        errors.append("the annotation task bridge must require authority and retain task receipts")
    problem_execution = nodes.get("execute_annotation_problem", {})
    if problem_execution.get("completion", {}).get("predicate") != "annotation_problem_run_recorded":
        errors.append("execute_annotation_problem must complete from a validated child run")
    if set(problem_execution.get("completion", {}).get("evidence", [])) != {
        "annotation_problem_ledger", "annotation_problem_run_receipt", "annotation_task_receipt",
    }:
        errors.append("annotation problem completion must synchronize ledger, child receipt, and durable task")
    annotation_iteration = edges.get("annotation_problem_to_selector", {})
    if annotation_iteration.get("type") != "iteration" or annotation_iteration.get("budget") != "annotation_problem_queue":
        errors.append("annotation problem execution must return through the bounded sequential queue")
    clarification_iteration = edges.get("annotation_clarification_to_selector", {})
    if clarification_iteration.get("type") != "iteration" or clarification_iteration.get("budget") != "annotation_clarification":
        errors.append("annotation clarification must return through a bounded decision loop")
    clarification_node = nodes.get("clarify_annotation_problem", {})
    if clarification_node.get("executor") != {"kind": "skill", "id": "grill-me"}:
        errors.append("annotation clarification must use the bounded grill-me executor")
    if clarification_node.get("completion", {}).get("predicate") != "annotation_problem_clarification_recorded":
        errors.append("annotation clarification must update the affected problem and durable task from decision evidence")
    decision_hosts = set(dynamic_templates.get("prebuild_material_decision", {}).get("allowed_hosts", []))
    if not {"structure_annotation_batch", "clarify_annotation_problem"} <= decision_hosts:
        errors.append("annotation intake and clarification must host bounded material decisions")

    required_profile_ids = {
        "design", "product_domain", "specification", "engineering", "review_adjudication", "qa_triage",
        "learning_retro",
    }
    if set(deliberation_profiles) != required_profile_ids:
        errors.append("the deliberation profile registry must contain exactly the seven justified profiles")
    profile_callers: set[str] = set()
    for profile_id, profile in deliberation_profiles.items():
        if not isinstance(profile.get("version"), str) or not profile["version"].strip():
            errors.append(f"deliberation profile {profile_id} needs a version")
        for field in ("purpose", "acceptance_focus"):
            if not profile.get(field):
                errors.append(f"deliberation profile {profile_id} needs {field}")
        lenses = profile.get("lenses")
        if not isinstance(lenses, list) or len(lenses) != 3 or len(set(lenses)) != 3:
            errors.append(f"deliberation profile {profile_id} must define exactly three distinct lenses")
        callers = profile.get("eligible_callers")
        if not isinstance(callers, list) or not callers:
            errors.append(f"deliberation profile {profile_id} needs eligible callers")
            callers = []
        for caller in callers:
            if caller not in nodes:
                errors.append(f"deliberation profile {profile_id} names unknown caller: {caller}")
            profile_callers.add(caller)

    if set(dynamic_subgraphs) != {"bounded_peer_deliberation"}:
        errors.append("the graph must expose one reusable bounded_peer_deliberation subgraph")
    deliberation = dynamic_subgraphs.get("bounded_peer_deliberation", {})
    if deliberation.get("kind") != "call_return_subgraph" or deliberation.get("profile_registry_ref") != "deliberation_profiles":
        errors.append("bounded_peer_deliberation must use the profile registry through a call-return contract")
    allowed_hosts = set(deliberation.get("allowed_hosts", []))
    if allowed_hosts != profile_callers:
        errors.append("deliberation allowed hosts must equal the closed profile caller registry")
    if {"run_required_checks", "prepare_release", "ship_change", "land_and_deploy_change"} & allowed_hosts:
        errors.append("routine checks and release executors must not invoke deliberation")
    invocation = deliberation.get("invocation", {})
    if invocation != {
        "guard": "material_competing_judgment_unresolved",
        "request_evidence": "deliberation_request",
        "suspend_invoking_node": True,
        "max_active_per_invoking_node": 1,
    }:
        errors.append("deliberation invocation must freeze one request and suspend exactly one eligible caller")
    if deliberation.get("executor") != {"kind": "controller", "id": "deliberation_controller"}:
        errors.append("the controller must own the reusable deliberation subgraph")
    specialist_execution = deliberation.get("specialist_execution", {})
    if specialist_execution != {
        "role_id": "reviewer", "model": "gpt-5.6-luna", "reasoning_effort": "max",
        "fresh_thread": True, "envelope_and_receipt_required": True,
    }:
        errors.append("every deliberation specialist execution must be a fresh Luna/max reviewer with envelope and receipt")

    subnodes = _indexed(deliberation.get("nodes"), "deliberation node", errors)
    subedges = _indexed(deliberation.get("edges"), "deliberation edge", errors)
    required_subnodes = {
        "prepare_deliberation", "observe_independently", "discuss_with_peers", "draft_joint_proposal",
        "check_deliberation_consent", "validate_deliberation", "resolve_deliberation_evidence",
        "ask_material_human_decision", "return_to_invoking_node",
    }
    if set(subnodes) != required_subnodes:
        errors.append("the reusable deliberation subgraph lifecycle is incomplete or duplicated")
    if set(nodes) & set(subnodes):
        errors.append("deliberation internal nodes must not be copied into the parent lifecycle")
    sub_outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)
    allowed_subedge_types = {"advance", "decision", "revision", "recovery", "return"}
    for edge_id, edge in subedges.items():
        if edge.get("from") not in subnodes or edge.get("to") not in subnodes:
            errors.append(f"deliberation edge {edge_id} must stay inside the subgraph")
        else:
            sub_outgoing[edge["from"]].append(edge)
        if edge.get("type") not in allowed_subedge_types:
            errors.append(f"deliberation edge {edge_id} has invalid type")
        if edge.get("type") in {"revision", "recovery"} and not edge.get("budget"):
            errors.append(f"deliberation edge {edge_id} needs a budget")
    if sub_outgoing.get("return_to_invoking_node"):
        errors.append("the deliberation return node must not select a parent downstream edge")
    for node_id in ("observe_independently", "discuss_with_peers", "draft_joint_proposal", "check_deliberation_consent"):
        delegation = subnodes.get(node_id, {}).get("delegation", {})
        if delegation.get("role_id") != "reviewer" or delegation.get("required_model") != "gpt-5.6-luna" or delegation.get("required_reasoning_effort") != "max":
            errors.append(f"deliberation node {node_id} must use the Luna/max reviewer role")
        if delegation.get("parallelism") != "read_only" or delegation.get("write_policy") != "none":
            errors.append(f"deliberation node {node_id} must stay read-only")
    evidence_node = subnodes.get("resolve_deliberation_evidence", {}).get("delegation", {})
    if set(evidence_node.get("role_ids", [])) != {"explorer", "qa_tester"} or evidence_node.get("required_model") != "gpt-5.6-luna" or evidence_node.get("required_reasoning_effort") != "max":
        errors.append("deliberation evidence work must use bounded Luna/max explorer or QA specialists")
    if subnodes.get("ask_material_human_decision", {}).get("executor") != {"kind": "human", "id": "codex_picker"}:
        errors.append("material deliberation choices must use the Codex picker")
    for node_id, node in subnodes.items():
        completion = node.get("completion", {})
        if not isinstance(completion, dict) or not completion.get("predicate"):
            errors.append(f"deliberation node {node_id} needs a completion predicate")
        for evidence_id in completion.get("evidence", []):
            if evidence_id not in evidence:
                errors.append(f"deliberation node {node_id} names unknown evidence: {evidence_id}")

    subtable = deliberation.get("outcome_table", {})
    required_dispositions = {
        "accepted", "revision_required", "evidence_or_experiment_required",
        "material_human_decision_required", "blocked", "fatal",
    }
    if subtable.get("node") != "validate_deliberation" or set(subtable.get("domain", [])) != required_dispositions:
        errors.append("deliberation validation must classify the complete closed disposition set")
    table_cases = subtable.get("cases", [])
    if {case.get("value") for case in table_cases if isinstance(case, dict)} != required_dispositions:
        errors.append("deliberation outcome cases must cover every disposition exactly")
    if {case.get("edge") for case in table_cases if isinstance(case, dict)} != {edge.get("id") for edge in sub_outgoing.get("validate_deliberation", [])}:
        errors.append("deliberation outcome cases must cover every validator edge exactly")
    revision_edge = subedges.get("deliberation_revision_to_discussion", {})
    if revision_edge.get("budget") != "deliberation_discussion_rounds" or revision_edge.get("to") != "discuss_with_peers":
        errors.append("deliberation revision must return to peer discussion through its round budget")
    evidence_edge = subedges.get("deliberation_evidence_to_resolution", {})
    if evidence_edge.get("budget") != "deliberation_evidence_resolution" or evidence_edge.get("to") != "resolve_deliberation_evidence":
        errors.append("factual disagreement must route through bounded evidence resolution")
    human_edge = subedges.get("deliberation_human_to_decision", {})
    if human_edge.get("budget") != "deliberation_material_human_decisions" or human_edge.get("to") != "ask_material_human_decision":
        errors.append("material human deliberation decisions must have a one-question budget")
    lifecycle = deliberation.get("lifecycle", {})
    required_lifecycle = {
        "instance_id": "request_id", "suspend_invoking_node": True, "resume_exact_invoking_node": True,
        "return_node_from_request": True, "bind_invoking_run_id": True, "bind_mission_anchor_digest": True,
        "bind_input_digest": True,
        "bind_profile_version": True, "bind_resolution_receipts_to_request": True,
        "accepted_proposal_required_for_accept": True,
        "may_select_parent_downstream_edge": False, "max_active_per_invoking_node": 1,
        "upstream_change_handling": "invalidate_affected_artifacts_then_return_to_caller",
    }
    if lifecycle != required_lifecycle:
        errors.append("deliberation lifecycle must bind and resume the exact caller without choosing parent edges")
    required_hard_guards = {
        "hard_safety", "data_truth", "tenant_and_security", "release_authority", "required_verification",
        "failed_ship_or_deploy_gate",
    }
    if set(deliberation.get("non_debatable_guards", [])) != required_hard_guards:
        errors.append("deliberation must preserve every hard safety, data, authority, release, and verification guard")
    definitions = deliberation.get("predicate_definitions", {})
    if not isinstance(definitions, dict) or not definitions or not all(isinstance(value, str) and value.strip() for value in definitions.values()):
        errors.append("every deliberation predicate needs an explicit truth-condition definition")

    deliberation_traces_raw = graph.get("deliberation_trace_scenarios")
    if not isinstance(deliberation_traces_raw, list):
        errors.append("deliberation_trace_scenarios must be a list")
        deliberation_traces_raw = []
    deliberation_traces = {
        trace.get("id"): trace
        for trace in deliberation_traces_raw
        if isinstance(trace, dict) and isinstance(trace.get("id"), str)
    }
    required_deliberation_traces = {
        "design_profile_returns_to_exact_caller",
        "engineering_profile_returns_to_exact_caller",
        "objection_routes_through_revision_evidence_and_human_gate",
        "routine_deterministic_node_skips_deliberation",
        "hard_gate_cannot_be_debated_away",
    }
    if set(deliberation_traces) != required_deliberation_traces:
        errors.append("deliberation traces must cover two callers, objections, routine skip, and hard-gate preservation")
    subtable_cases = {
        case.get("value"): case
        for case in table_cases
        if isinstance(case, dict) and isinstance(case.get("value"), str)
    }
    for trace_id, trace in deliberation_traces.items():
        caller = trace.get("invoking_node_id")
        if caller not in nodes:
            errors.append(f"deliberation trace {trace_id} names unknown caller: {caller}")
        if trace.get("template") != "bounded_peer_deliberation":
            errors.append(f"deliberation trace {trace_id} must use the shared template")
        if trace.get("return_node_id") != caller or trace.get("return_input_digest") != trace.get("input_digest"):
            errors.append(f"deliberation trace {trace_id} must return to the exact caller and input digest")
        steps = trace.get("steps")
        if trace.get("invoked") is False:
            if steps != [] or trace.get("ends_at") != caller:
                errors.append(f"routine deliberation trace {trace_id} must skip without leaving its caller")
            continue
        profile = deliberation_profiles.get(trace.get("profile_id"), {})
        if caller not in profile.get("eligible_callers", []):
            errors.append(f"deliberation trace {trace_id} uses an ineligible caller/profile pair")
        if trace.get("profile_version") != profile.get("version"):
            errors.append(f"deliberation trace {trace_id} must bind the selected profile version")
        if not isinstance(steps, list) or not steps:
            errors.append(f"deliberation trace {trace_id} needs internal steps")
            continue
        current = "prepare_deliberation"
        for step_index, step in enumerate(steps):
            if not isinstance(step, dict) or step.get("node") != current:
                errors.append(f"deliberation trace {trace_id} step {step_index} expected node {current}")
                break
            edge = subedges.get(step.get("edge"))
            if edge is None or edge.get("from") != current:
                errors.append(f"deliberation trace {trace_id} step {step_index} has invalid edge")
                break
            if current == "validate_deliberation":
                case = subtable_cases.get(step.get("outcome"))
                if not case or case.get("edge") != edge.get("id"):
                    errors.append(f"deliberation trace {trace_id} step {step_index} does not match the closed outcome table")
                    break
            current = edge.get("to")
        if trace.get("ends_at") != current:
            errors.append(f"deliberation trace {trace_id} ends at {current}, not {trace.get('ends_at')}")
    distinct_invocations = {
        (trace.get("invoking_node_id"), trace.get("profile_id"))
        for trace in deliberation_traces.values()
        if trace.get("invoked") is True
    }
    if len(distinct_invocations) < 2:
        errors.append("at least two distinct caller/profile pairs must prove reuse of the same deliberation subgraph")
    hard_trace = deliberation_traces.get("hard_gate_cannot_be_debated_away", {})
    if not {"failed_required_gate_preserved", "authority_not_expanded", "fatal_return", "exact_caller_return"} <= set(hard_trace.get("assertions", [])):
        errors.append("the hard-gate trace must prove deliberation cannot waive failure or authority")
    if nodes.get("deliver_slice", {}).get("delegation", {}).get("parallelism") != "serialized":
        errors.append("only one implementation writer may run after deliberation acceptance")

    slice_receipt = evidence.get("slice_delivery_receipt", {})
    slice_fields = set(slice_receipt.get("required_fields", [])) if isinstance(slice_receipt, dict) else set()
    required_slice_fields = {"slice_id", "plan_digest", "delivered_commit", "verification_refs", "result"}
    if not required_slice_fields <= slice_fields:
        errors.append("slice_delivery_receipt must bind slice id, plan digest, delivered commit, verification, and result")
    deliver_slice = nodes.get("deliver_slice", {})
    deliver_completion = deliver_slice.get("completion", {}) if isinstance(deliver_slice, dict) else {}
    if not isinstance(deliver_completion, dict) or deliver_completion.get("predicate") != "slice_delivery_recorded" or deliver_completion.get("evidence") != ["slice_delivery_receipt"]:
        errors.append("deliver_slice must complete with one slice_delivery_receipt")
    if "repository_revision_changed" in deliver_slice.get("invalidated_by", []):
        errors.append("slice delivery evidence must not be invalidated by later repository movement")
    if "slice_delivery_receipt" not in nodes.get("assemble_candidate", {}).get("inputs", []):
        errors.append("assemble_candidate must consume durable slice delivery receipts")
    if nodes.get("repair_candidate", {}).get("completion", {}).get("predicate") == "slice_delivery_recorded":
        errors.append("candidate repair must not overwrite a historical slice delivery receipt")

    gating_reviews = {
        "validate_strategy_opportunity",
        "validate_product_opportunity",
        "review_product_direction",
        "review_experience",
        "review_engineering",
    }
    for node_id in sorted(gating_reviews):
        completion = nodes.get(node_id, {}).get("completion", {})
        if not isinstance(completion, dict) or completion.get("predicate") != "review_disposition_recorded":
            errors.append(f"gating review {node_id} must record a typed disposition")
        guards = {edge.get("guard") for edge in outgoing.get(node_id, [])}
        if "review_revision_required" not in guards or "review_fatal" not in guards:
            errors.append(f"gating review {node_id} needs revision and fatal routes")
        if "stage_completed" in guards:
            errors.append(f"gating review {node_id} must not advance on generic stage_completed")

    legacy_release_nodes = {
        "publish_branch",
        "open_change",
        "verify_change",
        "merge_change",
        "deploy_change",
        "verify_environment",
        "observe_canary",
        "compensate_release",
    }
    for node_id in sorted(legacy_release_nodes & set(nodes)):
        errors.append(f"active v0 must not split compound release executor at node: {node_id}")
    compound_release_nodes = {"ship_change": "ship", "land_and_deploy_change": "land-and-deploy"}
    for node_id, executor_id in compound_release_nodes.items():
        node = nodes.get(node_id, {})
        if node.get("executor") != {"kind": "skill", "id": executor_id}:
            errors.append(f"compound release node {node_id} must use executor {executor_id}")
        completion = node.get("completion", {})
        if not isinstance(completion, dict) or completion.get("predicate") != "compound_release_recorded":
            errors.append(f"compound release node {node_id} must record compound execution")
        if "authority_envelope" not in node.get("inputs", []) or "authority_envelope" not in completion.get("evidence", []):
            errors.append(f"compound release node {node_id} must require and retain full authority evidence")
    if nodes.get("prepare_release", {}).get("executor") != {"kind": "deterministic", "id": "compound_release_preflight"}:
        errors.append("prepare_release must be a deterministic compound-authority preflight")

    for template_id, template in dynamic_templates.items():
        if template_id in nodes:
            errors.append(f"dynamic node template collides with static node: {template_id}")
        if template.get("kind") != "decision":
            errors.append(f"dynamic node template {template_id} must have kind decision")
        executor = template.get("executor", {})
        if not isinstance(executor, dict):
            errors.append(f"dynamic node template {template_id} has an invalid executor")
            executor = {}
        if executor.get("kind") != "human" or not executor.get("id"):
            errors.append(f"dynamic node template {template_id} must use a human executor")
        hosts = template.get("allowed_hosts")
        if not isinstance(hosts, list) or not hosts:
            errors.append(f"dynamic node template {template_id} needs allowed_hosts")
        else:
            for host in hosts:
                if host not in nodes or nodes.get(host, {}).get("kind") == "terminal":
                    errors.append(f"dynamic node template {template_id} has invalid host: {host}")
        completion = template.get("completion", {})
        if not isinstance(completion, dict):
            errors.append(f"dynamic node template {template_id} must declare completion")
            completion = {}
        if completion.get("predicate") != "human_decision_recorded" or "decision_receipt" not in completion.get("evidence", []):
            errors.append(f"dynamic node template {template_id} must require a human decision receipt")
        lifecycle = template.get("lifecycle", {})
        if not isinstance(lifecycle, dict):
            errors.append(f"dynamic node template {template_id} must declare lifecycle")
            lifecycle = {}
        if lifecycle.get("suspend_host") is not True or lifecycle.get("resume_same_host") is not True or lifecycle.get("max_active_per_host") != 1:
            errors.append(f"dynamic node template {template_id} must suspend and resume exactly one host")

    for node_id, node in nodes.items():
        if node.get("kind") == "fork":
            join_id = node.get("join")
            branches = [edge for edge in outgoing[node_id] if edge.get("type") == "fork"]
            if join_id not in nodes or nodes.get(join_id, {}).get("kind") != "join":
                errors.append(f"fork {node_id} has invalid join: {join_id}")
            if len(branches) < 2:
                errors.append(f"fork {node_id} needs at least two fork branches")
            for branch in branches:
                branch_id = branch.get("to")
                if not any(edge.get("to") == join_id and edge.get("type") == "join" for edge in outgoing.get(branch_id, [])):
                    errors.append(f"fork branch {branch_id} does not join at {join_id}")
        if node.get("kind") == "join":
            fork_id = node.get("fork")
            if fork_id not in nodes or nodes.get(fork_id, {}).get("kind") != "fork":
                errors.append(f"join {node_id} has invalid fork: {fork_id}")
            if node.get("join_policy") != "all_dispatched":
                errors.append(f"join {node_id} must use all_dispatched")

    if start in nodes:
        reachable = {start}
        queue = deque([start])
        while queue:
            for edge in outgoing[queue.popleft()]:
                target = edge.get("to")
                if target in nodes and target not in reachable:
                    reachable.add(target)
                    queue.append(target)
        for node_id in sorted(set(nodes) - reachable):
            errors.append(f"unreachable node: {node_id}")

    can_finish = set(terminals)
    queue = deque(terminals)
    while queue:
        for edge in incoming[queue.popleft()]:
            source = edge.get("from")
            if source in nodes and source not in can_finish:
                can_finish.add(source)
                queue.append(source)
    for node_id in sorted(set(nodes) - can_finish):
        errors.append(f"node cannot reach a terminal: {node_id}")

    review_node = meta.get("review_node")
    for terminal in terminals:
        for edge in incoming[terminal]:
            if edge.get("from") != review_node:
                errors.append(f"terminal {terminal} bypasses mandatory review node {review_node}")
    receipt_node = meta.get("run_receipt_node")
    cleanup_node_id = meta.get("cleanup_node")
    if not any(edge.get("from") == receipt_node and edge.get("to") == cleanup_node_id for edge in edges.values()):
        errors.append("run receipt must flow to the mandatory cleanup node")
    if not any(edge.get("from") == cleanup_node_id and edge.get("to") == review_node for edge in edges.values()):
        errors.append("cleanup must flow to mandatory run review")
    if any(edge.get("from") == receipt_node and edge.get("to") == review_node for edge in edges.values()):
        errors.append("run receipt must not bypass cleanup")
    cleanup_retry = edges.get("cleanup_authority_to_cleanup", {})
    if (
        cleanup_retry.get("from") != "request_cleanup_authority"
        or cleanup_retry.get("to") != cleanup_node_id
        or cleanup_retry.get("type") != "recovery"
        or cleanup_retry.get("budget") != "cleanup_attempts"
    ):
        errors.append("destructive cleanup retry must be one bounded return to the cleanup node")
    valid_delivery_statuses = {"completed", "blocked", "failed"}
    for edge_id, edge in edges.items():
        if edge.get("to") == receipt_node:
            if edge.get("sets_status") not in valid_delivery_statuses:
                errors.append(f"receipt edge {edge_id} must set completed, blocked, or failed delivery status")
        elif "sets_status" in edge:
            errors.append(f"non-receipt edge {edge_id} must not set delivery status")

    unknown_guard = policies.get("unknown_guard", {})
    if not isinstance(unknown_guard, dict):
        errors.append("unknown_guard policy must be an object")
        unknown_guard = {}
    if unknown_guard.get("action") != "block" or unknown_guard.get("location") != "originating_node":
        errors.append("unknown guards must block at the originating node")
    if unknown_guard.get("route_decision_node") not in nodes:
        errors.append("unknown route guards must point to the route decision node")
    learning = policies.get("learning", {})
    if not isinstance(learning, dict):
        errors.append("learning policy must be an object")
        learning = {}
    if learning.get("v0_mode") != "proposal_only":
        errors.append("graph v0 learning must be proposal_only")
    review_failure = learning.get("review_failure", {})
    if review_failure != {
        "action": "emit_degraded_receipt",
        "root_cause_class": "policy_issue",
        "preserve_run_status": True,
        "proposals_allowed": False,
    }:
        errors.append("review failure must emit a proposal-free degraded receipt and preserve run status")
    breach_policy = learning.get("confirmed_hard_invariant_breach", {})
    if breach_policy != {
        "preserve_delivery_receipt": True,
        "effective_status": "failed",
        "may_upgrade_status": False,
    }:
        errors.append("confirmed hard invariant breach must preserve the delivery receipt and close failed")
    if learning.get("future_auto_promotion") != "nonsemantic_presentation_and_diagnostics_within_policy_ceiling":
        errors.append("pre-unlock auto-promotion must be limited to nonsemantic presentation and diagnostics")
    if set(learning.get("pre_semantic_unlock_auto_promotable", [])) != {"presentation_only", "diagnostics_only"}:
        errors.append("pre-unlock auto-promotable classes must be presentation_only and diagnostics_only")
    required_semantic_unlock = {
        "executable_historical_scenario_replay",
        "independent_semantic_evaluator",
        "human_approved_semantic_policy_ceiling",
    }
    if not required_semantic_unlock <= set(learning.get("semantic_promotion_unlock_requirements", [])):
        errors.append("semantic promotion needs replay, an independent evaluator, and an approved ceiling")
    required_pre_unlock_approval = {
        "node_semantic_change",
        "edge_topology_change",
        "guard_semantic_change",
        "evidence_requirement_change",
    }
    if not required_pre_unlock_approval <= set(learning.get("pre_semantic_unlock_human_approved", [])):
        errors.append("semantic graph changes must stay human-approved before semantic unlock")
    human_decisions = policies.get("human_decisions", {})
    if not isinstance(human_decisions, dict):
        errors.append("human_decisions policy must be an object")
        human_decisions = {}
    decision_template = human_decisions.get("dynamic_template")
    if decision_template not in dynamic_templates:
        errors.append(f"unknown human decision template: {decision_template}")
    status_handlers = policies.get("status_handlers", {})
    if not isinstance(status_handlers, dict) or status_handlers.get("blocked") != {"node": receipt_node, "sets_status": "blocked"} or status_handlers.get("fatal") != {"node": receipt_node, "sets_status": "failed"}:
        errors.append("blocked and fatal status handlers must flow to the run receipt node")

    return errors


def self_test(graph: dict[str, Any]) -> tuple[list[str], int]:
    failures: list[str] = []
    cases: list[tuple[str, dict[str, Any], str]] = []

    try:
        _unique_object([("duplicate", 1), ("duplicate", 2)])
    except DuplicateKeyError:
        pass
    else:
        failures.append("self-test 'duplicate JSON key' was not rejected")

    unknown_target = copy.deepcopy(graph)
    unknown_target["edges"][0]["to"] = "missing_node"
    cases.append(("unknown target", unknown_target, "unknown target"))

    unreachable = copy.deepcopy(graph)
    unreachable["nodes"].append({
        "id": "orphan",
        "kind": "outcome",
        "lane": "test",
        "executor": {"kind": "controller", "id": "test"},
        "inputs": [],
        "outcome": "Test orphan.",
        "completion": {"predicate": "run_closed", "evidence": ["run_review_receipt"]},
        "invalidated_by": [],
    })
    unreachable["edges"].append({"id": "orphan_to_end", "from": "orphan", "to": "run_completed", "guard": "run_status_completed", "type": "complete"})
    cases.append(("unreachable node", unreachable, "unreachable node: orphan"))

    unbounded = copy.deepcopy(graph)
    revision = next(edge for edge in unbounded["edges"] if edge["type"] == "revision")
    revision.pop("budget")
    cases.append(("unbounded revision", unbounded, "needs a budget"))

    review_bypass = copy.deepcopy(graph)
    review_bypass["edges"].append({"id": "bypass_review", "from": "record_run_receipt", "to": "run_completed", "guard": "run_status_completed", "type": "complete"})
    cases.append(("review bypass", review_bypass, "bypasses mandatory review"))

    cleanup_bypass = copy.deepcopy(graph)
    next(edge for edge in cleanup_bypass["edges"] if edge["id"] == "receipt_to_cleanup")["to"] = "review_run"
    cases.append(("cleanup bypass", cleanup_bypass, "mandatory cleanup node"))

    cross_run_cleanup = copy.deepcopy(graph)
    cross_run_cleanup["policies"]["cleanup"]["scope"] = "all_visible_workspaces"
    cases.append(("cross-run cleanup", cross_run_cleanup, "current run"))

    broad_cleanup_target = copy.deepcopy(graph)
    broad_cleanup_target["policies"]["cleanup"]["forbidden_targets"].remove("workspace_root")
    cases.append(("broad cleanup target", broad_cleanup_target, "forbid broad roots"))

    inferred_cleanup_consent = copy.deepcopy(graph)
    inferred_cleanup_consent["policies"]["cleanup"]["destructive_confirmation"] = "standing_cleanup_preference"
    cases.append(("inferred cleanup consent", inferred_cleanup_consent, "explicit yes or do it"))

    unbounded_cleanup_retry = copy.deepcopy(graph)
    next(edge for edge in unbounded_cleanup_retry["edges"] if edge["id"] == "cleanup_authority_to_cleanup").pop("budget")
    cases.append(("unbounded cleanup retry", unbounded_cleanup_retry, "needs a budget"))

    terminal_without_cleanup = copy.deepcopy(graph)
    next(node for node in terminal_without_cleanup["nodes"] if node["id"] == "run_completed")["completion"]["evidence"].remove("run_cleanup_receipt")
    cases.append(("terminal without cleanup", terminal_without_cleanup, "must require run_cleanup_receipt"))

    undefined_predicate = copy.deepcopy(graph)
    undefined_predicate["predicate_definitions"].pop("stage_completed")
    cases.append(("undefined predicate", undefined_predicate, "needs a truth-condition definition"))

    invalid_dynamic_host = copy.deepcopy(graph)
    invalid_dynamic_host["dynamic_node_templates"][0]["allowed_hosts"].append("deploy_change_missing")
    cases.append(("invalid dynamic host", invalid_dynamic_host, "has invalid host"))

    duplicate_node = copy.deepcopy(graph)
    duplicate_node["nodes"].append(copy.deepcopy(duplicate_node["nodes"][0]))
    cases.append(("duplicate node id", duplicate_node, "duplicate node id"))

    invalid_executor = copy.deepcopy(graph)
    invalid_executor["nodes"][0]["executor"]["kind"] = "inline_shell"
    cases.append(("invalid executor", invalid_executor, "invalid executor"))

    unknown_evidence = copy.deepcopy(graph)
    unknown_evidence["nodes"][0]["completion"]["evidence"].append("missing_evidence_type")
    cases.append(("unknown evidence", unknown_evidence, "unknown completion evidence"))

    broken_join = copy.deepcopy(graph)
    broken_join["edges"] = [edge for edge in broken_join["edges"] if edge["id"] != "review_to_join"]
    cases.append(("broken fork join", broken_join, "does not join"))

    unsafe_review_failure = copy.deepcopy(graph)
    unsafe_review_failure["policies"]["learning"]["review_failure"]["proposals_allowed"] = True
    cases.append(("unsafe review failure", unsafe_review_failure, "proposal-free degraded receipt"))

    malformed_completion = copy.deepcopy(graph)
    malformed_completion["nodes"][0]["completion"] = ["not", "an", "object"]
    cases.append(("malformed completion", malformed_completion, "must declare completion"))

    malformed_template_executor = copy.deepcopy(graph)
    malformed_template_executor["dynamic_node_templates"][0]["executor"] = ["not", "an", "object"]
    cases.append(("malformed template executor", malformed_template_executor, "invalid executor"))

    incomplete_outcome_table = copy.deepcopy(graph)
    incomplete_outcome_table["outcome_tables"][0]["cases"].pop()
    cases.append(("incomplete outcome table", incomplete_outcome_table, "cover its domain exactly"))

    duplicate_outcome = copy.deepcopy(graph)
    duplicate_outcome["outcome_tables"][0]["cases"][1]["value"] = duplicate_outcome["outcome_tables"][0]["cases"][0]["value"]
    cases.append(("duplicate outcome", duplicate_outcome, "duplicate outcome values"))

    broken_trace = copy.deepcopy(graph)
    broken_trace["trace_scenarios"][0]["steps"][1]["node"] = "align_product"
    cases.append(("broken trace", broken_trace, "expected node"))

    unsafe_late_breach = copy.deepcopy(graph)
    unsafe_late_breach["policies"]["learning"]["confirmed_hard_invariant_breach"]["effective_status"] = "completed"
    cases.append(("unsafe late breach", unsafe_late_breach, "close failed"))

    stale_slice_binding = copy.deepcopy(graph)
    next(node for node in stale_slice_binding["nodes"] if node["id"] == "deliver_slice")["invalidated_by"].append("repository_revision_changed")
    cases.append(("stale slice binding", stale_slice_binding, "must not be invalidated by later repository movement"))

    unsafe_semantic_promotion = copy.deepcopy(graph)
    unsafe_semantic_promotion["policies"]["learning"]["future_auto_promotion"] = "low_risk_semantic_graph_edits"
    cases.append(("unsafe semantic promotion", unsafe_semantic_promotion, "limited to nonsemantic"))

    untyped_review = copy.deepcopy(graph)
    next(node for node in untyped_review["nodes"] if node["id"] == "review_engineering")["completion"]["predicate"] = "verification_recorded"
    cases.append(("untyped review", untyped_review, "must record a typed disposition"))

    split_release_executor = copy.deepcopy(graph)
    next(node for node in split_release_executor["nodes"] if node["id"] == "ship_change")["executor"]["id"] = "publish-only"
    cases.append(("split release executor", split_release_executor, "must use executor ship"))

    missing_delivery_status = copy.deepcopy(graph)
    next(edge for edge in missing_delivery_status["edges"] if edge["to"] == "record_run_receipt").pop("sets_status")
    cases.append(("missing delivery status", missing_delivery_status, "must set completed, blocked, or failed"))

    unknown_specialist = copy.deepcopy(graph)
    next(node for node in unknown_specialist["nodes"] if node["id"] == "deliver_slice")["delegation"]["allowed_roles"] = ["ghost_writer"]
    cases.append(("unknown specialist", unknown_specialist, "unknown specialist role"))

    delegated_controller = copy.deepcopy(graph)
    delegated_controller["policies"]["delegation"]["transition_authority"] = "specialist_may_advance"
    cases.append(("delegated transition authority", delegated_controller, "controller-only graph transition authority"))

    unsafe_parallel_writer = copy.deepcopy(graph)
    next(node for node in unsafe_parallel_writer["nodes"] if node["id"] == "deliver_slice")["delegation"]["parallelism"] = "read_only"
    cases.append(("unsafe parallel writer", unsafe_parallel_writer, "must require isolation or serialization"))

    incomplete_delegation_receipt = copy.deepcopy(graph)
    next(item for item in incomplete_delegation_receipt["evidence_types"] if item["id"] == "delegation_receipt")["required_fields"].remove("verification_criteria")
    cases.append(("incomplete delegation receipt", incomplete_delegation_receipt, "delegation_receipt must bind"))

    delegation_completes_node = copy.deepcopy(graph)
    next(node for node in delegation_completes_node["nodes"] if node["id"] == "review_candidate")["completion"]["evidence"].append("delegation_receipt")
    cases.append(("delegation completes node", delegation_completes_node, "cannot complete from a delegation receipt"))

    persistent_private_memory = copy.deepcopy(graph)
    persistent_private_memory["policies"]["delegation"]["persistent_role_config"] = "durable_private_agent_memory"
    cases.append(("persistent private memory", persistent_private_memory, "must not imply private durable agent memory"))

    reused_agent_thread = copy.deepcopy(graph)
    reused_agent_thread["policies"]["delegation"]["execution_lifecycle"] = "persistent_agent_thread"
    cases.append(("reused agent thread", reused_agent_thread, "must be fresh agent threads"))

    side_quest_hijacks_parent = copy.deepcopy(graph)
    side_quest_hijacks_parent["policies"]["focus"]["parent_transition"] = "replace_active_run"
    cases.append(("side quest hijacks parent", side_quest_hijacks_parent, "resume the same parent node"))

    side_quest_inherits_authority = copy.deepcopy(graph)
    side_quest_inherits_authority["policies"]["focus"]["side_quest_authority_inheritance"] = "copy_parent"
    cases.append(("side quest inherits authority", side_quest_inherits_authority, "must not inherit parent release authority"))

    unauthorized_side_quest_creation = copy.deepcopy(graph)
    unauthorized_side_quest_creation["policies"]["focus"]["side_quest_action"] = "create_linked_codex_task"
    cases.append(("unauthorized side quest creation", unauthorized_side_quest_creation, "when authorized"))

    reversible_question = copy.deepcopy(graph)
    reversible_question["policies"]["autonomy"]["post_alignment_reversible_decisions"] = "ask_human"
    cases.append(("reversible question after alignment", reversible_question, "auto-decide reversible choices"))

    short_completion = copy.deepcopy(graph)
    short_completion["policies"]["release"]["explicit_implementation_through_production_requested_completion"] = "candidate_verified"
    cases.append(("shortened implementation completion", short_completion, "must target verified production"))

    repeated_release_confirmation = copy.deepcopy(graph)
    repeated_release_confirmation["policies"]["release"]["reconfirm_bound_authority"] = True
    cases.append(("repeated release confirmation", repeated_release_confirmation, "must not be reconfirmed"))

    unauthorized_release_target = copy.deepcopy(graph)
    unauthorized_release_target["policies"]["release"]["without_release_authority"] = "always_production"
    cases.append(("unauthorized release target", unauthorized_release_target, "respect the requested completion target"))

    nested_final_stops_run = copy.deepcopy(graph)
    nested_final_stops_run["policies"]["release"]["nested_skill_final"] = "outer_terminal"
    cases.append(("nested skill stops outer run", nested_final_stops_run, "must return to the outer controller"))

    incomplete_mission_anchor = copy.deepcopy(graph)
    next(item for item in incomplete_mission_anchor["evidence_types"] if item["id"] == "route_card")["required_fields"].remove("primary_outcome")
    cases.append(("incomplete mission anchor", incomplete_mission_anchor, "bind the complete mission anchor"))

    unbound_verification_receipt = copy.deepcopy(graph)
    next(item for item in unbound_verification_receipt["evidence_types"] if item["id"] == "verification_receipt")["required_fields"].remove("receipt_id")
    cases.append(("unbound verification receipt", unbound_verification_receipt, "stable receipt_id"))

    unbound_join_receipt = copy.deepcopy(graph)
    next(item for item in unbound_join_receipt["evidence_types"] if item["id"] == "join_receipt")["required_fields"].remove("branch_receipt_ids")
    cases.append(("unbound join receipt", unbound_join_receipt, "exact branch receipt IDs"))

    untyped_alignment_lock = copy.deepcopy(graph)
    next(node for node in untyped_alignment_lock["nodes"] if node["id"] == "align_product")["completion"] = {
        "predicate": "current_artifact_recorded", "evidence": ["artifact_receipt"]
    }
    cases.append(("untyped alignment lock", untyped_alignment_lock, "typed alignment lock"))

    missing_focus_policy_trace = copy.deepcopy(graph)
    next(trace for trace in missing_focus_policy_trace["policy_trace_scenarios"] if trace["id"] == "side_quest_preserves_parent")["assertions"].remove("parent_resumes_same_node")
    cases.append(("missing focus policy trace", missing_focus_policy_trace, "missing required assertions"))

    annotation_without_coverage = copy.deepcopy(graph)
    annotation_without_coverage["policies"]["annotation_batch"]["coverage_rule"] = "best_effort"
    cases.append(("annotation without full coverage", annotation_without_coverage, "reconcile every observation"))

    duplicate_annotation_tasks = copy.deepcopy(graph)
    duplicate_annotation_tasks["policies"]["annotation_batch"]["duplicates"] = "one_task_per_annotation"
    cases.append(("duplicate annotation tasks", duplicate_annotation_tasks, "must not create duplicate work"))

    annotation_task_without_authority = copy.deepcopy(graph)
    next(node for node in annotation_task_without_authority["nodes"] if node["id"] == "materialize_annotation_tasks")["inputs"].remove("authority_envelope")
    cases.append(("annotation task without authority", annotation_task_without_authority, "must require authority"))

    recursive_annotation_child = copy.deepcopy(graph)
    recursive_annotation_child["policies"]["annotation_batch"]["child_input"] = "full_annotation_batch"
    cases.append(("recursive annotation child", recursive_annotation_child, "must receive one ledger problem"))

    wrong_deliberation_model = copy.deepcopy(graph)
    wrong_deliberation_model["dynamic_subgraph_templates"][0]["specialist_execution"]["model"] = "gpt-5.6-terra"
    cases.append(("wrong deliberation model", wrong_deliberation_model, "fresh Luna/max reviewer"))

    wrong_deliberation_effort = copy.deepcopy(graph)
    wrong_deliberation_effort["policies"]["deliberation"]["specialist_reasoning_effort"] = "high"
    cases.append(("wrong deliberation effort", wrong_deliberation_effort, "must use max reasoning effort"))

    deliberation_without_peer_exchange = copy.deepcopy(graph)
    deliberation_without_peer_exchange["policies"]["deliberation"]["peer_exchange"] = "independent_reports_only"
    cases.append(("deliberation without peer exchange", deliberation_without_peer_exchange, "lossless statements"))

    deliberation_majority_vote = copy.deepcopy(graph)
    deliberation_majority_vote["policies"]["deliberation"]["decision_rule"] = "majority_vote"
    cases.append(("deliberation majority vote", deliberation_majority_vote, "must never use majority vote"))

    unbounded_deliberation_rounds = copy.deepcopy(graph)
    unbounded_deliberation_rounds["policies"]["deliberation"]["max_discussion_rounds"] = 3
    cases.append(("unbounded deliberation rounds", unbounded_deliberation_rounds, "limited to two rounds"))

    deliberation_wrong_return = copy.deepcopy(graph)
    deliberation_wrong_return["dynamic_subgraph_templates"][0]["lifecycle"]["resume_exact_invoking_node"] = False
    cases.append(("deliberation wrong return", deliberation_wrong_return, "exact caller"))

    deliberation_without_mission_binding = copy.deepcopy(graph)
    deliberation_without_mission_binding["dynamic_subgraph_templates"][0]["lifecycle"]["bind_mission_anchor_digest"] = False
    cases.append(("deliberation without mission binding", deliberation_without_mission_binding, "exact caller"))

    unbounded_deliberation_evidence = copy.deepcopy(graph)
    unbounded_deliberation_evidence["policies"]["deliberation"]["max_evidence_or_experiment_cycles"] = 2
    cases.append(("unbounded deliberation evidence", unbounded_deliberation_evidence, "limited to one cycle"))

    unbounded_deliberation_human_gate = copy.deepcopy(graph)
    next(item for item in unbounded_deliberation_human_gate["dynamic_subgraph_templates"][0]["edges"] if item["id"] == "deliberation_human_to_decision").pop("budget")
    cases.append(("unbounded deliberation human gate", unbounded_deliberation_human_gate, "one-question budget"))

    deliberation_without_broadcast_evidence = copy.deepcopy(graph)
    next(item for item in deliberation_without_broadcast_evidence["evidence_types"] if item["id"] == "deliberation_round")["required_fields"].remove("broadcasts")
    cases.append(("deliberation without broadcast evidence", deliberation_without_broadcast_evidence, "missing required deliberation fields"))

    routine_node_can_deliberate = copy.deepcopy(graph)
    routine_node_can_deliberate["dynamic_subgraph_templates"][0]["allowed_hosts"].append("run_required_checks")
    cases.append(("routine node can deliberate", routine_node_can_deliberate, "allowed hosts must equal"))

    deliberation_waives_hard_gate = copy.deepcopy(graph)
    deliberation_waives_hard_gate["policies"]["deliberation"]["release_gate_override"] = True
    cases.append(("deliberation waives hard gate", deliberation_waives_hard_gate, "cannot waive hard"))

    duplicated_profile_graph = copy.deepcopy(graph)
    duplicated_profile_graph["dynamic_subgraph_templates"].append(copy.deepcopy(duplicated_profile_graph["dynamic_subgraph_templates"][0]))
    duplicated_profile_graph["dynamic_subgraph_templates"][1]["id"] = "design_only_deliberation"
    cases.append(("duplicated profile graph", duplicated_profile_graph, "one reusable bounded_peer_deliberation"))

    for name, candidate, expected in cases:
        errors = validate(candidate)
        if not any(expected in error for error in errors):
            failures.append(f"self-test {name!r} did not detect {expected!r}")
    return failures, 1 + len(cases)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("graph", nargs="?", type=Path, default=GRAPH_PATH)
    parser.add_argument("--self-test", action="store_true", help="also prove key invalid mutations are rejected")
    args = parser.parse_args()

    try:
        graph = load_graph(args.graph)
    except (OSError, json.JSONDecodeError, DuplicateKeyError) as error:
        print(f"INVALID: {error}")
        return 1

    errors = validate(graph)
    if errors:
        print("INVALID")
        for error in errors:
            print(f"- {error}")
        return 1

    if args.self_test:
        failures, case_count = self_test(graph)
        if failures:
            print("SELF-TEST FAILED")
            for failure in failures:
                print(f"- {failure}")
            return 1

    print(f"VALID: {graph['graph']['id']} {graph['graph']['version']} ({len(graph['nodes'])} nodes, {len(graph['edges'])} edges)")
    if args.self_test:
        print(f"SELF-TEST: {case_count} invalid contract cases rejected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
