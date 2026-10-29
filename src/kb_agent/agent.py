"""Bounded model/tool loop with auditable observations and source validation."""
import copy
import hashlib
import math
import queue
import threading
from datetime import datetime, timezone
from functools import partial
from uuid import uuid4
from pathlib import Path

from .contracts import ContractError, incomplete, require, validate_action, validate_request, validate_result, validate_conflict_verification, validate_execution_outcome
from .models import InvalidModelOutput, ModelError
from .knowledge import failure
from .progress import summarize_progress, action_progress_error
from .contracts import fields, nonempty, validate_answer_dates
from .conflicts import numeric_conflict_candidates, validate_numeric_conflicts

ENGINE_REVISION = hashlib.sha256(b"".join(path.name.encode("utf-8") + path.read_bytes()
                                          for path in sorted(Path(__file__).parent.glob("*.py")))).hexdigest()


def bounded_call(function, timeout):
    """Wall-clock wait bound. Only used for read-only tools and model requests.

    A timed-out daemon may finish its read later; its result is ignored and
    cannot append evidence or start another action. No background retries.
    """
    mailbox = queue.Queue(maxsize=1)

    def worker():
        try:
            mailbox.put((True, function()))
        except Exception as exc:
            mailbox.put((False, exc))

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    try:
        ok, value = mailbox.get(timeout=timeout)
    except queue.Empty:
        raise TimeoutError("Call deadline exceeded") from None
    if not ok:
        raise value
    return value


class Agent:
    def __init__(self, model, tools, max_model_calls=12, max_tool_calls=6, model_timeout=60, tool_timeout=10, max_validation_errors=3):
        require(type(max_model_calls) is int and max_model_calls > 0, "Invalid model budget")
        require(type(max_tool_calls) is int and max_tool_calls > 0, "Invalid tool budget")
        require(type(max_validation_errors) is int and max_validation_errors > 0, "Invalid validation repair budget")
        for value in (model_timeout, tool_timeout):
            require(type(value) in (int, float) and math.isfinite(value) and value > 0, "Timeout must be finite and positive")
        self.model, self.tools = model, tools
        self.budgets = {"max_model_calls": max_model_calls, "max_tool_calls": max_tool_calls,
                        "model_timeout": model_timeout, "tool_timeout": tool_timeout,
                        "max_validation_errors": max_validation_errors}
        self._used = False

    def run(self, request):
        validate_request(request)
        require(not self._used, "Create a new Agent and tools per run")
        self._used = True
        request = copy.deepcopy(request)
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:12]
        events, observations, evidence = [], [], {}
        model_calls = tool_calls = 0
        consecutive_errors = 0
        previous_error = None

        def record_repair(error):
            nonlocal consecutive_errors, previous_error
            fingerprint = (error["code"], error["message"])
            consecutive_errors = consecutive_errors + 1 if fingerprint == previous_error else 1
            previous_error = fingerprint
            return consecutive_errors >= self.budgets["max_validation_errors"]

        def event(kind, data):
            events.append({"event_id": len(events) + 1, "timestamp": datetime.now(timezone.utc).isoformat(),
                           "step": model_calls, "type": kind, "data": copy.deepcopy(data)})

        event("run_started", {"run_id": run_id, "mode": self.model.mode, "model": self.model.model_id,
                              "runtime_version": "1.1",
                              "engine_revision": ENGINE_REVISION,
                              "model_configuration": getattr(self.model, "configuration", {}),
                              "corpus_revision": self.tools.knowledge.revision, "budgets": self.budgets,
                              "fault_injection": self.tools.fault})
        result = None
        resolved_question = request["question"]
        resolver = getattr(self.model, "resolve_request", None)
        if callable(resolver) and getattr(self.model, "use_reference_classifier", True):
            model_calls += 1
            try:
                resolution = bounded_call(partial(resolver, copy.deepcopy(request), self.budgets["model_timeout"]), self.budgets["model_timeout"])
                if isinstance(resolution, dict) and resolution.get("action") == "continue":
                    fields(resolution, {"action", "question"}, {"reason"})
                    require(nonempty(resolution["question"]), "消歧后的问题必须非空。")
                    require(resolution["question"] == request["question"], "指代分类不得改写当前问题或增加新任务。")
                    resolved_question = resolution["question"]
                else:
                    validate_action(resolution)
                    require(resolution["action"] == "finish" and resolution["result"].get("status") == "needs_clarification"
                            and resolution["result"].get("reason_code") in ("ambiguous_reference", "missing_user_context"), "问题消歧只能请求澄清或继续，不能生成业务答案。")
                    validate_result(resolution["result"], {})
                    require(not resolution["result"]["citations"], "消歧阶段没有文档引用依据。")
                    if resolution["result"]["reason_code"] == "missing_user_context":
                        # A pre-retrieval classifier cannot know which policy
                        # conditions apply. Reject this draft and let the normal
                        # model/tool loop inspect the question and evidence.
                        error = {"code": "premature_clarification", "message": "尚未检索资料，指代分类不能凭空要求业务适用条件。请按原始问题进入工具循环：主题明确先检索；确实指代不明可追问。"}
                        observations.append({"rejected_action": resolution, "validation_error": error})
                        event("validation_error", error)
                    else:
                        result = resolution["result"]
                event("request_resolution", resolution)
            except (ContractError, InvalidModelOutput):
                result = incomplete("invalid_model_output", "问题消歧未返回合法结果，未继续业务工具调用。")
            except Exception:
                result = incomplete("model_failure", "问题消歧请求失败或超时。")
        while result is None and model_calls < self.budgets["max_model_calls"]:
            progress = summarize_progress(observations)
            state = {"request": request, "resolved_question": resolved_question, "observations": observations,
                     "potential_numeric_conflicts": numeric_conflict_candidates(observations),
                     "progress": progress,
                     "available_evidence": [{"document_id": key[0], "passage_id": key[1], "version_date": source["version_date"]}
                                            for key, source in evidence.items()],
                     "remaining": {"model_calls": self.budgets["max_model_calls"] - model_calls,
                                   "tool_calls": self.budgets["max_tool_calls"] - tool_calls}}
            model_calls += 1
            try:
                action = bounded_call(partial(self.model.next_action, copy.deepcopy(state), self.budgets["model_timeout"]), self.budgets["model_timeout"])
            except InvalidModelOutput as exc:
                error = {"code": "invalid_model_output", "message": str(exc)}
                event("validation_error", error)
                observations.append({"validation_error": error})
                if record_repair(error):
                    result = incomplete("invalid_model_output", "连续相同模型协议错误达到修复上限，未生成可靠结果。")
                    break
                continue
            except (ModelError, TimeoutError) as exc:
                event("model_error", {"code": "model_failure", "message": str(exc)})
                result = incomplete("model_failure", "模型请求失败或超时，尚未得到有效最终结果。")
                break
            except Exception:
                result = incomplete("model_failure", "模型适配器失败，尚未得到有效最终结果。")
                break
            try:
                validate_action(action)
                action_event = copy.deepcopy(action)
                if action["action"] == "finish" and "reason" not in action:
                    action_event["decision_basis"] = action["result"].get("answer")
                    action_event["decision_basis_source"] = "model_result.answer"
                event("model_action", action_event)
                if action["action"] == "finish":
                    validate_result(action["result"], evidence)
                    validate_answer_dates(action["result"], evidence, request)
                    validate_numeric_conflicts(action["result"], observations, evidence)
                    validate_conflict_verification(action["result"], observations)
                    validate_execution_outcome(action["result"], observations)
                    candidate_step = model_calls
                    applicability_checker = getattr(self.model, "check_applicability", None)
                    if callable(applicability_checker) and action["result"]["status"] == "answered":
                        if model_calls >= self.budgets["max_model_calls"]:
                            result = incomplete("budget_exhausted", "模型额度已用尽，尚未完成适用条件核验。")
                            break
                        model_calls += 1
                        event("review_started", {"candidate_step": candidate_step, "kind": "applicability"})
                        try:
                            scope = bounded_call(partial(applicability_checker, copy.deepcopy(request), copy.deepcopy(evidence), self.budgets["model_timeout"]), self.budgets["model_timeout"])
                            fields(scope, {"missing_conditions", "reason"})
                            require(isinstance(scope["missing_conditions"], list) and all(nonempty(x) for x in scope["missing_conditions"]), "适用条件核验必须返回missing_conditions字符串数组。")
                            require(nonempty(scope["reason"]) and scope["reason"].strip() not in ("一句依据", "依据", "简短依据", "reason", "..."), "适用条件核验必须说明原文条件和用户信息，不能返回模板占位依据。")
                            event("applicability_review", scope)
                            require(not scope["missing_conditions"], "仍缺少用户适用条件：" + "、".join(scope["missing_conditions"]) + "。请请求用户补充，不能将条件式答案标为任务已解决。")
                        except InvalidModelOutput:
                            raise ContractError("适用条件核验返回无效JSON，不能作为成功答案提交。") from None
                        except (ModelError, TimeoutError):
                            result = incomplete("model_failure", "适用条件核验请求失败或超时。")
                            break
                        except ContractError:
                            raise
                        except Exception:
                            result = incomplete("model_failure", "适用条件核验适配器异常。")
                            break
                    reviewer = getattr(self.model, "review_result", None)
                    if callable(reviewer) and action["result"]["status"] == "answered":
                        if model_calls >= self.budgets["max_model_calls"]:
                            result = incomplete("budget_exhausted", "模型额度已用尽，尚未完成最终证据复核。")
                            break
                        model_calls += 1
                        event("review_started", {"candidate_step": candidate_step, "kind": "evidence"})
                        try:
                            review = bounded_call(partial(reviewer, copy.deepcopy(request), copy.deepcopy(action["result"]),
                                                  copy.deepcopy(evidence), copy.deepcopy(observations), self.budgets["model_timeout"]), self.budgets["model_timeout"])
                            fields(review, {"valid", "issues"})
                            require(type(review["valid"]) is bool and isinstance(review["issues"], list)
                                    and all(nonempty(issue) for issue in review["issues"]), "复核结果必须为valid布尔值与issues字符串数组。")
                            require((review["valid"] and not review["issues"]) or (not review["valid"] and bool(review["issues"])), "复核结论与issues不一致。")
                            event("evidence_review", review)
                            require(review["valid"], "证据复核未通过：" + "；".join(review["issues"]))
                        except InvalidModelOutput:
                            raise ContractError("复核返回无效JSON，不能视为业务结果已通过。") from None
                        except (ModelError, TimeoutError):
                            result = incomplete("model_failure", "最终证据复核请求失败或超时。")
                            break
                        except ContractError:
                            raise
                        except Exception:
                            result = incomplete("model_failure", "最终证据复核适配器异常。")
                            break
                    result = action["result"]
                    break
            except ContractError as exc:
                error = {"code": "invalid_model_output", "message": str(exc)}
                event("validation_error", error)
                observations.append({"rejected_action": action, "validation_error": error})
                if record_repair(error):
                    result = incomplete("invalid_model_output", "连续相同模型校验错误达到修复上限，未生成可靠结果。")
                    break
                continue
            if tool_calls >= self.budgets["max_tool_calls"]:
                result = incomplete("budget_exhausted", "工具调用额度已用尽，无法完成模型请求的进一步查证。")
                break
            progress_error = action_progress_error(action, progress)
            if progress_error:
                error = {"code": "no_progress", "message": progress_error}
                event("validation_error", error)
                observations.append({"rejected_action": action, "validation_error": error})
                if record_repair(error):
                    result = incomplete("invalid_model_output", "模型连续请求无进展动作，修复上限已达到。")
                    break
                continue
            consecutive_errors = 0
            previous_error = None
            tool_calls += 1
            call_id = "tool-" + str(tool_calls)
            # Link the action event to the actual tool attempt.
            events[-1]["data"]["call_id"] = call_id
            try:
                returned, injected = bounded_call(partial(self.tools.execute, action["tool_name"], copy.deepcopy(action["arguments"]), self.budgets["tool_timeout"]), self.budgets["tool_timeout"])
            except TimeoutError:
                returned, injected = failure("timeout", "Tool deadline exceeded", True), False
            except Exception:
                returned, injected = failure("internal_error", "Tool executor failed"), False
            if returned["ok"] and action["tool_name"] == "read_passage":
                source = returned["data"]
                evidence[(source["document_id"], source["passage_id"])] = copy.deepcopy(source)
            if returned["ok"]:
                summary = ("hits=" + str(len(returned["data"]["hits"]))) if action["tool_name"] == "search_documents" else "Original passage read"
            else:
                summary = returned["error"]["code"]
            event("tool_result", {"call_id": call_id, "summary": summary, "injected": injected, "result": returned})
            observations.append({"action": action, "call_id": call_id, "result": returned})
        if result is None:
            result = incomplete("budget_exhausted", "模型调用额度已用尽，尚未得到通过校验的最终结果。")
        output = {"run_id": run_id, "mode": self.model.mode, "model": self.model.model_id,
                  "resolved_question": resolved_question,
                  "runtime_version": "1.1",
                  "engine_revision": ENGINE_REVISION,
                  "model_configuration": getattr(self.model, "configuration", {}),
                  "corpus_revision": self.tools.knowledge.revision, "budgets": self.budgets,
                  "model_calls": model_calls, "tool_calls": tool_calls, "result": result}
        event("run_finished", output)
        return output, events
