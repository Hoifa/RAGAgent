import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.kb_agent.agent import Agent
from src.kb_agent.knowledge import KnowledgeBase, ToolExecutor
from src.kb_agent.models import ChatModel, InvalidModelOutput, ModelError, QWEN_BASE_URL, read_stream_content, load_local_env
from src.kb_agent.contracts import ContractError


def sse(chunks, done=True):
    text = "".join("data: " + json.dumps(chunk, ensure_ascii=False) + "\r\n\r\n" for chunk in chunks)
    if done:
        text += "data: [DONE]\r\n\r\n"
    return io.BytesIO(text.encode("utf-8"))


class QwenTests(unittest.TestCase):
    def test_context_resolution_separates_current_question_from_historical_data(self):
        model = ChatModel("https://example.invalid/v1", "test", "test-only-secret")
        response = io.BytesIO(json.dumps({"choices": [{"message": {"content": '{"action":"continue","question":"resolved"}'}}]}).encode())
        request = {"question": "那材料呢？", "history": [{"role": "user", "content": "差旅报销期限？"}]}
        with patch.object(model._opener, "open", return_value=response) as call:
            model.resolve_request(request, 1)
        messages = json.loads(call.call_args[0][0].data)["messages"]
        self.assertEqual(len(messages), 2)
        self.assertEqual(json.loads(messages[-1]["content"]), {"current_question": request["question"], "history": request["history"]})
    def test_history_roles_reach_provider_without_becoming_evidence(self):
        model = ChatModel(QWEN_BASE_URL, "qwen-flash", "test-only-secret", False, True, True)
        history = [{"role": "user", "content": "差旅报销期限？"}, {"role": "assistant", "content": "历史回答不作事实证据"}]
        response = sse([{"choices": [{"delta": {"content": '{}'}, "finish_reason": "stop"}]}])
        with patch.object(model._opener, "open", return_value=response) as opened:
            model.next_action({"request": {"question": "那材料呢？", "history": history}}, 1)
        body = json.loads(opened.call_args[0][0].data)
        self.assertEqual(body["messages"][1:3], history)
        self.assertIn("历史仅用于指代", body["messages"][0]["content"])

    def test_user_selected_defaults_and_dashscope_key(self):
        with patch.dict("os.environ", {"DASHSCOPE_API_KEY": "test-only-secret"}, clear=True), patch("src.kb_agent.models.load_local_env", return_value={}):
            model = ChatModel.from_env()
        self.assertEqual(model.model_id, "qwen-flash")
        self.assertEqual(model.configuration["endpoint"], QWEN_BASE_URL + "/chat/completions")
        self.assertTrue(model.configuration["stream"])
        self.assertTrue(model.configuration["enable_thinking"])
        self.assertFalse(model.configuration["json_mode"])
        self.assertNotIn("test-only-secret", json.dumps(model.configuration))

    def test_non_thinking_can_use_json_mode(self):
        with patch.dict("os.environ", {"DASHSCOPE_API_KEY": "test-only-secret", "LLM_ENABLE_THINKING": "false"}, clear=True), patch("src.kb_agent.models.load_local_env", return_value={}):
            model = ChatModel.from_env()
        self.assertTrue(model.configuration["json_mode"])
        self.assertFalse(model.configuration["enable_thinking"])

    def test_experiment_override_does_not_modify_local_config(self):
        config = {"DASHSCOPE_API_KEY": "test-only-secret", "LLM_ENABLE_THINKING": "true", "LLM_JSON_MODE": "false"}
        with patch("src.kb_agent.models.load_local_env", return_value=dict(config)), patch.dict("os.environ", {}, clear=True):
            experiment = ChatModel.from_env({"LLM_ENABLE_THINKING": "false", "LLM_JSON_MODE": "true"})
            original = ChatModel.from_env()
        self.assertFalse(experiment.configuration["enable_thinking"])
        self.assertTrue(experiment.configuration["json_mode"])
        self.assertTrue(original.configuration["enable_thinking"])

    def test_sse_only_accumulates_content_and_ignores_usage(self):
        chunks = [{"choices": [{"delta": {"reasoning_content": "private-test-marker"}}]},
                  {"choices": [{"delta": {"content": '{"action":'}}]},
                  {"choices": []},
                  {"choices": [{"delta": {"content": '"tool"}'}, "finish_reason": "stop"}]}]
        content = read_stream_content(sse(chunks))
        self.assertEqual(json.loads(content), {"action": "tool"})
        self.assertNotIn("private-test-marker", content)

    def test_streamed_request_uses_top_level_thinking_flag(self):
        action = {"action": "tool", "tool_name": "search_documents", "arguments": {"query": "报销"}, "reason": "查找依据"}
        model = ChatModel(QWEN_BASE_URL, "qwen-flash", "test-only-secret", False, True, True)
        response = sse([{"choices": [{"delta": {"content": json.dumps(action)}, "finish_reason": "stop"}]}])
        with patch.object(model._opener, "open", return_value=response) as opened:
            self.assertEqual(model.next_action({}, 1), action)
        body = json.loads(opened.call_args[0][0].data)
        self.assertTrue(body["enable_thinking"])
        self.assertTrue(body["stream"])
        self.assertNotIn("extra_body", body)
        self.assertNotIn("response_format", body)

    def test_incomplete_or_length_limited_stream_is_rejected(self):
        for finish in (None, "length", "content_filter"):
            with self.subTest(finish=finish), self.assertRaises(InvalidModelOutput):
                read_stream_content(sse([{"choices": [{"delta": {"content": "{}"}, "finish_reason": finish}]}]))
        with self.assertRaises(InvalidModelOutput):
            read_stream_content(sse([{"choices": [{"delta": {"content": "{}"}, "finish_reason": "stop"}]}], done=False))

    def test_stream_error_does_not_echo_provider_text(self):
        with self.assertRaises(ModelError) as caught:
            read_stream_content(sse([{"error": {"message": "sensitive-test-marker"}}]))
        self.assertNotIn("sensitive-test-marker", str(caught.exception))

    def test_reasoning_not_in_agent_trace(self):
        result = {"status": "needs_clarification", "reason_code": "ambiguous_reference", "answer": "请说明查询事项。", "citations": [], "gaps": ["尚未明确查询事项"], "follow_up_question": "你想查询哪项制度？"}
        action = {"action": "finish", "result": result, "reason": "需要明确查询对象"}
        response = sse([{"choices": [{"delta": {"reasoning_content": "private-test-marker"}}]},
                        {"choices": [{"delta": {"content": json.dumps(action)}, "finish_reason": "stop"}]}])
        model = ChatModel(QWEN_BASE_URL, "qwen-flash", "test-only-secret", False, True, True)
        kb = KnowledgeBase.load(Path(__file__).resolve().parents[1] / "data/corpora/normal.json")
        with patch.object(model._opener, "open", return_value=response):
            output, events = Agent(model, ToolExecutor(kb)).run({"question": "那这个呢？"})
        for marker in ("private-test-marker", "test-only-secret", "reasoning_content"):
            self.assertNotIn(marker, json.dumps([output, events]))

    def test_local_env_is_data_not_code(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text('# local config\nDASHSCOPE_API_KEY="test-only-secret"\nLLM_MODEL=qwen-flash\n', encoding="utf-8")
            config = load_local_env(path)
            self.assertEqual(config["DASHSCOPE_API_KEY"], "test-only-secret")
            with patch("src.kb_agent.models.load_local_env", return_value=config), patch.dict("os.environ", {"LLM_MODEL": "qwen-flash-override"}, clear=True):
                self.assertEqual(ChatModel.from_env().model_id, "qwen-flash-override")
            path.write_text('DASHSCOPE_API_KEY=test\nDASHSCOPE_API_KEY=another\n', encoding="utf-8")
            with self.assertRaises(ContractError):
                load_local_env(path)


if __name__ == "__main__":
    unittest.main()
