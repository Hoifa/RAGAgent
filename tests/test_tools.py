import copy
import json
import tempfile
import unittest
from pathlib import Path

from src.kb_agent.contracts import ContractError
from src.kb_agent.knowledge import KnowledgeBase, ToolExecutor

ROOT = Path(__file__).resolve().parents[1]


class ToolTests(unittest.TestCase):
    def load(self, name="normal"):
        return KnowledgeBase.load(ROOT / ("data/corpora/" + name + ".json"))

    def test_normal_and_rephrased_query_retrieve_same_source(self):
        kb = self.load()
        for query in ("差旅报销期限多久？", "出差结束后最晚多久交报销？"):
            hits = kb.search(query)["data"]["hits"]
            self.assertEqual(hits[0]["document_id"], "D01")

    def test_conflict_documents_both_retrieved(self):
        for name in ("conflict", "scoped"):
            hits = self.load(name).search("报销期限多久")["data"]["hits"]
            self.assertTrue({"D01", "D02"}.issubset({h["document_id"] for h in hits}))

    def test_replacement_and_product_queries(self):
        hits = self.load("resolved").search("差旅报销期限 替代制度 适用范围")["data"]["hits"]
        self.assertIn("D06", [h["document_id"] for h in hits])
        hits = self.load().search("星帧剪辑2.0桌面版 字幕 导出 格式")["data"]["hits"]
        self.assertEqual(hits[0]["document_id"], "D05")

    def test_short_deadline_query_retains_operative_and_replacement_clauses(self):
        hits = self.load("resolved").search("差旅报销期限")["data"]["hits"]
        ids = {(h["document_id"], h["passage_id"]) for h in hits}
        self.assertTrue({("D06", "P01"), ("D06", "P02"), ("D01", "P01"), ("D02", "P01")}.issubset(ids))

    def test_missing_and_failure_are_different(self):
        tools = ToolExecutor(self.load())
        no_hits, _ = tools.execute("search_documents", {"query": "育儿假"}, 10)
        self.assertEqual(no_hits["data"]["hits"], [])
        self.assertTrue(no_hits["ok"])
        missing, _ = tools.execute("read_passage", {"document_id": "D99", "passage_id": "P01"}, 10)
        self.assertFalse(missing["ok"])
        self.assertEqual(missing["error"]["code"], "not_found")

    def test_generic_policy_words_do_not_retrieve_unrelated_deadline(self):
        for query in ("公司育儿假天数规定", "育儿假有多少天", "企业育儿假相关制度要求"):
            self.assertEqual(self.load().search(query)["data"]["hits"], [])

    def test_exact_read_and_caller_mutation_do_not_change_snapshot(self):
        kb = self.load()
        returned = kb.read("D01", "P01")
        self.assertEqual(returned["data"]["text"], "差旅报销应在行程结束后30天内提交。")
        returned["data"]["text"] = "changed by caller"
        self.assertIn("30天", kb.read("D01", "P01")["data"]["text"])

    def test_reload_changes_hash_without_mutating_active_snapshot(self):
        original = json.loads((ROOT / "data/corpora/normal.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "corpus.json"
            path.write_text(json.dumps(original), encoding="utf-8")
            before = KnowledgeBase.load(path)
            original[0]["passages"][0]["text"] = "差旅报销应在行程结束后45天内提交。"
            path.write_text(json.dumps(original), encoding="utf-8")
            after = KnowledgeBase.load(path)
        self.assertNotEqual(before.revision, after.revision)
        self.assertIn("30天", before.read("D01", "P01")["data"]["text"])
        self.assertIn("45天", after.read("D01", "P01")["data"]["text"])

    def test_bad_documents_fail_at_load(self):
        base = json.loads((ROOT / "data/corpora/normal.json").read_text(encoding="utf-8"))
        mutations = [base + [base[0]], []]
        for key, value in (("passages", []), ("version_date", "2026-02-30"), ("title", " ")):
            value_docs = copy.deepcopy(base)
            value_docs[0][key] = value
            mutations.append(value_docs)
        duplicate_passage = copy.deepcopy(base)
        duplicate_passage[0]["passages"].append(duplicate_passage[0]["passages"][0])
        mutations.append(duplicate_passage)
        for documents in mutations:
            with self.assertRaises(ContractError):
                KnowledgeBase(documents)

    def test_dependency_graph_rejects_missing_passages_and_cycles(self):
        base = json.loads((ROOT / "data/corpora/normal.json").read_text(encoding="utf-8"))
        for mapping in ({"P01": ["P99"]}, {"P01": ["P01"]}):
            docs = copy.deepcopy(base)
            docs[0]["citation_dependencies"] = mapping
            with self.assertRaises(ContractError):
                KnowledgeBase(docs)
        docs = copy.deepcopy(base)
        docs[1]["citation_dependencies"] = {"P01": ["P02"], "P02": ["P01"]}
        with self.assertRaises(ContractError):
            KnowledgeBase(docs)

    def test_injected_empty_result_then_real_result(self):
        tools = ToolExecutor(self.load(), {"tool": "search_documents", "behavior": "first_call_empty"})
        first, injected = tools.execute("search_documents", {"query": "报销期限"}, 10)
        second, injected2 = tools.execute("search_documents", {"query": "差旅报销期限"}, 10)
        self.assertTrue(injected)
        self.assertEqual(first["data"]["hits"], [])
        self.assertFalse(injected2)
        self.assertTrue(second["data"]["hits"])


if __name__ == "__main__":
    unittest.main()
