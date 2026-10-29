"""Evidence audits must detect failures hidden by a matching business status."""
import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.audit_evidence import inspect_run, audit_reports, inside_root, pair_checks
from src.kb_agent.agent import Agent
from src.kb_agent.knowledge import KnowledgeBase, ToolExecutor
from src.kb_agent.models import ScriptedModel
from src.kb_agent.__main__ import write_artifacts
from src.kb_agent.contracts import ContractError, validate_result

ROOT = Path(__file__).resolve().parents[1]


class EvidenceAuditTests(unittest.TestCase):
    def setUp(self):
        self.case = next(c for c in json.loads((ROOT / "tests/fixtures/case-manifest.json").read_text(encoding="utf-8"))["cases"] if c["case_id"] == "A01")
        self.request = json.loads((ROOT / self.case["input"]).read_text(encoding="utf-8"))
        self.kb = KnowledgeBase.load(ROOT / self.case["corpus"])
        self.output, self.trace = Agent(ScriptedModel.load(ROOT / "tests/fixtures/mock/A01.json"), ToolExecutor(self.kb)).run(self.request)
        self.recorded = {k: self.output[k] for k in ("run_id", "mode", "model", "engine_revision", "corpus_revision", "model_configuration")}
        self.recorded.update(case_id="A01", execution="executed", repeat_index=1, status="answered")

    def inspect(self, trace=None, output=None, request=None):
        return inspect_run(self.case, self.request if request is None else request,
                           output or self.output, trace or self.trace, self.kb, self.recorded)

    def test_valid_saved_run_replays_with_trace_links(self):
        result = self.inspect()
        self.assertTrue(result["passed"])
        self.assertEqual(len(result["transitions"]), 2)
        self.assertEqual(result["transitions"][0]["next_action"], "read_passage")
        self.assertEqual(result["transitions"][1]["next_action"], "finish:answered")

    def test_tampered_search_is_detected_even_with_correct_answer_and_quotes(self):
        trace = copy.deepcopy(self.trace)
        hit = next(e for e in trace if e["type"] == "tool_result")["data"]["result"]["data"]["hits"][0]
        hit["excerpt"] = "tampered retrieval evidence"
        result = self.inspect(trace=trace)
        self.assertTrue(result["checks"]["result_and_evidence_valid"])
        self.assertFalse(result["checks"]["tool_observations_replay"])

    def test_missing_tool_result_cannot_keep_successful_trace_count(self):
        trace = copy.deepcopy(self.trace)
        trace = [e for e in trace if not (e["type"] == "tool_result" and e["data"]["call_id"] == "tool-1")]
        result = self.inspect(trace=trace)
        self.assertFalse(result["checks"]["actual_tool_counts"])
        self.assertFalse(result["checks"]["trace_sequence"])

    def test_finished_output_must_match_saved_output(self):
        trace = copy.deepcopy(self.trace)
        trace[-1]["data"]["result"]["answer"] = "different output"
        self.assertFalse(self.inspect(trace=trace)["checks"]["trace_envelope"])

    def test_forged_quote_does_not_pass_audit(self):
        output = copy.deepcopy(self.output)
        output["result"]["citations"][0]["quote"] = "fabricated quote"
        self.assertFalse(self.inspect(output=output)["checks"]["result_and_evidence_valid"])

    def test_trace_step_without_model_marker_is_detected(self):
        output = copy.deepcopy(self.output)
        output["model_calls"] += 1
        self.assertFalse(self.inspect(output=output)["checks"]["model_count_has_trace_markers"])

    def test_controlled_comparison_rejects_different_user_requests(self):
        left = self.inspect()
        right = copy.deepcopy(left)
        right["request"]["question"] = "A different question"
        checks = pair_checks(left, right, "conflict")
        self.assertFalse(checks["same_request"])

    def test_audit_cannot_follow_references_outside_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                inside_root(Path(directory), "../outside/output.json")

    def test_missing_artifacts_and_duplicate_rows_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data/corpora").mkdir(parents=True)
            shutil.copyfile(ROOT / self.case["corpus"], root / self.case["corpus"])
            stored = write_artifacts(root / "runs", "A01", self.request, self.output, self.trace)
            row = dict(self.recorded, directory=str(stored.relative_to(root)))
            report = root / "evaluation-results.json"
            report.write_text(json.dumps({"runs": [row, row]}), encoding="utf-8")
            runs, _, _ = audit_reports([report], {"cases": [self.case]}, root)
            self.assertEqual([r["passed"] for r in runs], [True, False])
            (stored / "output.json").unlink()
            runs, _, _ = audit_reports([report], {"cases": [self.case]}, root)
            self.assertFalse(any(r["passed"] for r in runs))

    def test_not_executed_is_not_a_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / "report.json"
            report.write_text(json.dumps({"runs": [{"case_id": "A01", "execution": "not_run"}]}), encoding="utf-8")
            runs, _, _ = audit_reports([report], {"cases": [self.case]}, root)
            self.assertFalse(runs[0]["passed"])
            self.assertEqual(runs[0]["error"], "not_executed")

    def test_resolution_is_a_hint_not_a_replacement_of_current_question(self):
        class ResolvingModel(ScriptedModel):
            def resolve_request(self, request, timeout):
                return {"action": "continue", "question": request["question"]}

            def next_action(self, state, timeout):
                self.seen = copy.deepcopy(state)
                return super().next_action(state, timeout)
        final = {"action": "finish", "result": {"status": "unanswerable", "reason_code": "insufficient_evidence",
                 "answer": "No evidence", "citations": [], "gaps": ["Missing rule"], "follow_up_question": None}}
        model = ResolvingModel([final])
        Agent(model, ToolExecutor(self.kb)).run(self.request)
        self.assertEqual(model.seen["request"], self.request)
        self.assertEqual(model.seen["resolved_question"], self.request["question"])

    def test_resolution_cannot_invent_a_comparison_task(self):
        class RewritingModel(ScriptedModel):
            def resolve_request(self, request, timeout):
                return {"action": "continue", "question": "a different task"}
        output, _ = Agent(RewritingModel([{"unused": True}]), ToolExecutor(self.kb)).run(self.request)
        self.assertEqual(output["result"]["reason_code"], "invalid_model_output")
        self.assertEqual(output["tool_calls"], 0)

    def test_fact_review_omits_assistant_claims_but_retains_user_conditions(self):
        import io
        from unittest.mock import patch
        from src.kb_agent.models import ChatModel
        model = ChatModel("https://example.invalid/v1", "test", "test-only-secret")
        request = {"question": "verify", "history": [{"role": "user", "content": "my condition"},
                    {"role": "assistant", "content": "untrusted prior fact"}]}
        before = copy.deepcopy(request)
        payload = {"choices": [{"message": {"content": '{"valid":true,"issues":[]}'}}]}
        with patch.object(model._opener, "open", return_value=io.BytesIO(json.dumps(payload).encode())) as call:
            model.review_result(request, {}, {}, [], 1)
        context = json.loads(json.loads(call.call_args[0][0].data)["messages"][1]["content"])
        self.assertEqual(context["request"]["history"], [request["history"][0]])
        self.assertEqual(request, before)

    def test_real_adapter_resolves_reference_inside_action_loop(self):
        from unittest.mock import patch
        from src.kb_agent.models import ChatModel
        model = ChatModel("https://example.invalid/v1", "test", "test-only-secret")
        actions = json.loads((ROOT / "tests/fixtures/mock/A01.json").read_text(encoding="utf-8"))
        with patch.object(model, "resolve_request", side_effect=AssertionError("No pre-classifier request")) as resolver, \
             patch.object(model, "next_action", side_effect=actions), \
             patch.object(model, "check_applicability", return_value={"missing_conditions": [], "reason": "Source has no extra condition"}), \
             patch.object(model, "review_result", return_value={"valid": True, "issues": []}):
            output, trace = Agent(model, ToolExecutor(self.kb)).run(self.request)
        resolver.assert_not_called()
        self.assertEqual(output["result"]["status"], "answered")
        self.assertEqual(output["model_calls"], 5)
        self.assertFalse(any(e["type"] == "request_resolution" for e in trace))

    def test_pre_retrieval_business_condition_guess_does_not_end_the_run(self):
        script = json.loads((ROOT / "tests/fixtures/mock/A01.json").read_text(encoding="utf-8"))
        class PrematureModel(ScriptedModel):
            def resolve_request(self, request, timeout):
                return {"action": "finish", "result": {"status": "needs_clarification", "reason_code": "missing_user_context",
                        "answer": "Need an unspecified condition", "gaps": ["unverified condition"], "citations": [], "follow_up_question": "Which condition?"}}
        output, trace = Agent(PrematureModel(script), ToolExecutor(self.kb)).run(self.request)
        self.assertEqual(output["result"]["status"], "answered")
        self.assertEqual(output["model_calls"], 4)
        self.assertTrue(any(e["type"] == "validation_error" and e["data"]["code"] == "premature_clarification" for e in trace))

    def test_unread_citation_feedback_names_the_required_tool_arguments(self):
        result = self.output["result"]
        with self.assertRaises(ContractError) as caught:
            validate_result(result, {})
        self.assertIn("document_id=D01", str(caught.exception))
        self.assertIn("passage_id=P01", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
