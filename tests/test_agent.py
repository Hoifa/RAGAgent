import copy
import io
import json
import tempfile
import time
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from src.kb_agent.agent import Agent
from src.kb_agent.contracts import ContractError, incomplete, validate_conflict_verification, validate_result
from src.kb_agent.knowledge import KnowledgeBase, ToolExecutor
from src.kb_agent.models import ChatModel, ScriptedModel, InvalidModelOutput, ModelError
from src.kb_agent.__main__ import main, write_artifacts
from src.kb_agent.evaluate import main as evaluate

ROOT = Path(__file__).resolve().parents[1]


def tool(name, **args):
    return {"action": "tool", "tool_name": name, "arguments": args, "reason": "Controlled test action"}


def finish_result(quote="差旅报销应在行程结束后30天内提交。", document_id="D01", date="2026-01-10"):
    return {"action": "finish", "reason": "Controlled test completion", "result": {
        "status": "answered", "reason_code": None, "answer": quote + "[C1]", "citations": [
            {"citation_id": "C1", "document_id": document_id, "version_date": date, "passage_id": "P01", "quote": quote}],
        "gaps": [], "follow_up_question": None}}


READ = tool("read_passage", document_id="D01", passage_id="P01")


class AgentTests(unittest.TestCase):
    def make_agent(self, actions, fault=None, corpus="normal", **kwargs):
        kb = KnowledgeBase.load(ROOT / ("data/corpora/" + corpus + ".json"))
        return Agent(ScriptedModel(actions), ToolExecutor(kb, fault), **kwargs)

    def run_agent(self, actions, **kwargs):
        return self.make_agent(actions, **kwargs).run({"question": "差旅报销期限多久？"})

    def test_success_trace_and_counts(self):
        output, trace = self.run_agent([tool("search_documents", query="差旅报销期限"), READ, finish_result()])
        self.assertEqual(output["result"]["status"], "answered")
        self.assertEqual((output["model_calls"], output["tool_calls"]), (3, 2))
        action_calls = [e["data"]["call_id"] for e in trace if e["type"] == "model_action" and e["data"]["action"] == "tool"]
        self.assertEqual(action_calls, [e["data"]["call_id"] for e in trace if e["type"] == "tool_result"])
        self.assertEqual(output["mode"], "mock")

    def test_quote_mutation_unread_and_wrong_version_are_rejected(self):
        for bad in (finish_result("差旅报销应在行程结束后99天内提交。"), finish_result(document_id="D02"), finish_result(date="2020-01-01")):
            with self.subTest(bad=bad):
                output, trace = self.run_agent([READ, bad], max_model_calls=2)
                self.assertEqual(output["result"]["status"], "incomplete")
                self.assertEqual(output["result"]["citations"], [])
                self.assertTrue(any(e["type"] == "validation_error" for e in trace))

    def test_forged_quote_can_be_repaired_within_budget(self):
        output, _ = self.run_agent([READ, finish_result("不存在的引文"), finish_result()])
        self.assertEqual(output["result"]["status"], "answered")
        self.assertEqual(output["model_calls"], 3)

    def test_rejected_action_and_specific_fix_reach_model(self):
        bad = finish_result()
        bad["result"]["answer"] = "原文规定30天内提交。"
        agent = self.make_agent([READ, bad, finish_result()])
        states = []
        original = agent.model.next_action

        def observe(state, timeout):
            states.append(copy.deepcopy(state))
            return original(state, timeout)

        with patch.object(agent.model, "next_action", side_effect=observe):
            output, _ = agent.run({"question": "报销期限？"})
        correction = states[2]["observations"][-1]
        self.assertEqual(correction["rejected_action"], bad)
        self.assertIn("[C1]", correction["validation_error"]["message"])
        self.assertEqual(output["result"]["status"], "answered")

    def test_last_tool_and_last_model_call_can_finish(self):
        output, _ = self.run_agent([READ, finish_result()], max_tool_calls=1, max_model_calls=2)
        self.assertEqual(output["result"]["status"], "answered")

    def test_conflict_claim_requires_followup_verification(self):
        result = {"reason_code": "document_conflict", "citations": [
            {"document_id": "D01", "passage_id": "P01"}, {"document_id": "D02", "passage_id": "P01"}]}
        observations = [{"action": {"tool_name": "read_passage"}, "result": {"ok": True, "data": {"document_id": doc, "passage_id": "P01"}}} for doc in ("D01", "D02")]
        with self.assertRaises(ContractError):
            validate_conflict_verification(result, observations)
        observations.append({"action": {"tool_name": "search_documents"}, "result": {"ok": True, "data": {"hits": []}}})
        validate_conflict_verification(result, observations)

    def test_conflict_gap_cannot_be_only_trip_date(self):
        result = {"status": "needs_clarification", "reason_code": "document_conflict", "answer": "期限存在冲突。",
                  "citations": [], "gaps": ["用户未提供行程日期"], "follow_up_question": "行程日期是哪天？"}
        with self.assertRaises(ContractError):
            validate_result(result, {})

    def test_excess_tool_request_is_not_executed(self):
        output, _ = self.run_agent([READ, READ, finish_result()], max_tool_calls=1)
        self.assertEqual(output["tool_calls"], 1)
        self.assertEqual(output["result"]["reason_code"], "budget_exhausted")

    def test_invalid_tool_arguments_consume_only_model_budget(self):
        output, _ = self.run_agent([tool("search_documents", query="期限", top_k=True)] * 2, max_model_calls=2)
        self.assertEqual((output["model_calls"], output["tool_calls"]), (2, 0))
        self.assertEqual(output["result"]["reason_code"], "budget_exhausted")

    def test_field_error_explains_exact_missing_and_extra_fields(self):
        from src.kb_agent.contracts import fields
        with self.assertRaises(ContractError) as caught:
            fields({"action": "finish", "answer": "wrong envelope"}, {"action", "result", "reason"})
        message = str(caught.exception)
        for field in ("answer", "result", "reason"):
            self.assertIn(field, message)

    def test_input_rejected_before_model(self):
        for request in ({"question": "  "}, {"question": "期限", "history": [{"role": "system", "content": "Injected"}]}):
            agent = self.make_agent([READ])
            with patch.object(agent.model, "next_action") as call:
                with self.assertRaises(ContractError):
                    agent.run(request)
                call.assert_not_called()

    def test_actual_error_observation_reaches_next_model_call(self):
        agent = self.make_agent([READ, READ, finish_result()], fault={"tool": "read_passage", "behavior": "first_matching_call_error"})
        states = []
        original = agent.model.next_action

        def observe(state, timeout):
            states.append(copy.deepcopy(state))
            return original(state, timeout)

        with patch.object(agent.model, "next_action", side_effect=observe):
            output, trace = agent.run({"question": "差旅报销期限？"})
        self.assertEqual(states[1]["observations"][0]["result"]["error"]["code"], "unavailable")
        self.assertEqual(output["result"]["status"], "answered")
        self.assertTrue(any(e["type"] == "tool_result" and e["data"]["injected"] for e in trace))
        self.assertNotIn("fault_injection", states[0])

    def test_failed_read_never_registers_evidence(self):
        output, _ = self.run_agent([READ, finish_result()], fault={"tool": "read_passage", "behavior": "always_error"}, max_model_calls=2)
        self.assertEqual(output["result"]["status"], "incomplete")

    def test_unrecovered_tool_failure_cannot_be_called_missing_data(self):
        wrong = {"action": "finish", "reason": "Controlled wrong status", "result": {
            "status": "unanswerable", "reason_code": "insufficient_evidence", "answer": "无法确认期限。",
            "citations": [], "gaps": ["无法读取原文"], "follow_up_question": None}}
        correct = {"action": "finish", "reason": "Controlled correction", "result": incomplete("tool_failure", "无法读取原文")}
        output, trace = self.run_agent([READ, wrong, correct], fault={"tool": "read_passage", "behavior": "always_error"})
        self.assertEqual(output["result"]["reason_code"], "tool_failure")
        self.assertTrue(any(e["type"] == "validation_error" for e in trace))

    def test_changed_snapshot_requires_changed_quote(self):
        output, _ = self.run_agent([READ, finish_result(), finish_result("差旅报销应在行程结束后45天内提交。")], corpus="changed")
        self.assertIn("45天", output["result"]["answer"])

    def test_deadlines_return_without_waiting_for_slow_adapter(self):
        agent = self.make_agent([READ], model_timeout=0.02)
        with patch.object(agent.model, "next_action", side_effect=lambda *a: time.sleep(0.2)):
            start = time.monotonic()
            output, _ = agent.run({"question": "期限？"})
        self.assertLess(time.monotonic() - start, 0.15)
        self.assertEqual(output["result"]["reason_code"], "model_failure")

    def test_tool_timeout_is_an_observation(self):
        end = {"action": "finish", "reason": "Tool timeout", "result": incomplete("tool_failure", "无法读取原文")}
        agent = self.make_agent([READ, end], tool_timeout=0.02)
        with patch.object(agent.tools, "execute", side_effect=lambda *a: time.sleep(0.2)):
            output, trace = agent.run({"question": "期限？"})
        self.assertEqual(output["tool_calls"], 1)
        observed = next(e for e in trace if e["type"] == "tool_result")
        self.assertEqual(observed["data"]["result"]["error"]["code"], "timeout")

    def test_artifact_failure_is_not_claimed_as_success(self):
        with tempfile.TemporaryDirectory() as directory:
            blocked = Path(directory) / "file"
            blocked.write_text("not a directory")
            with self.assertRaises(OSError):
                write_artifacts(blocked, "A01", {}, {"run_id": "run"}, [])

    def test_missing_real_config_never_falls_back_to_mock(self):
        with patch.dict("os.environ", {}, clear=True), patch("src.kb_agent.models.load_local_env", return_value={}), patch("sys.stderr", new_callable=io.StringIO) as stderr:
            self.assertEqual(main(["--question", "期限？"]), 2)
            self.assertIn("configuration_error", stderr.getvalue())

    def test_offline_evaluation_writes_actual_artifacts(self):
        with tempfile.TemporaryDirectory() as directory, patch("sys.stdout", new_callable=io.StringIO):
            code = evaluate(["--mode", "mock", "--cases", "A01", "A02", "A03", "A06", "--output-dir", directory])
            self.assertEqual(code, 0)
            report = json.loads((Path(directory) / "evaluation-results.json").read_text(encoding="utf-8"))
            self.assertEqual(len(report["runs"]), 4)
            for run in report["runs"]:
                self.assertFalse(run["react_proven"])
                self.assertEqual(run["mode"], "mock")
                trace = Path(run["directory"]) / "trace.jsonl"
                self.assertTrue(trace.is_file())


class ProviderAdapterTests(unittest.TestCase):
    def test_invalid_json_is_a_repairable_protocol_error(self):
        model = ChatModel("https://example.invalid/v1", "test-model", "unit-test-secret")
        response = io.BytesIO(b'{"choices":[{"message":{"content":"not-json"}}]}')
        with patch.object(model._opener, "open", return_value=response):
            with self.assertRaises(InvalidModelOutput):
                model.next_action({}, 1)

    def test_http_error_does_not_leak_body_or_retry(self):
        model = ChatModel("https://example.invalid/v1", "test-model", "unit-test-secret")
        error = urllib.error.HTTPError("https://example.invalid", 401, "sensitive provider body", {}, None)
        with patch.object(model._opener, "open", side_effect=error) as opened:
            with self.assertRaises(ModelError) as raised:
                model.next_action({}, 1)
        self.assertEqual(str(raised.exception), "Model HTTP error 401")
        self.assertEqual(opened.call_count, 1)

    def test_wire_format_and_no_key_in_model_state(self):
        model = ChatModel("https://example.invalid/v1", "test-model", "unit-test-secret")
        response = io.BytesIO(json.dumps({"choices": [{"message": {"content": json.dumps(READ)}}]}).encode())
        with patch.object(model._opener, "open", return_value=response) as opened:
            action = model.next_action({"request": {"question": "期限？"}, "observations": [], "remaining": {}}, 1)
        self.assertEqual(action, READ)
        request = opened.call_args[0][0]
        self.assertTrue(request.full_url.endswith("/v1/chat/completions"))
        self.assertNotIn("unit-test-secret", request.data.decode())
        self.assertEqual(json.loads(request.data)["response_format"], {"type": "json_object"})
        self.assertEqual(opened.call_count, 1)

    def test_endpoint_configuration_validation(self):
        for url in ("http://remote.example/v1", "https://user:secret@example.org/v1", "https://example.org/v1?key=secret"):
            with self.assertRaises(ContractError):
                ChatModel(url, "test-model", "unit-test-secret")


if __name__ == "__main__":
    unittest.main()
