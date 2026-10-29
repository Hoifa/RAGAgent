"""A model may not hide observed numeric disagreement by declaring success."""
import json
import unittest
from pathlib import Path

from src.kb_agent.agent import Agent
from src.kb_agent.conflicts import numeric_conflict_candidates, validate_numeric_conflicts
from src.kb_agent.contracts import ContractError
from src.kb_agent.knowledge import KnowledgeBase, ToolExecutor
from src.kb_agent.models import ScriptedModel

ROOT = Path(__file__).resolve().parents[1]


def tool(name, **arguments):
    return {"action": "tool", "tool_name": name, "arguments": arguments, "reason": "Controlled evidence action"}


def citation(source, cid):
    return dict(citation_id=cid, document_id=source["document_id"], passage_id=source["passage_id"],
                version_date=source["version_date"], quote=source["text"])


class NumericRiskTests(unittest.TestCase):
    def setUp(self):
        self.kb = KnowledgeBase.load(ROOT / "data/corpora/conflict.json")
        self.observation = {"action": tool("search_documents", query="差旅报销期限"),
                            "result": self.kb.search("差旅报销期限")}

    def test_detects_value_disagreement_in_candidates_without_choosing_a_value(self):
        risks = numeric_conflict_candidates([self.observation])
        self.assertEqual(risks, [{"passages": [{"document_id": "D01", "passage_id": "P01"},
                                               {"document_id": "D02", "passage_id": "P01"}]}])
        self.assertNotIn("answer", risks[0])

    def test_generic_document_ids_and_unrelated_wording_are_not_a_case_lookup(self):
        def hit(doc, text):
            return {"document_id": doc, "passage_id": "rule", "excerpt": text}
        observation = {"action": {"tool_name": "search_documents"}, "result": {"ok": True, "data": {"hits": [
            hit("alpha", "套餐可创建7个项目。"), hit("beta", "套餐可创建9个项目。"), hit("other", "工单保留9天。")]}}}
        risks = numeric_conflict_candidates([observation])
        self.assertEqual({p["document_id"] for p in risks[0]["passages"]}, {"alpha", "beta"})
        self.assertEqual(len(risks), 1)

    def test_same_value_is_not_numeric_disagreement(self):
        observation = {"action": {"tool_name": "search_documents"}, "result": {"ok": True, "data": {"hits": [
            {"document_id": d, "passage_id": "p", "excerpt": "期限为7天。"} for d in ("one", "two")]}}}
        self.assertEqual(numeric_conflict_candidates([observation]), [])

    def test_answer_cannot_ignore_an_unread_opposing_candidate(self):
        actions = json.loads((ROOT / "tests/fixtures/mock/A01.json").read_text(encoding="utf-8"))
        output, trace = Agent(ScriptedModel(actions), ToolExecutor(self.kb), max_model_calls=3).run({"question": "报销期限多久？"})
        self.assertEqual(output["result"]["status"], "incomplete")
        self.assertEqual(output["result"]["citations"], [])
        self.assertTrue(any(e["type"] == "validation_error" and "D02" in e["data"]["message"] for e in trace))

    def test_reading_both_still_cannot_choose_one_without_precedence_proof(self):
        source = self.kb.read("D01", "P01")["data"]
        result = {"status": "answered", "citations": [citation(source, "C1")]}
        evidence = {(doc, "P01"): self.kb.read(doc, "P01")["data"] for doc in ("D01", "D02")}
        with self.assertRaises(ContractError):
            validate_numeric_conflicts(result, [self.observation], evidence)

    def test_unrelated_third_quote_cannot_resolve_numeric_disagreement(self):
        evidence = {(doc, "P01"): self.kb.read(doc, "P01")["data"] for doc in ("D01", "D02", "D03")}
        result = {"status": "answered", "citations": [citation(evidence[("D01", "P01")], "C1"), citation(evidence[("D03", "P01")], "C2")]}
        with self.assertRaises(ContractError):
            validate_numeric_conflicts(result, [self.observation], evidence)

    def test_explicit_supersession_can_support_model_chosen_answer(self):
        kb = KnowledgeBase.load(ROOT / "data/corpora/resolved.json")
        reads = [(doc, "P01") for doc in ("D01", "D02", "D06")] + [("D06", "P02")]
        actions = [tool("search_documents", query="差旅报销期限")]
        actions += [tool("read_passage", document_id=d, passage_id=p) for d, p in reads]
        result = {"status": "answered", "reason_code": None, "answer": "15天[C1]，替代依据[C2]。",
                  "citations": [citation(kb.read("D06", p)["data"], cid) for p, cid in (("P01", "C1"), ("P02", "C2"))],
                  "gaps": [], "follow_up_question": None}
        actions.append({"action": "finish", "result": result})
        output, _ = Agent(ScriptedModel(actions), ToolExecutor(kb)).run({"question": "2026年5月10日结束出差，报销期限多久？"})
        self.assertEqual(output["result"]["status"], "answered")


if __name__ == "__main__":
    unittest.main()
