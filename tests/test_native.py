import io
import json
import unittest
from unittest.mock import patch

from src.kb_agent.models import ChatModel, InvalidModelOutput
from src.kb_agent.native import messages_for_state, tool_definitions
from src.kb_agent.contracts import validate_action


class NativeTests(unittest.TestCase):
    def model(self):
        return ChatModel("https://example.invalid/v1", "qwen-flash", "test-only-secret", True, True, False, "native")

    def test_native_call_is_decoded_without_fabricating_decision_reason(self):
        payload = {"choices": [{"finish_reason": "tool_calls", "message": {"tool_calls": [
            {"id": "provider-id", "function": {"name": "search_documents", "arguments": json.dumps({"query": "报销期限", "reason": "查找制度"})}}]}}]}
        model = self.model()
        with patch.object(model._opener, "open", return_value=io.BytesIO(json.dumps(payload).encode())) as opened:
            action = model.next_action({"request": {"question": "期限？"}}, 1)
        validate_action(action)
        self.assertEqual(action["reason"], "查找制度")
        self.assertEqual(action["provider_call_id"], "provider-id")
        self.assertEqual(action["arguments"], {"query": "报销期限"})
        wire = json.loads(opened.call_args[0][0].data)
        self.assertEqual(wire["tool_choice"], "auto")
        self.assertFalse(wire["parallel_tool_calls"])
        self.assertFalse(wire["stream"])
        self.assertNotIn("response_format", wire)

    def test_tool_messages_preserve_provider_call_identity_and_result(self):
        observation = {"action": {"action": "tool", "tool_name": "search_documents", "arguments": {"query": "x"}, "reason": "查找", "provider_call_id": "provider-id"},
                       "call_id": "tool-1", "result": {"ok": True, "data": {"hits": []}}}
        messages = messages_for_state({"request": {"question": "x"}, "observations": [observation]})
        self.assertEqual(messages[2]["tool_calls"][0]["id"], "provider-id")
        self.assertEqual(messages[3]["role"], "tool")
        self.assertEqual(messages[3]["tool_call_id"], "provider-id")
        self.assertEqual(json.loads(messages[3]["content"])["result"], observation["result"])

    def test_unavailable_actions_are_not_offered_after_stall(self):
        tools = tool_definitions({"progress": {"no_new_candidate_searches": 2, "unread_candidates": []}})
        self.assertEqual([t["function"]["name"] for t in tools], ["finish"])
        tools = tool_definitions({"progress": {"unread_candidates": [{"document_id": "D02", "passage_id": "P01"}]}})
        read = next(t for t in tools if t["function"]["name"] == "read_passage")
        self.assertEqual(read["function"]["parameters"]["properties"]["document_id"]["enum"], ["D02"])

    def test_multiple_function_calls_are_rejected_without_executing_one(self):
        call = {"id": "id", "function": {"name": "finish", "arguments": "{}"}}
        payload = {"choices": [{"finish_reason": "tool_calls", "message": {"tool_calls": [call, call]}}]}
        model = self.model()
        with patch.object(model._opener, "open", return_value=io.BytesIO(json.dumps(payload).encode())):
            with self.assertRaises(InvalidModelOutput):
                model.next_action({"request": {"question": "x"}}, 1)

    def test_text_only_response_repair_forces_structure_not_a_business_status(self):
        result = {"status": "unanswerable", "reason_code": "insufficient_evidence", "answer": "资料不足", "citations": [], "gaps": ["缺少制度"], "follow_up_question": None}
        payload = {"choices": [{"finish_reason": "tool_calls", "message": {"tool_calls": [
            {"id": "repaired-id", "function": {"name": "finish", "arguments": json.dumps(result)}}]}}]}
        model = self.model()
        state = {"request": {"question": "x"}, "observations": [{"validation_error": {"message": "native_call_missing:repair"}}]}
        with patch.object(model._opener, "open", return_value=io.BytesIO(json.dumps(payload).encode())) as opened:
            action = model.next_action(state, 1)
        wire = json.loads(opened.call_args[0][0].data)
        self.assertEqual(wire["tool_choice"], {"type": "function", "function": {"name": "finish"}})
        self.assertEqual(action["result"], result)
        status_schema = wire["tools"][0]["function"]["parameters"]["properties"]["status"]
        self.assertEqual(len(status_schema["enum"]), 4)


if __name__ == "__main__":
    unittest.main()
