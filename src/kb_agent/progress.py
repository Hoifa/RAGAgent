"""Mechanical progress signals, never a business-answer decision."""


def summarize_progress(observations):
    seen, reads, failures = set(), set(), {}
    search_calls = stale = empty = 0
    for item in observations:
        action, result = item.get("action", {}), item.get("result")
        if result is None:
            continue
        if action.get("tool_name") == "search_documents":
            search_calls += 1
            if result["ok"]:
                keys = {(h["document_id"], h["passage_id"]) for h in result["data"]["hits"]}
                stale = 0 if keys - seen else stale + 1
                empty = empty + 1 if not keys else 0
                seen.update(keys)
        elif action.get("tool_name") == "read_passage":
            args = action["arguments"]
            key = (args["document_id"], args["passage_id"])
            if result["ok"]:
                reads.add(key)
                failures.pop(key, None)
                seen.update((p["document_id"], p["passage_id"]) for p in result["data"].get("citation_dependencies", []))
            else:
                failures[key] = failures.get(key, 0) + 1
    as_ids = lambda keys: [{"document_id": d, "passage_id": p} for d, p in sorted(keys)]
    return {"search_calls": search_calls, "no_new_candidate_searches": stale,
            "consecutive_empty_searches": empty, "unread_candidates": as_ids(seen - reads),
            "successful_reads": as_ids(reads),
            "read_failures": [dict(document_id=k[0], passage_id=k[1], attempts=v) for k, v in sorted(failures.items())]}


def action_progress_error(action, progress):
    if action["tool_name"] == "search_documents" and progress["no_new_candidate_searches"] >= 2:
        return "连续两次检索没有新增候选，停止无进展检索。请选择读取已有未读候选，或根据相关性结束并说明缺口。"
    if action["tool_name"] == "read_passage":
        args = action["arguments"]
        if args in progress["successful_reads"]:
            return "该原文已成功读取，仍在本轮证据中。请使用已有证据、读取其他片段或结束，不重复读取。"
        if any(f["document_id"] == args["document_id"] and f["passage_id"] == args["passage_id"] and f["attempts"] >= 2 for f in progress["read_failures"]):
            return "该片段已连续读取失败两次。请选择其他有效证据；必要资料仍不可读时以incomplete/tool_failure结束。"
    return None
