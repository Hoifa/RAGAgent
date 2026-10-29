"""Regressions from actual stage-three failures, with controlled model outputs."""
import copy
import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from src.kb_agent.agent import Agent
from src.kb_agent.contracts import validate_action, validate_result, ContractError, validate_answer_dates
from src.kb_agent.knowledge import KnowledgeBase, ToolExecutor
from src.kb_agent.models import ChatModel, ScriptedModel
from src.kb_agent.progress import summarize_progress
from src.kb_agent.assessment import assess_case
from src.kb_agent.evaluate import append_report
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def search(query):
    return {"action": "tool", "tool_name": "search_documents", "arguments": {"query": query}, "reason": "查找依据"}


def end(status="unanswerable", reason="insufficient_evidence"):
    return {"action": "finish", "result": {"status": status, "reason_code": reason,
            "answer": "当前资料没有该问题的依据。", "citations": [], "gaps": ["缺少相应制度资料"], "follow_up_question": None}}


class ReliabilityTests(unittest.TestCase):
    def run_actions(self, actions, **limits):
        kb = KnowledgeBase.load(ROOT / "data/corpora/normal.json")
        return Agent(ScriptedModel(actions), ToolExecutor(kb), **limits).run({"question": "知识库未覆盖的问题"})

    def test_finish_without_redundant_reason_preserves_model_basis(self):
        output, trace = self.run_actions([end()])
        self.assertEqual(output["result"]["status"], "unanswerable")
        event = next(e for e in trace if e["type"] == "model_action")
        self.assertEqual(event["data"]["decision_basis"], end()["result"]["answer"])
        self.assertEqual(event["data"]["decision_basis_source"], "model_result.answer")
        self.assertNotIn("reason", event["data"])

    def test_tool_still_requires_model_action_purpose(self):
        action = search("育儿假")
        del action["reason"]
        with self.assertRaises(ContractError):
            validate_action(action)

    def test_no_citations_error_explains_removing_placeholder(self):
        result = end()["result"]
        result["answer"] += "[C1]"
        with self.assertRaises(ContractError) as raised:
            validate_result(result, {})
        self.assertIn("删除", str(raised.exception))

    def test_repeated_no_progress_search_is_not_executed(self):
        actions = [search("育儿假"), search("育儿假"), search("育儿假"), end()]
        output, trace = self.run_actions(actions)
        self.assertEqual(output["tool_calls"], 2)
        self.assertEqual(output["result"]["status"], "unanswerable")
        self.assertTrue(any(e["type"] == "validation_error" and e["data"]["code"] == "no_progress" for e in trace))

    def test_three_consecutive_invalid_outputs_stop_before_global_limit(self):
        output, _ = self.run_actions([{"wrong": "shape"}] * 8)
        self.assertEqual(output["model_calls"], 3)
        self.assertEqual(output["tool_calls"], 0)
        self.assertEqual(output["result"]["reason_code"], "invalid_model_output")

    def test_duplicate_successful_read_does_not_waste_tool_budget(self):
        read = {"action": "tool", "tool_name": "read_passage", "arguments": {"document_id": "D01", "passage_id": "P01"}, "reason": "读取原文"}
        output, trace = self.run_actions([read, read, end()])
        self.assertEqual(output["tool_calls"], 1)
        self.assertTrue(any(e["type"] == "validation_error" and e["data"]["code"] == "no_progress" for e in trace))

    def test_new_candidates_reset_progress_and_errors_do_not_look_like_empty(self):
        def observation(query, hits, ok=True):
            return {"action": search(query), "result": {"ok": ok, "data": {"hits": hits} if ok else None}}
        a = {"document_id": "D01", "passage_id": "P01"}
        b = {"document_id": "D02", "passage_id": "P01"}
        items = [observation("a", [a]), observation("a", [a]), observation("b", [b])]
        self.assertEqual(summarize_progress(items)["no_new_candidate_searches"], 0)
        self.assertEqual(summarize_progress([observation("x", [], False)])["consecutive_empty_searches"], 0)

    def test_provider_receives_question_then_actual_observations_in_order(self):
        action = search("报销")
        state = {"request": {"question": "那材料呢？", "history": [{"role": "user", "content": "讨论差旅报销"}]},
                 "observations": [{"action": action, "call_id": "tool-1", "result": {"ok": True, "data": {"hits": []}}}],
                 "remaining": {"model_calls": 5}, "available_evidence": []}
        response = io.BytesIO(json.dumps({"choices": [{"message": {"content": json.dumps(end())}}]}).encode())
        model = ChatModel("https://example.invalid/v1", "test", "test-only-secret")
        before = copy.deepcopy(state)
        with patch.object(model._opener, "open", return_value=response) as call:
            model.next_action(state, 1)
        messages = json.loads(call.call_args[0][0].data)["messages"]
        self.assertEqual(messages[2], {"role": "user", "content": "那材料呢？"})
        self.assertEqual(json.loads(messages[3]["content"]), action)
        self.assertEqual(json.loads(messages[4]["content"])["call_id"], "tool-1")
        self.assertIn("runtime", json.loads(messages[5]["content"]))
        self.assertEqual(state, before)

    def test_review_rejection_is_feedback_not_an_accepted_answer(self):
        from test_agent import READ, finish_result
        class ReviewingModel(ScriptedModel):
            def __init__(self):
                super().__init__([READ, finish_result(), finish_result()])
                self.reviews = 0
            def review_result(self, request, result, evidence, observations, timeout):
                self.reviews += 1
                return {"valid": self.reviews > 1, "issues": ["Controlled rejected conclusion"] if self.reviews == 1 else []}
        model = ReviewingModel()
        kb = KnowledgeBase.load(ROOT / "data/corpora/normal.json")
        output, trace = Agent(model, ToolExecutor(kb)).run({"question": "未覆盖的问题"})
        self.assertEqual(output["model_calls"], 5)
        reviews = [e["data"]["valid"] for e in trace if e["type"] == "evidence_review"]
        self.assertEqual(reviews, [False, True])
        self.assertEqual(output["result"]["status"], "answered")

    def test_review_cannot_run_beyond_model_budget(self):
        from test_agent import READ, finish_result
        class ReviewingModel(ScriptedModel):
            def review_result(self, *args):
                raise AssertionError("Should not be called")
        kb = KnowledgeBase.load(ROOT / "data/corpora/normal.json")
        output, _ = Agent(ReviewingModel([READ, finish_result()]), ToolExecutor(kb), max_model_calls=2).run({"question": "未覆盖的问题"})
        self.assertEqual(output["model_calls"], 2)
        self.assertEqual(output["result"]["reason_code"], "budget_exhausted")

    def test_context_resolution_uses_only_request_and_can_clarify_without_tools(self):
        class ResolvingModel(ScriptedModel):
            def resolve_request(self, request, timeout):
                self.seen = copy.deepcopy(request)
                result = end("needs_clarification", "ambiguous_reference")
                result["result"]["follow_up_question"] = "请说明事项。"
                return result
        model = ResolvingModel([search("must-not-execute")])
        kb = KnowledgeBase.load(ROOT / "data/corpora/normal.json")
        request = {"question": "那需要什么材料？"}
        output, trace = Agent(model, ToolExecutor(kb)).run(request)
        self.assertEqual(model.seen, request)
        self.assertEqual((output["model_calls"], output["tool_calls"]), (1, 0))
        self.assertEqual(output["result"]["status"], "needs_clarification")
        self.assertTrue(any(e["type"] == "request_resolution" for e in trace))

    def test_context_resolver_cannot_invent_a_business_answer(self):
        from test_agent import finish_result
        class ResolvingModel(ScriptedModel):
            def resolve_request(self, request, timeout):
                return finish_result()
        kb = KnowledgeBase.load(ROOT / "data/corpora/normal.json")
        output, _ = Agent(ResolvingModel([search("must-not-execute")]), ToolExecutor(kb)).run({"question": "期限？"})
        self.assertEqual(output["result"]["reason_code"], "invalid_model_output")
        self.assertEqual(output["tool_calls"], 0)

    def test_missing_replacement_evidence_fails_even_when_status_matches(self):
        from test_agent import READ, finish_result
        kb = KnowledgeBase.load(ROOT / "data/corpora/normal.json")
        output, trace = Agent(ScriptedModel([READ, finish_result()]), ToolExecutor(kb)).run({"question": "期限？"})
        case = {"expected_status": "answered", "required_document_ids": ["D01"],
                "assertions": {"required_passages": [{"document_id": "D01", "passage_id": "P02"}]}}
        checks = assess_case(case, {}, output, trace, kb)
        self.assertTrue(checks["status_matches"])
        self.assertFalse(checks["required_passages_cited"])

    def test_atomic_summary_preserves_previous_completed_runs(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            append_report(path, {"run_id": "first"})
            append_report(path, {"run_id": "second"})
            self.assertEqual([r["run_id"] for r in json.loads(path.read_text(encoding="utf-8"))["runs"]], ["first", "second"])
            self.assertEqual(list(Path(directory).glob("*.tmp")), [])

    def test_reviewer_does_not_inherit_rejected_answers_or_old_errors(self):
        model = ChatModel("https://example.invalid/v1", "test", "test-only-secret")
        response = io.BytesIO(json.dumps({"choices": [{"message": {"content": '{"valid":true,"issues":[]}'}}]}).encode())
        observations = [{"rejected_action": {"bad": "old-answer-marker"}, "validation_error": {"message": "old-error-marker"}},
                        {"action": search("x"), "result": {"ok": True, "data": {"hits": []}}}]
        with patch.object(model._opener, "open", return_value=response) as call:
            model.review_result({"question": "x"}, end()["result"], {}, observations, 1)
        wire = call.call_args[0][0].data.decode()
        self.assertNotIn("old-answer-marker", wire)
        self.assertNotIn("old-error-marker", wire)
        context = json.loads(json.loads(wire)["messages"][1]["content"])
        self.assertEqual(len(context["tool_observations"]), 1)

    def test_cli_explicit_profile_does_not_require_editing_secret_config(self):
        from src.kb_agent.__main__ import main
        script = json.loads((ROOT / "tests/fixtures/mock/A01.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as directory, patch("sys.stdout", new_callable=io.StringIO), patch("sys.stderr", new_callable=io.StringIO):
            with patch("src.kb_agent.__main__.ChatModel.from_env", return_value=ScriptedModel(script)) as factory:
                code = main(["--mode", "real", "--thinking-mode", "off", "--input", str(ROOT / "tests/fixtures/inputs/A01.json"),
                             "--corpus", str(ROOT / "data/corpora/normal.json"), "--output-dir", directory])
            self.assertEqual(code, 0)
            self.assertEqual(factory.call_args[0][0], {"LLM_ENABLE_THINKING": "false", "LLM_JSON_MODE": "true"})

    def test_missing_applicability_condition_rejects_success_and_allows_question(self):
        from test_agent import READ, finish_result
        class ScopeModel(ScriptedModel):
            def check_applicability(self, request, evidence, timeout):
                return {"missing_conditions": ["所属地区"], "reason": "不同地区适用不同规则"}
        clarification = end("needs_clarification", "missing_user_context")
        clarification["result"]["follow_up_question"] = "您属于哪个地区？"
        kb = KnowledgeBase.load(ROOT / "data/corpora/scoped.json")
        output, trace = Agent(ScopeModel([READ, finish_result(), clarification]), ToolExecutor(kb)).run({"question": "报销期限？"})
        self.assertEqual(output["result"]["status"], "needs_clarification")
        self.assertEqual(output["model_calls"], 4)
        self.assertTrue(any(e["type"] == "applicability_review" for e in trace))

    def test_applicability_check_does_not_receive_the_proposed_answer(self):
        model = ChatModel("https://example.invalid/v1", "test", "test-only-secret")
        response = io.BytesIO(json.dumps({"choices": [{"message": {"content": '{"missing_conditions":[]}'}}]}).encode())
        with patch.object(model._opener, "open", return_value=response) as call:
            model.check_applicability({"question": "期限？"}, {}, 1)
        context = json.loads(json.loads(call.call_args[0][0].data)["messages"][1]["content"])
        self.assertEqual(set(context), {"request", "read_evidence"})

    def test_citation_dependency_requires_successful_read_and_explicit_quote(self):
        kb = KnowledgeBase.load(ROOT / "data/corpora/resolved.json")
        rule = kb.read("D06", "P01")["data"]
        support = kb.read("D06", "P02")["data"]
        def cite(source, cid):
            return {"citation_id": cid, "document_id": source["document_id"], "passage_id": source["passage_id"], "version_date": source["version_date"], "quote": source["text"]}
        result = {"status": "answered", "reason_code": None, "answer": "15天[C1]。", "citations": [cite(rule, "C1")], "gaps": [], "follow_up_question": None}
        evidence = {("D06", "P01"): rule}
        with self.assertRaises(ContractError):
            validate_result(result, evidence)
        evidence[("D06", "P02")] = support
        with self.assertRaises(ContractError):
            validate_result(result, evidence)
        result["citations"].append(cite(support, "C2"))
        result["answer"] += "替代依据[C2]。"
        validate_result(result, evidence)

    def test_read_failure_cannot_be_misrepresented_as_missing_user_context(self):
        from test_agent import READ
        wrong = end("needs_clarification", "missing_user_context")
        wrong["result"]["follow_up_question"] = "请用户提供无法读取的制度。"
        correct = end("incomplete", "tool_failure")
        kb = KnowledgeBase.load(ROOT / "data/corpora/normal.json")
        tools = ToolExecutor(kb, {"tool": "read_passage", "behavior": "always_error"})
        output, trace = Agent(ScriptedModel([READ, wrong, correct]), tools).run({"question": "报销期限？"})
        self.assertEqual(output["result"]["reason_code"], "tool_failure")
        self.assertTrue(any(e["type"] == "validation_error" for e in trace))

    def test_unrequested_calendar_deadline_does_not_borrow_authority_from_duration(self):
        kb = KnowledgeBase.load(ROOT / "data/corpora/resolved.json")
        source = kb.read("D06", "P01")["data"]
        evidence = {("D06", "P01"): source}
        result = {"status": "answered", "answer": "应于2026年5月25日提交。", "citations": [{"document_id": "D06", "passage_id": "P01", "quote": source["text"]}]}
        request = {"question": "2026年5月10日结束出差，期限多久？"}
        with self.assertRaises(ContractError):
            validate_answer_dates(result, evidence, request)
        result["answer"] = "行程结束日期2026年5月10日满足2026年4月1日之后的条件，期限15天。"
        validate_answer_dates(result, evidence, request)

    def test_assistant_history_is_not_a_source_for_absolute_dates(self):
        result = {"status": "answered", "answer": "截止日期2026-05-25。", "citations": []}
        request = {"question": "请核实期限", "history": [{"role": "assistant", "content": "截止日期2026-05-25"}]}
        with self.assertRaises(ContractError):
            validate_answer_dates(result, {}, request)


if __name__ == "__main__":
    unittest.main()
