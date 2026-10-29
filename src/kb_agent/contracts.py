"""Strict boundary validation; no business answers are chosen here."""
import re


class ContractError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ContractError(message)


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def fields(value, required, optional=()):
    require(isinstance(value, dict), "Expected an object")
    missing = set(required) - set(value)
    unexpected = set(value) - set(required) - set(optional)
    require(not missing and not unexpected,
            "JSON字段不匹配：缺少=" + str(sorted(missing)) + "；多余=" + str(sorted(unexpected))
            + "；必填字段=" + str(sorted(required)) + "；可选字段=" + str(sorted(optional)))


def validate_request(request):
    fields(request, {"question"}, {"history"})
    require(nonempty(request["question"]), "question must be nonempty")
    history = request.get("history", [])
    require(isinstance(history, list), "history must be a list")
    for message in history:
        fields(message, {"role", "content"})
        require(message["role"] in ("user", "assistant"), "history role is not allowed")
        require(nonempty(message["content"]), "history content must be nonempty")


def validate_tool(name, arguments):
    if name == "search_documents":
        fields(arguments, {"query"}, {"top_k"})
        require(nonempty(arguments["query"]), "query must be nonempty")
        k = arguments.get("top_k", 5)
        require(type(k) is int and 1 <= k <= 10, "top_k must be an integer from 1 to 10")
    elif name == "read_passage":
        fields(arguments, {"document_id", "passage_id"})
        require(all(nonempty(v) for v in arguments.values()), "document and passage IDs must be nonempty")
    else:
        raise ContractError("Unknown tool")


def validate_action(action):
    require(isinstance(action, dict), "Action must be an object")
    kind = action.get("action")
    if kind == "tool":
        fields(action, {"action", "tool_name", "arguments", "reason"}, {"provider_call_id"})
        validate_tool(action["tool_name"], action["arguments"])
    elif kind == "finish":
        fields(action, {"action", "result"}, {"reason", "provider_call_id"})
        require(isinstance(action["result"], dict), "finish.result must be an object")
    else:
        raise ContractError("Unknown action")
    if kind == "tool" or "reason" in action:
        require(nonempty(action["reason"]), "A short action reason is required")
    if "provider_call_id" in action:
        require(nonempty(action["provider_call_id"]), "Invalid provider call ID")


def validate_result(result, evidence):
    fields(result, {"status", "reason_code", "answer", "citations", "gaps", "follow_up_question"})
    require(nonempty(result["answer"]), "answer must be nonempty")
    require(isinstance(result["gaps"], list) and all(nonempty(g) for g in result["gaps"]), "gaps must contain strings")
    require(isinstance(result["citations"], list), "citations must be a list")
    follow_up = result["follow_up_question"]
    require(follow_up is None or nonempty(follow_up), "Invalid follow-up question")
    reasons = {
        "answered": (None,),
        "needs_clarification": ("document_conflict", "missing_user_context", "ambiguous_reference"),
        "unanswerable": ("out_of_scope", "insufficient_evidence"),
        "incomplete": ("tool_failure", "model_failure", "budget_exhausted", "invalid_model_output"),
    }
    status = result["status"]
    require(isinstance(status, str) and status in reasons, "Unknown status")
    require(result["reason_code"] in reasons[status], "Status and reason do not match")
    if status == "answered":
        require(bool(result["citations"]) and not result["gaps"] and follow_up is None, "answered requires evidence and no unresolved gaps")
    else:
        require(bool(result["gaps"]), "非成功状态的 gaps 必须是非空字符串数组，例如缺少制度适用范围或优先级依据；不能填空数组。")
    if status == "needs_clarification":
        require(nonempty(follow_up), "Clarification requires a question")
        if result["reason_code"] == "document_conflict":
            require(any(re.search(r"适用(?:范围|制度|依据)|优先级|替代(?:关系|依据)|applicab|precedence|supersed", gap, re.I) for gap in result["gaps"]),
                    "冲突的 gaps 必须明确缺少适用制度、适用范围、优先级或替代依据。version_date 是版本日期，不是生效日期；不能仅要求用户给行程日期或部门就声称能够消解冲突。请请求确认适用制度或补充制度说明。")
    ids = set()
    for citation in result["citations"]:
        fields(citation, {"citation_id", "document_id", "version_date", "passage_id", "quote"})
        require(all(nonempty(v) for v in citation.values()), "Citation values must be nonempty strings")
        cid = citation["citation_id"]
        require(re.fullmatch(r"C[1-9][0-9]*", cid) is not None and cid not in ids, "Invalid or duplicate citation ID")
        ids.add(cid)
        source = evidence.get((citation["document_id"], citation["passage_id"]))
        require(source is not None, "缺少成功读取的原文：document_id=" + citation["document_id"] + "，passage_id=" + citation["passage_id"] + "。请先调用 read_passage 补充该原文再提交结果；检索摘录不能作为引用证据。")
        require(citation["version_date"] == source["version_date"], "Citation date mismatch")
        require(citation["quote"] in source["text"], "Quote is not an exact source substring")
    references = set(re.findall(r"\[(C[0-9]+)\]", result["answer"]))
    cited_passages = {(c["document_id"], c["passage_id"]) for c in result["citations"]}
    for key in cited_passages:
        required = {(p["document_id"], p["passage_id"]) for p in evidence[key].get("citation_dependencies", [])}
        missing = required - cited_passages
        require(not missing, "该条款声明了必需的配套依据，请先read_passage并同时引用：" + str(sorted(missing)))
    if ids:
        require(references == ids, "answer 正文必须包含与 citations 对应的引用标记：" + ", ".join("[" + cid + "]" for cid in sorted(ids)) + "；不要只在 citations 数组中填写引用。")
    else:
        require(not references, "citations为空，answer必须删除所有[C...]占位引用；没有证据时直接说明缺口或追问。")


def validate_conflict_verification(result, observations):
    """Check claimed conflict investigation, without deciding business truth."""
    if result["reason_code"] != "document_conflict":
        return
    sources = {(c["document_id"], c["passage_id"]) for c in result["citations"]}
    require(len(sources) >= 2, "冲突结果必须引用至少两个不同的原文片段。")
    positions = []
    for source in sources:
        indices = [i for i, item in enumerate(observations)
                   if item.get("action", {}).get("tool_name") == "read_passage"
                   and item.get("result", {}).get("ok")
                   and (item["result"]["data"]["document_id"], item["result"]["data"]["passage_id"]) == source]
        require(bool(indices), "冲突引用必须先读取双方原文。")
        positions.append(min(indices))
    require(any(i > max(positions) and item.get("action", {}).get("tool_name") == "search_documents"
                and item.get("result", {}).get("ok") for i, item in enumerate(observations)),
            "冲突双方已读取，但还未补充查证。请调用 search_documents 查找适用范围、优先级或替代关系；仍无依据时说明制度资料缺口，请用户确认适用制度。")


def validate_execution_outcome(result, observations):
    """Do not misreport unresolved evidence-reading failures as absent data."""
    if result["status"] not in ("unanswerable", "needs_clarification"):
        return
    unread_errors = set()
    search_failed = False
    for item in observations:
        action, returned = item.get("action", {}), item.get("result", {})
        if action.get("tool_name") == "search_documents":
            search_failed = not returned.get("ok", False)
        if action.get("tool_name") == "read_passage":
            arguments = action["arguments"]
            key = (arguments["document_id"], arguments["passage_id"])
            if returned.get("ok"):
                unread_errors.discard(key)
            else:
                unread_errors.add(key)
    require(not unread_errors and not search_failed,
            "工具错误不等于资料不足或缺少用户条件。尚有原文读取失败或检索未恢复，请选择有限恢复行动；若无法核验必要资料，使用 incomplete/tool_failure，不能用 unanswerable 或追问让用户修复工具问题。")


def validate_answer_dates(result, evidence, request):
    """No implicit calendar calculator: new absolute dates need provenance."""
    if result["status"] != "answered":
        return

    def dates(text):
        full = {(int(y), int(m), int(d)) for y, m, d in re.findall(r"(\d{4})年(\d{1,2})月(\d{1,2})日", text)}
        full.update((int(y), int(m), int(d)) for y, m, d in re.findall(r"(\d{4})-(\d{1,2})-(\d{1,2})", text))
        short = {(int(m), int(d)) for m, d in re.findall(r"(\d{1,2})月(\d{1,2})日", text)}
        short.update((m, d) for _, m, d in full)
        return full, short

    source = [request.get("question", "")]
    source.extend(m["content"] for m in request.get("history", []) if m["role"] == "user")
    for citation in result["citations"]:
        source.extend((citation["quote"], evidence[(citation["document_id"], citation["passage_id"])]["version_date"]))
    known_full, known_short = dates("\n".join(source))
    claimed_full, claimed_short = dates(result["answer"])
    require(claimed_full <= known_full and claimed_short <= known_short,
            "答案出现原文或用户输入未提供的绝对日期。当前工具没有日历计算及计日规则核验能力；请删除擅自推算的截止日期，仅回答有原文支持的期限与适用条件。")


def incomplete(reason, gap):
    return {"status": "incomplete", "reason_code": reason,
            "answer": "任务未完成：" + gap, "citations": [], "gaps": [gap], "follow_up_question": None}
