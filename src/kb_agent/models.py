"""Configurable Chat Completions adapter and explicitly scripted offline model."""
import copy
import hashlib
import json
import os
import socket
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from .contracts import ContractError, nonempty, require
from .prompts import SYSTEM_PROMPT as ACTION_PROMPT, REVIEW_PROMPT, CONTEXT_PROMPT, APPLICABILITY_PROMPT
from .native import NATIVE_PROMPT, tool_definitions, messages_for_state


class ModelError(RuntimeError):
    """Safe operational error: never include response bodies or credentials."""


class InvalidModelOutput(ValueError):
    pass


QWEN_BASE_URL = "https://cn-beijing.maas.qianwenaiapi.com/compatible-mode/v1"
CONFIG_NAMES = {"LLM_BASE_URL", "LLM_MODEL", "LLM_API_KEY", "DASHSCOPE_API_KEY",
                "LLM_JSON_MODE", "LLM_STREAM", "LLM_ENABLE_THINKING", "LLM_ACTION_PROTOCOL"}


def load_local_env(path=None):
    """Read local config without interpolation, code execution or secret logging."""
    path = Path(path) if path is not None else Path(__file__).resolve().parents[2] / ".env"
    if not path.exists():
        return {}
    values = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        require("=" in line, "Invalid local .env line; use NAME=value")
        name, value = line.split("=", 1)
        name, value = name.strip(), value.strip()
        require(name in CONFIG_NAMES, "Unsupported local .env variable")
        if value.startswith(("'", '"')):
            require(len(value) >= 2 and value[-1] == value[0], "Unclosed quote in local .env")
            value = value[1:-1]
        require(name not in values, "Duplicate local .env variable")
        values[name] = value
    return values


def env_bool(config, name, default):
    value = config.get(name, str(default)).lower()
    require(value in ("true", "false"), name + " must be true or false")
    return value == "true"


def read_stream_content(response):
    """Read SSE content only. Reasoning fields are neither accumulated nor logged."""
    content, data_lines = [], []
    total = 0
    stopped = False

    def consume(lines):
        nonlocal stopped
        data = "\n".join(lines)
        if data == "[DONE]":
            if not stopped:
                raise InvalidModelOutput("Stream ended without a successful completion")
            return True
        chunk = json.loads(data)
        if "error" in chunk:
            raise ModelError("Model returned a streaming error")
        choices = chunk.get("choices", [])
        if not choices:  # Usage-only or metadata chunk.
            return False
        choice = choices[0]
        finish = choice.get("finish_reason")
        if finish is not None:
            if finish != "stop":
                raise InvalidModelOutput("Model stream did not complete normally")
            stopped = True
        part = choice.get("delta", {}).get("content")
        if part is not None:
            if not isinstance(part, str):
                raise InvalidModelOutput("Stream content must be text")
            content.append(part)
        # Never access or append delta.reasoning_content.
        return False

    while True:
        raw_line = response.readline(65_537)
        if not raw_line:
            break
        total += len(raw_line)
        if len(raw_line) > 65_536 or total > 2_000_000:
            raise InvalidModelOutput("Model stream exceeds size limit")
        line = raw_line.decode("utf-8").rstrip("\r\n")
        if not line:
            if data_lines:
                done = consume(data_lines)
                data_lines = []
                if done:
                    return "".join(content)
        elif line.startswith("data:"):
            data_lines.append(line[5:].lstrip(" "))
        # SSE comments/event/id fields carry no answer text.
    if data_lines and consume(data_lines):
        return "".join(content)
    raise InvalidModelOutput("Model stream was interrupted before DONE")


# Backwards-compatible import; active prompt lives in prompts.py.
SYSTEM_PROMPT = ACTION_PROMPT


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class ChatModel:
    mode = "real"
    # A separate classifier over-clarified clear policy questions in real
    # regression. Let the same bounded action loop choose clarify or search.
    use_reference_classifier = False

    def __init__(self, base_url, model, api_key, json_mode=True, stream=False, enable_thinking=None, action_protocol="json"):
        require(all(nonempty(v) for v in (base_url, model, api_key)), "Set the local API key: DASHSCOPE_API_KEY for Qwen, or LLM_API_KEY")
        parsed = urllib.parse.urlsplit(base_url)
        require(parsed.scheme in ("https", "http") and bool(parsed.hostname), "Invalid LLM_BASE_URL")
        require(not parsed.username and not parsed.password and not parsed.query and not parsed.fragment, "Base URL must not embed credentials or query parameters")
        require(parsed.scheme == "https" or parsed.hostname in ("localhost", "127.0.0.1", "::1"), "Use HTTPS for remote model endpoints")
        self._endpoint = base_url.rstrip("/") + "/chat/completions"
        self._api_key = api_key
        self.model_id = model
        self._json_mode = json_mode
        self._stream = stream
        self._enable_thinking = enable_thinking
        require(action_protocol in ("json", "native"), "Invalid action protocol")
        require(action_protocol != "native" or enable_thinking is not True, "Native action mode currently requires non-thinking configuration")
        self._action_protocol = action_protocol
        self._opener = urllib.request.build_opener(NoRedirect())

    @classmethod
    def from_env(cls, overrides=None):
        # User-selected project defaults, not automatic model selection.
        config = dict(load_local_env())
        config.update({key: value for key, value in os.environ.items() if key in CONFIG_NAMES})
        if overrides:
            require(set(overrides) <= CONFIG_NAMES, "Unsupported model configuration override")
            config.update(overrides)
        model = config.get("LLM_MODEL", "qwen-flash")
        is_qwen = model.lower().startswith("qwen")
        thinking = env_bool(config, "LLM_ENABLE_THINKING", True) if is_qwen or "LLM_ENABLE_THINKING" in config else None
        json_mode = env_bool(config, "LLM_JSON_MODE", not thinking)
        stream = env_bool(config, "LLM_STREAM", is_qwen)
        base_url = config.get("LLM_BASE_URL", QWEN_BASE_URL if is_qwen else "")
        key = config.get("LLM_API_KEY") or (config.get("DASHSCOPE_API_KEY", "") if is_qwen else "")
        protocol = config.get("LLM_ACTION_PROTOCOL", "auto")
        require(protocol in ("auto", "json", "native"), "LLM_ACTION_PROTOCOL must be auto, json or native")
        if protocol == "auto":
            protocol = "native" if is_qwen and thinking is False else "json"
        return cls(base_url, model, key, json_mode, stream, thinking, protocol)

    @property
    def configuration(self):
        """Public reproducibility metadata only; never expose the API key."""
        return {"endpoint": self._endpoint, "stream": self._stream,
                "enable_thinking": self._enable_thinking, "json_mode": self._json_mode,
                "prompt_revision": hashlib.sha256((NATIVE_PROMPT if self._action_protocol == "native" else ACTION_PROMPT).encode("utf-8")).hexdigest(),
                "action_protocol": self._action_protocol, "action_stream": self._stream if self._action_protocol == "json" else False,
                "review_prompt_revision": hashlib.sha256(REVIEW_PROMPT.encode("utf-8")).hexdigest(),
                "context_prompt_revision": hashlib.sha256(CONTEXT_PROMPT.encode("utf-8")).hexdigest(),
                "applicability_prompt_revision": hashlib.sha256(APPLICABILITY_PROMPT.encode("utf-8")).hexdigest(),
                "evidence_review": "answered_only",
                "reference_resolution": "optional_classifier" if self.use_reference_classifier else "action_loop",
                "conversation_protocol": "native-tool-messages-v1" if self._action_protocol == "native" else "chronological-v2"}

    def next_action(self, state, timeout):
        # No case ID, corpus filename, fixture expectations, fault configuration,
        # API keys or provider responses are included in the model's state.
        history = state.get("request", {}).get("history", [])
        # Preserve conversational roles for reference resolution. The system
        # instruction still requires re-reading documents for factual claims.
        require(isinstance(history, list) and all(isinstance(m, dict) and m.get("role") in ("user", "assistant")
                and nonempty(m.get("content")) and set(m) == {"role", "content"} for m in history), "Invalid model history")
        if self._action_protocol == "native":
            observations = state.get("observations", [])
            last_error = observations[-1].get("validation_error", {}).get("message", "") if observations else ""
            repair_finish = last_error.startswith("native_call_missing:")
            tools = tool_definitions(state)
            if repair_finish:
                tools = [tool for tool in tools if tool["function"]["name"] == "finish"]
            return self._request(messages_for_state(state), timeout, tools, repair_finish)
        messages = [{"role": "system", "content": ACTION_PROMPT}] + copy.deepcopy(history)
        current_question = state.get("request", {}).get("question")
        if current_question is not None:
            messages.append({"role": "user", "content": current_question})
        for observation in state.get("observations", []):
            prior = observation.get("action", observation.get("rejected_action"))
            if prior is not None:
                messages.append({"role": "assistant", "content": json.dumps(prior, ensure_ascii=False)})
            returned = {k: v for k, v in observation.items() if k not in ("action", "rejected_action")}
            messages.append({"role": "user", "content": json.dumps(returned, ensure_ascii=False)})
        runtime = {key: value for key, value in state.items() if key not in ("request", "observations")}
        messages.append({"role": "user", "content": json.dumps({"runtime": runtime}, ensure_ascii=False)})
        return self._request(messages, timeout)

    def review_result(self, request, result, evidence, observations, timeout):
        # Review only the current candidate and real tool results. Rejected
        # answers and old validation messages would bias the reviewer toward
        # repeating an already-fixed error.
        actual_observations = [item for item in observations if "result" in item and "action" in item]
        review_request = copy.deepcopy(request)
        review_request["history"] = [m for m in request.get("history", []) if m["role"] == "user"]
        context = {"request": review_request, "candidate_result": result,
                   "read_evidence": list(evidence.values()), "tool_observations": actual_observations}
        return self._request([{"role": "system", "content": REVIEW_PROMPT},
                              {"role": "user", "content": json.dumps(context, ensure_ascii=False)}], timeout)

    def resolve_request(self, request, timeout):
        # This is a reference-classification task, not another conversational
        # answer. Explicit fields keep history from becoming the active task.
        messages = [{"role": "system", "content": CONTEXT_PROMPT},
                    {"role": "user", "content": json.dumps({"current_question": request["question"],
                     "history": request.get("history", [])}, ensure_ascii=False)}]
        return self._request(messages, timeout)

    def check_applicability(self, request, evidence, timeout):
        # Do not show the proposed answer: the check must not simply agree
        # with a confident conditional answer that omitted a needed question.
        review_request = copy.deepcopy(request)
        review_request["history"] = [m for m in request.get("history", []) if m["role"] == "user"]
        context = {"request": review_request, "read_evidence": list(evidence.values())}
        return self._request([{"role": "system", "content": APPLICABILITY_PROMPT},
                              {"role": "user", "content": json.dumps(context, ensure_ascii=False)}], timeout)

    def _request(self, messages, timeout, native_tools=None, force_finish=False):
        streaming = self._stream and native_tools is None
        payload = {"model": self.model_id, "messages": messages, "stream": streaming}
        if native_tools is not None:
            choice = {"type": "function", "function": {"name": "finish"}} if force_finish else "auto"
            payload.update(tools=native_tools, tool_choice=choice, parallel_tool_calls=False)
        elif self._json_mode:
            payload["response_format"] = {"type": "json_object"}
        if self._enable_thinking is not None:
            # SDK extra_body fields are top-level keys on the HTTP wire.
            payload["enable_thinking"] = self._enable_thinking
        request = urllib.request.Request(self._endpoint, data=json.dumps(payload).encode("utf-8"),
                                         headers={"Content-Type": "application/json", "Authorization": "Bearer " + self._api_key})
        try:
            # urllib has no automatic application-level retry. Every call is counted.
            with self._opener.open(request, timeout=timeout) as response:
                if streaming:
                    content = read_stream_content(response)
                else:
                    raw = response.read(2_000_001)
                    if len(raw) > 2_000_000:
                        raise InvalidModelOutput("Model response exceeds size limit")
                    envelope = json.loads(raw)
                    choice = envelope["choices"][0]
                    if choice.get("finish_reason") not in (None, "stop", "tool_calls" if native_tools else "stop"):
                        raise InvalidModelOutput("Model response did not complete normally")
                    if native_tools is not None:
                        calls = choice["message"].get("tool_calls", [])
                        if not calls:
                            raise InvalidModelOutput("native_call_missing:模型已回复文本但未提交结构。下一轮请使用finish函数填写状态、答案、引用和缺口，不输出普通文本。")
                        if len(calls) != 1:
                            raise InvalidModelOutput("native_multiple_calls:每轮只允许一个函数调用，不执行多个并行调用。")
                        call = calls[0]
                        name = call["function"]["name"]
                        arguments = json.loads(call["function"]["arguments"])
                        if not isinstance(arguments, dict):
                            raise InvalidModelOutput("Function arguments must be an object")
                        note = arguments.pop("reason", None)
                        action = {"action": "finish", "result": arguments} if name == "finish" else {"action": "tool", "tool_name": name, "arguments": arguments}
                        action["provider_call_id"] = call["id"]
                        if note is not None:
                            action["reason"] = note
                        return action
                    content = choice["message"]["content"]
            if not isinstance(content, str):
                raise InvalidModelOutput("Model did not return text JSON")
            return json.loads(content)
        except urllib.error.HTTPError as exc:
            raise ModelError("Model HTTP error " + str(exc.code)) from None
        except (urllib.error.URLError, socket.timeout, TimeoutError, OSError):
            raise ModelError("Model connection failed or timed out") from None
        except (json.JSONDecodeError, KeyError, IndexError, TypeError, AttributeError, UnicodeError):
            raise InvalidModelOutput("Model response is not a valid JSON action") from None


class ScriptedModel:
    """A fixture player, deliberately NOT an implementation of model reasoning."""
    mode = "mock"
    model_id = "scripted-offline-mock"

    def __init__(self, actions):
        require(isinstance(actions, list) and bool(actions), "Mock script must be a nonempty action array")
        self._actions = iter(copy.deepcopy(actions))

    @classmethod
    def load(cls, path):
        return cls(json.loads(Path(path).read_text(encoding="utf-8-sig")))

    def next_action(self, state, timeout):
        try:
            return next(self._actions)
        except StopIteration:
            raise ModelError("Offline script exhausted; no actual model decisions were made") from None
