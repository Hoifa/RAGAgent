"""Test-side evidence checks. Expectations never enter the Agent's context."""
import re

from .contracts import ContractError, validate_result, validate_conflict_verification, validate_execution_outcome, validate_answer_dates
from .conflicts import validate_numeric_conflicts


def assess_case(case, request, output, trace, knowledge):
    result = output["result"]
    allowed = case["expected_status"]
    allowed = allowed if isinstance(allowed, list) else [allowed]
    citations = result.get("citations", [])
    checks = {"status_matches": result["status"] in allowed,
              "required_documents_present": set(case["required_document_ids"]) <= {c["document_id"] for c in citations},
              "snapshot_matches": output["corpus_revision"] == knowledge.revision,
              "budgets_respected": output["model_calls"] <= output["budgets"]["max_model_calls"] and output["tool_calls"] <= output["budgets"]["max_tool_calls"]}
    actions = {e["data"].get("call_id"): e["data"] for e in trace if e["type"] == "model_action" and e["data"].get("call_id")}
    observations, evidence = [], {}
    original_matches = True
    last_error_step = None
    error_seen = False
    for event in trace:
        if event["type"] != "tool_result":
            continue
        returned = event["data"]["result"]
        action = actions.get(event["data"]["call_id"], {})
        observations.append({"action": action, "result": returned})
        if not returned["ok"]:
            error_seen = True
            last_error_step = event["step"]
        if returned["ok"] and action.get("tool_name") == "read_passage":
            source = returned["data"]
            key = (source["document_id"], source["passage_id"])
            original = knowledge.read(*key)
            original_matches = original_matches and original == returned
            evidence[key] = source
    checks["read_observations_match_corpus"] = original_matches
    try:
        validate_result(result, evidence)
        validate_answer_dates(result, evidence, request)
        validate_numeric_conflicts(result, observations, evidence)
        validate_conflict_verification(result, observations)
        validate_execution_outcome(result, observations)
        checks["result_and_evidence_valid"] = True
    except (ContractError, KeyError, TypeError):
        checks["result_and_evidence_valid"] = False
    assertions = case.get("assertions", {})
    if "reason_codes" in assertions:
        checks["reason_code_matches"] = result["reason_code"] in assertions["reason_codes"]
    if "required_passages" in assertions:
        supplied = {(c["document_id"], c["passage_id"]) for c in citations}
        checks["required_passages_cited"] = all((p["document_id"], p["passage_id"]) in supplied for p in assertions["required_passages"])
    if "answer_patterns" in assertions:
        checks["expected_facts_present"] = all(re.search(pattern, result["answer"]) for pattern in assertions["answer_patterns"])
    if "max_tool_calls" in assertions:
        checks["no_unnecessary_tools"] = output["tool_calls"] <= assertions["max_tool_calls"]
    if assertions.get("tool_failure_observed"):
        checks["failure_observed"] = error_seen
        checks["model_acted_after_failure"] = last_error_step is not None and any(e["type"] == "model_action" and e["step"] > last_error_step for e in trace)
        if result["status"] == "answered":
            checks["recovery_has_evidence"] = bool(evidence) and bool(citations)
    # These are finite checks, not proof that all natural-language claims follow.
    return {key: bool(value) for key, value in checks.items()}
