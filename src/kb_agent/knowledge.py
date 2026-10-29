"""Immutable per-run knowledge snapshot and lightweight lexical retrieval."""
import copy
import hashlib
import json
import math
import re
import time
from collections import Counter
from datetime import date
from pathlib import Path

from .contracts import ContractError, fields, nonempty, require, validate_tool


def success(data):
    return {"ok": True, "data": data, "error": None}


def failure(code, message, retryable=False):
    return {"ok": False, "data": None, "error": {"code": code, "message": message, "retryable": retryable}}


# Generic vocabulary normalization, not question/answer or document-ID routing.
ALIASES = (("出差", "差旅"), ("最晚", "期限"), ("最迟", "期限"),
           ("多久", "期限"), ("所需资料", "材料"))
# These generic terms alone must not make an unrelated policy look relevant.
STOP_WORDS = {"公司", "企业", "制度", "规定", "相关", "具体", "关于", "信息", "要求", "多少", "天数"}


def terms(text):
    text = text.lower()
    for source, target in ALIASES:
        text = text.replace(source, target)
    output = re.findall(r"[a-z0-9]+(?:\.[0-9]+)?", text)
    for part in re.findall(r"[\u4e00-\u9fff]+", text):
        output.extend(part[i:i + 2] for i in range(len(part) - 1))
    return Counter(token for token in output if token not in STOP_WORDS)


class KnowledgeBase:
    def __init__(self, documents):
        require(isinstance(documents, list) and bool(documents), "Knowledge must be a nonempty document array")
        self._documents = copy.deepcopy(documents)
        self._passages = {}
        self._dependencies = {}
        document_ids = set()
        for document in self._documents:
            fields(document, {"document_id", "title", "version_date", "passages"}, {"scope", "effective_date", "supersedes", "citation_dependencies"})
            for key in ("document_id", "title", "version_date"):
                require(nonempty(document[key]), "Document metadata must be nonempty")
            require(document["document_id"] not in document_ids, "Duplicate document ID")
            document_ids.add(document["document_id"])
            for key in ("version_date", "effective_date"):
                if key in document:
                    try:
                        require(date.fromisoformat(document[key]).isoformat() == document[key], "Invalid date format")
                    except (ValueError, TypeError):
                        raise ContractError("Invalid document date") from None
            if "scope" in document:
                require(nonempty(document["scope"]), "scope must be nonempty text")
            if "supersedes" in document:
                require(isinstance(document["supersedes"], list) and all(nonempty(x) for x in document["supersedes"]), "supersedes must be a list of IDs")
            require(isinstance(document["passages"], list) and bool(document["passages"]), "Document needs passages")
            for passage in document["passages"]:
                fields(passage, {"passage_id", "text"})
                require(all(nonempty(v) for v in passage.values()), "Passage fields must be nonempty")
                key = (document["document_id"], passage["passage_id"])
                require(key not in self._passages, "Duplicate passage ID")
                self._passages[key] = {k: document[k] for k in ("document_id", "title", "version_date")}
                self._passages[key].update(passage)
            dependencies = document.get("citation_dependencies", {})
            require(isinstance(dependencies, dict), "citation_dependencies must be an object")
            passage_ids = {p["passage_id"] for p in document["passages"]}
            for source, targets in dependencies.items():
                require(source in passage_ids and isinstance(targets, list) and bool(targets)
                        and all(nonempty(target) and target in passage_ids and target != source for target in targets),
                        "Citation dependencies must reference other passages in the same document")
                require(len(targets) == len(set(targets)), "Duplicate citation dependency")
                self._dependencies[(document["document_id"], source)] = targets
            def visit(source, path):
                require(source not in path, "Cyclic citation dependencies")
                for target in dependencies.get(source, []):
                    visit(target, path | {source})
            for source in dependencies:
                visit(source, set())
        payload = json.dumps(self._documents, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.revision = hashlib.sha256(payload).hexdigest()
        self._tokens = {key: terms(p["title"] + " " + p["text"]) for key, p in self._passages.items()}
        self._df = Counter(t for tokens in self._tokens.values() for t in tokens)
        self._average_length = sum(sum(t.values()) for t in self._tokens.values()) / len(self._tokens)

    @classmethod
    def load(cls, path):
        return cls(json.loads(Path(path).read_text(encoding="utf-8-sig")))

    def search(self, query, top_k=5, deadline=None):
        query_terms = terms(query)
        scored = []
        n = len(self._tokens)
        for key, tokens in self._tokens.items():
            if deadline is not None and time.monotonic() >= deadline:
                raise TimeoutError()
            length = sum(tokens.values())
            score = 0.0
            for term in query_terms:
                tf = tokens.get(term, 0)
                if tf:
                    idf = math.log(1 + (n - self._df[term] + 0.5) / (self._df[term] + 0.5))
                    score += idf * tf * 2.2 / (tf + 1.2 * (0.25 + 0.75 * length / self._average_length))
            if score > 0:
                scored.append((score, key))
        scored.sort(key=lambda item: (-item[0], item[1]))
        # Balance source diversity against passage relevance. Hard document-first
        # ordering hid the operative clauses of multi-passage notices behind
        # unrelated documents. A soft penalty retains useful sibling passages.
        ranked, counts = [], Counter()
        remaining = list(scored)
        while remaining and len(ranked) < top_k:
            best = min(remaining, key=lambda item: (-item[0] / (1 + 0.5 * counts[item[1][0]]), item[1]))
            remaining.remove(best)
            ranked.append(best)
            counts[best[1][0]] += 1
        hits = []
        for _, key in ranked:
            p = self._passages[key]
            hits.append({k: p[k] for k in ("document_id", "title", "version_date", "passage_id")})
            hits[-1].update(excerpt=p["text"][:200], rank=len(hits))
        return success({"corpus_revision": self.revision, "hits": hits})

    def read(self, document_id, passage_id):
        passage = self._passages.get((document_id, passage_id))
        if passage is None:
            return failure("not_found", "Document or passage not found")
        data = dict(copy.deepcopy(passage), corpus_revision=self.revision)
        dependencies = self._dependencies.get((document_id, passage_id), [])
        if dependencies:
            data["citation_dependencies"] = [{"document_id": document_id, "passage_id": pid} for pid in dependencies]
        return success(data)


class ToolExecutor:
    def __init__(self, knowledge, fault=None):
        self.knowledge = knowledge
        self.fault = copy.deepcopy(fault)
        self._matched_calls = 0
        if fault is not None:
            fields(fault, {"tool", "behavior"}, {"match", "code"})
            require(fault["tool"] in ("search_documents", "read_passage"), "Invalid fault tool")
            require(fault["behavior"] in ("always_error", "first_matching_call_error", "first_call_empty"), "Invalid fault behavior")
            require(fault.get("code", "unavailable") in ("unavailable", "timeout", "internal_error"), "Invalid fault code")
            require(isinstance(fault.get("match", {}), dict), "Invalid fault match")
            allowed = {"query", "top_k"} if fault["tool"] == "search_documents" else {"document_id", "passage_id"}
            require(set(fault.get("match", {})) <= allowed, "Invalid fault match fields")
            require(fault["behavior"] != "first_call_empty" or fault["tool"] == "search_documents", "Empty injection only applies to search")

    def execute(self, name, arguments, timeout):
        validate_tool(name, arguments)
        start = time.monotonic()
        injected = False
        if self.fault and name == self.fault["tool"] and all(arguments.get(k) == v for k, v in self.fault.get("match", {}).items()):
            self._matched_calls += 1
            behavior = self.fault["behavior"]
            injected = behavior == "always_error" or self._matched_calls == 1
            if injected:
                if behavior == "first_call_empty":
                    return success({"corpus_revision": self.knowledge.revision, "hits": []}), True
                return failure(self.fault.get("code", "unavailable"), "Test-injected tool failure", True), True
        try:
            if name == "search_documents":
                result = self.knowledge.search(arguments["query"], arguments.get("top_k", 5), start + timeout)
            else:
                result = self.knowledge.read(arguments["document_id"], arguments["passage_id"])
            if time.monotonic() - start >= timeout:
                raise TimeoutError()
            return result, injected
        except TimeoutError:
            return failure("timeout", "Tool deadline exceeded", True), injected
        except Exception:
            return failure("internal_error", "Tool execution failed"), injected
