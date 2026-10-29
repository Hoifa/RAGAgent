"""Conservative risk detection, never a choice of the correct policy value."""
import re

from .contracts import require


def numeric_conflict_candidates(observations):
    """Flag passages whose wording matches but numeric values differ.

    Search snippets are only risk signals, not accepted citation evidence.
    Different wording may hide a conflict; matching wording may be coincidental.
    """
    sources = {}
    for item in observations:
        action, returned = item.get("action", {}), item.get("result", {})
        if not returned.get("ok"):
            continue
        if action.get("tool_name") == "search_documents":
            passages = returned["data"]["hits"]
        elif action.get("tool_name") == "read_passage":
            passages = [returned["data"]]
        else:
            continue
        for passage in passages:
            text = passage.get("text", passage.get("excerpt", ""))
            values = re.findall(r"\d+(?:\.\d+)?", text)
            if not values:
                continue
            shape = re.sub(r"\s+", "", re.sub(r"\d+(?:\.\d+)?", "<number>", text))
            key = (passage["document_id"], passage["passage_id"])
            sources[key] = (shape, values)
    pairs = []
    keys = sorted(sources)
    for i, left in enumerate(keys):
        for right in keys[i + 1:]:
            if left[0] == right[0]:
                continue
            if sources[left][0] == sources[right][0] and sources[left][1] != sources[right][1]:
                pairs.append({"passages": [{"document_id": key[0], "passage_id": key[1]} for key in (left, right)]})
    return pairs


def validate_numeric_conflicts(result, observations, evidence):
    if result["status"] != "answered":
        return
    for risk in numeric_conflict_candidates(observations):
        keys = {(p["document_id"], p["passage_id"]) for p in risk["passages"]}
        missing = keys - set(evidence)
        require(not missing, "检索或读取发现措辞相同但数值不同的候选，不能忽略另一方。请先read_passage读取这些位置，再查证范围或替代关系：" + str(sorted(missing)))
        docs = {key[0] for key in keys}
        # Do not infer authority from a newer date or an unrelated third quote.
        # Current corpus uses explicit document IDs in its supersession text.
        proof = [c for c in result["citations"] if (c["document_id"], c["passage_id"]) not in keys
                 and all(doc in c["quote"] for doc in docs)
                 and re.search(r"替代|优先|适用|废止|supersed|precedence|appl", c["quote"], re.I)]
        require(bool(proof), "双方数值存在潜在冲突。answered需引用明确关联双方文档的适用或替代原文；没有依据时继续补查，列出双方原文并请求确认适用制度，不能自行选值。")
