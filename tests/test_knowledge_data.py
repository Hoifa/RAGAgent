"""Knowledge fixture integrity checks, not Agent or model evaluations."""

import json
import unittest
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORPORA_DIR = ROOT / "data" / "corpora"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


class KnowledgeDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpora = {p.stem: read_json(p) for p in CORPORA_DIR.glob("*.json")}
        cls.manifest = read_json(ROOT / "tests/fixtures/case-manifest.json")

    def by_id(self, name):
        return {d["document_id"]: d for d in self.corpora[name]}

    def test_document_contract_and_unique_ids(self):
        for name, documents in self.corpora.items():
            with self.subTest(corpus=name):
                self.assertIsInstance(documents, list)
                self.assertTrue(documents)
                ids = []
                for document in documents:
                    self.assertTrue({"document_id", "title", "version_date", "passages"} <= set(document)
                                    <= {"document_id", "title", "version_date", "passages", "citation_dependencies"})
                    for key in ("document_id", "title", "version_date"):
                        self.assertIsInstance(document[key], str)
                        self.assertTrue(document[key].strip())
                    self.assertEqual(date.fromisoformat(document["version_date"]).isoformat(), document["version_date"])
                    ids.append(document["document_id"])
                    self.assertTrue(document["passages"])
                    passage_ids = []
                    for passage in document["passages"]:
                        self.assertEqual(set(passage), {"passage_id", "text"})
                        for value in passage.values():
                            self.assertIsInstance(value, str)
                            self.assertTrue(value.strip())
                        passage_ids.append(passage["passage_id"])
                    self.assertEqual(len(passage_ids), len(set(passage_ids)))
                self.assertEqual(len(ids), len(set(ids)))

    def test_snapshot_membership_and_isolation(self):
        normal = {"D01", "D03", "D04", "D05"}
        expected = {"normal": normal, "changed": normal,
                    "conflict": normal | {"D02"}, "resolved": normal | {"D02", "D06"},
                    "scoped": normal | {"D02"}}
        self.assertEqual(set(self.corpora), set(expected))
        for name, ids in expected.items():
            self.assertEqual(set(self.by_id(name)), ids)

    def test_shared_documents_do_not_drift(self):
        normal = self.by_id("normal")
        for name in self.corpora:
            for doc_id in ("D03", "D04", "D05"):
                self.assertEqual(normal[doc_id], self.by_id(name)[doc_id])
        for doc_id, document in self.by_id("conflict").items():
            self.assertEqual(document, self.by_id("resolved")[doc_id])

    def test_change_is_only_deadline_text(self):
        normal = json.loads(json.dumps(self.corpora["normal"]))
        document = next(d for d in normal if d["document_id"] == "D01")
        self.assertIn("行程结束后30天", document["passages"][0]["text"])
        document["passages"][0]["text"] = document["passages"][0]["text"].replace("30天", "45天")
        self.assertEqual(normal, self.corpora["changed"])

    def test_conflict_has_no_implicit_resolution(self):
        documents = self.by_id("conflict")
        self.assertGreater(documents["D02"]["version_date"], documents["D01"]["version_date"])
        self.assertEqual(documents["D01"]["passages"], [
            {"passage_id": "P01", "text": "差旅报销应在行程结束后30天内提交。"}])
        self.assertEqual(documents["D02"]["passages"], [
            {"passage_id": "P01", "text": "差旅报销应在行程结束后15天内提交。"}])
        for doc_id in ("D03", "D04", "D05"):
            self.assertNotIn("替代D01", json.dumps(documents[doc_id], ensure_ascii=False))

    def test_scope_and_replacement_are_in_citable_text(self):
        scoped = self.by_id("scoped")
        self.assertIn("总部员工", scoped["D01"]["passages"][0]["text"])
        self.assertIn("海外分支机构员工", scoped["D02"]["passages"][0]["text"])
        passages = self.by_id("resolved")["D06"]["passages"]
        self.assertIn("2026年4月1日及以后", passages[0]["text"])
        self.assertIn("15天", passages[0]["text"])
        self.assertIn("替代D01", passages[1]["text"])
        self.assertIn("D02", passages[1]["text"])
        self.assertIn("不在本通知适用范围", passages[2]["text"])

    def test_case_inputs_and_manifest_references(self):
        ids = []
        for case in self.manifest["cases"]:
            ids.append(case["case_id"])
            corpus = read_json(ROOT / case["corpus"])
            request = read_json(ROOT / case["input"])
            self.assertTrue(request["question"].strip())
            self.assertLessEqual(set(request), {"question", "history"})
            for message in request.get("history", []):
                self.assertIn(message["role"], ("user", "assistant"))
                self.assertTrue(message["content"].strip())
            self.assertLessEqual(set(case["required_document_ids"]), {d["document_id"] for d in corpus})
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue({"A01", "A02", "A03", "A04", "A05", "A06"}.issubset(ids))
        b03 = next(c for c in self.manifest["cases"] if c["case_id"] == "B03")
        self.assertIn("2026年5月10日", read_json(ROOT / b03["input"])["question"])

    def test_product_scope_and_out_of_scope_topics(self):
        product = self.by_id("normal")["D05"]["passages"][0]["text"]
        for required in ("2.0桌面版", "SRT", "TXT", "不说明移动端"):
            self.assertIn(required, product)
        for corpus in self.corpora.values():
            text = json.dumps(corpus, ensure_ascii=False)
            self.assertNotIn("育儿假", text)
            self.assertNotIn("购房补贴", text)


if __name__ == "__main__":
    unittest.main()
