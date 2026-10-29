# Selected actual model paths

Selection is for readability, not an aggregate quality score. Every final run, including failures, is linked in final-audit. Tool parameters and next-action reasons below come from actual traces; none are a preset real-model decision script. The full validation/repair loop remains in each raw Trace.

## A01 / round 1

Question: 差旅报销应在行程结束后多久内提交？

Status: answered / None. [Input](verified-candidate/A01/20261028T133634Z-52e3eb66263c/input.json), [Output](verified-candidate/A01/20261028T133634Z-52e3eb66263c/output.json), [Trace](verified-candidate/A01/20261028T133634Z-52e3eb66263c/trace.jsonl).

| Step | Tool | Arguments | Observation | Next action | Next model basis |
|---|---|---|---|---|---|
| 1 | search_documents | {"query": "差旅报销 提交期限 行程结束后", "top_k": 5} | hits=5 | read_passage | 读取差旅报销提交期限的具体规定，以确认30天内提交的依据 |
| 2 | read_passage | {"document_id": "D01", "passage_id": "P01"} | Original passage read | finish:answered | 差旅报销应在行程结束后30天内提交。 |

Final answer: 差旅报销应在行程结束后30天内提交 [C1]。

## A02 / round 1

Question: 差旅报销期限多久？

Status: needs_clarification / document_conflict. [Input](verified-candidate/A02/20261028T133640Z-4b2da5066d92/input.json), [Output](verified-candidate/A02/20261028T133640Z-4b2da5066d92/output.json), [Trace](verified-candidate/A02/20261028T133640Z-4b2da5066d92/trace.jsonl).

| Step | Tool | Arguments | Observation | Next action | Next model basis |
|---|---|---|---|---|---|
| 1 | search_documents | {"query": "差旅报销期限规定", "top_k": 5} | hits=5 | read_passage | 确认差旅报销期限为30天内的具体规定 |
| 2 | read_passage | {"document_id": "D01", "passage_id": "P01"} | Original passage read | read_passage | 确认另一份文件中关于差旅报销期限为15天内的规定，以核查是否存在制度冲突 |
| 3 | read_passage | {"document_id": "D02", "passage_id": "P01"} | Original passage read | finish:needs_clarification | 差旅报销期限存在两种不同规定：根据《差旅报销提交规定》（2026-01-10），应在行程结束后30天内提交；而根据《差旅费用报销办理说明》（2026-03-15），应在行程结束后15天内提交。两者在适用范围或优先级上未明确说明，需确认以哪一版本为准或是否存在适用条件差异。 |
| 6 | search_documents | {"query": "差旅报销提交规定 与 差旅费用报销办理说明 优先级或替代关系", "top_k": 5} | hits=5 | finish:needs_clarification | 差旅报销期限存在两种不同规定：根据《差旅报销提交规定》（2026-01-10），应在行程结束后30天内提交；而根据《差旅费用报销办理说明》（2026-03-15），应在行程结束后15天内提交。目前未找到明确说明两份文件之间优先级、适用范围或替代关系的依据，无法确定应以哪一版本为准。[C1][C2] |

Final answer: 差旅报销期限存在两种不同规定：根据《差旅报销提交规定》（2026-01-10），应在行程结束后30天内提交；而根据《差旅费用报销办理说明》（2026-03-15），应在行程结束后15天内提交。目前未找到明确说明两份文件之间优先级、适用范围或替代关系的依据，无法确定应以哪一版本为准。[C1][C2]

## A03 / round 1

Question: 公司的育儿假有多少天？

Status: unanswerable / insufficient_evidence. [Input](verified-candidate/A03/20261028T133653Z-9b96fa9fb31a/input.json), [Output](verified-candidate/A03/20261028T133653Z-9b96fa9fb31a/output.json), [Trace](verified-candidate/A03/20261028T133653Z-9b96fa9fb31a/trace.jsonl).

| Step | Tool | Arguments | Observation | Next action | Next model basis |
|---|---|---|---|---|---|
| 1 | search_documents | {"query": "公司育儿假天数规定", "top_k": 5} | hits=0 | search_documents | 使用更精确的关键词检索育儿假相关制度文件 |
| 2 | search_documents | {"query": "育儿假 休假天数 公司规定", "top_k": 5} | hits=0 | finish:unanswerable | 未找到关于公司育儿假具体天数的相关制度文件。请确认是否需要查询特定地区或企业类型的育儿假规定，或提供更具体的制度名称、版本日期等信息以便进一步检索。 |

Final answer: 未找到关于公司育儿假具体天数的相关制度文件。请确认是否需要查询特定地区或企业类型的育儿假规定，或提供更具体的制度名称、版本日期等信息以便进一步检索。

## A05 / round 1

Question: 那需要哪些材料？

Status: answered / None. [Input](verified-candidate/A05/20261028T133702Z-563e68aea4b2/input.json), [Output](verified-candidate/A05/20261028T133702Z-563e68aea4b2/output.json), [Trace](verified-candidate/A05/20261028T133702Z-563e68aea4b2/trace.jsonl).

| Step | Tool | Arguments | Observation | Next action | Next model basis |
|---|---|---|---|---|---|
| 1 | search_documents | {"query": "差旅报销所需材料", "top_k": 5} | hits=5 | read_passage | 读取差旅报销所需材料的具体要求，以确认完整清单 |
| 2 | read_passage | {"document_id": "D03", "passage_id": "P01"} | Original passage read | finish:answered | 申请差旅报销时，应提交已审批的出差申请单、费用明细表及与费用对应的发票。涉及交通或住宿费用的，还应提交对应的行程凭证或住宿账单。 |

Final answer: 申请差旅报销时，应提交已审批的出差申请单、费用明细表及与费用对应的发票。涉及交通或住宿费用的，还应提交对应的行程凭证或住宿账单。[C1]

## A06 / round 1

Question: 差旅报销应在行程结束后多久内提交？

Status: incomplete / tool_failure. [Input](verified-candidate/A06/20261028T133710Z-a60b8e25c113/input.json), [Output](verified-candidate/A06/20261028T133710Z-a60b8e25c113/output.json), [Trace](verified-candidate/A06/20261028T133710Z-a60b8e25c113/trace.jsonl).

| Step | Tool | Arguments | Observation | Next action | Next model basis |
|---|---|---|---|---|---|
| 1 | search_documents | {"query": "差旅报销 提交期限 行程结束后", "top_k": 5} | hits=5 | read_passage | 读取差旅报销提交期限的具体规定，以确认30天内提交的条款是否完整有效 |
| 2 | read_passage | {"document_id": "D01", "passage_id": "P01"} | unavailable | read_passage | 尝试重新读取差旅报销提交期限的原文，确认30天内提交的规定是否有效 |
| 3 | read_passage | {"document_id": "D01", "passage_id": "P01"} | unavailable | finish:incomplete | 无法获取差旅报销提交期限的具体规定，读取相关文档失败。 |

Final answer: 无法获取差旅报销提交期限的具体规定，读取相关文档失败。

## B01 / round 1

Question: 差旅报销应在行程结束后多久内提交？

Status: answered / None. [Input](verified-candidate/B01/20261028T133714Z-184a6c191a77/input.json), [Output](verified-candidate/B01/20261028T133714Z-184a6c191a77/output.json), [Trace](verified-candidate/B01/20261028T133714Z-184a6c191a77/trace.jsonl).

| Step | Tool | Arguments | Observation | Next action | Next model basis |
|---|---|---|---|---|---|
| 1 | search_documents | {"query": "差旅报销提交期限 行程结束后", "top_k": 5} | hits=5 | read_passage | 读取差旅报销提交期限的具体规定，以确认45天内提交的依据 |
| 2 | read_passage | {"document_id": "D01", "passage_id": "P01"} | Original passage read | finish:answered | 差旅报销应在行程结束后45天内提交。 |

Final answer: 差旅报销应在行程结束后45天内提交 [C1]。

## B03 / round 1

Question: 我这次出差在2026年5月10日结束，差旅报销期限多久？

Status: answered / None. [Input](verified-candidate/B03/20261028T133731Z-785f64426a7c/input.json), [Output](verified-candidate/B03/20261028T133731Z-785f64426a7c/output.json), [Trace](verified-candidate/B03/20261028T133731Z-785f64426a7c/trace.jsonl).

| Step | Tool | Arguments | Observation | Next action | Next model basis |
|---|---|---|---|---|---|
| 1 | search_documents | {"query": "差旅报销期限 2026年5月10日 出差结束", "top_k": 5} | hits=5 | read_passage | 确认2026年4月1日及以后出差的报销期限是否为15天 |
| 2 | read_passage | {"document_id": "D06", "passage_id": "P01"} | Original passage read | read_passage | 确认新通知是否替代旧规定，以及替代范围 |
| 3 | read_passage | {"document_id": "D06", "passage_id": "P02"} | Original passage read | finish:answered | 您本次差旅的报销期限为行程结束后15天内。 |
| 6 | read_passage | {"document_id": "D01", "passage_id": "P01"} | Original passage read | read_passage | 核查旧规定中差旅报销期限是否与新通知冲突 |
| 7 | read_passage | {"document_id": "D02", "passage_id": "P01"} | Original passage read | finish:answered | 您本次差旅的报销期限为行程结束后15天内。根据《差旅报销期限统一执行通知》（D06，2026-04-01），自2026年4月1日起，行程结束日期在2026年4月1日及以后的差旅报销统一在行程结束后15天内提交 [C1]。该规定已明确替代此前《差旅报销提交规定》（D01）中30天的期限 [C2] 和《差旅费用报销办理说明》（D02）中15天的期限 [C3]。尽管旧规定中已有15天期限，但新通知确认其适用范围覆盖本次出差，并作为现行有效规则执行。 |

Final answer: 您本次差旅的报销期限为行程结束后15天内。根据《差旅报销期限统一执行通知》（D06，2026-04-01），自2026年4月1日起，行程结束日期在2026年4月1日及以后的差旅报销统一在行程结束后15天内提交 [C1]。该规定已明确替代此前《差旅报销提交规定》（D01）中30天的期限 [C2] 和《差旅费用报销办理说明》（D02）中15天的期限 [C3]。尽管旧规定中已有15天期限，但新通知确认其适用范围覆盖本次出差，并作为现行有效规则执行。同时，通知中明确指出本条款替代D01和D02中的报销提交期限条款，确保了规则的优先性与一致性 [C4]。

AI review note: supersession proof exists as C4, but earlier C2/C3 placement is ambiguous; see ai-review.json.

## B08 / round 1

Question: 差旅报销应在行程结束后多久内提交？

Status: answered / None. [Input](verified-candidate/B08/20261028T133808Z-5fbba3bcae6f/input.json), [Output](verified-candidate/B08/20261028T133808Z-5fbba3bcae6f/output.json), [Trace](verified-candidate/B08/20261028T133808Z-5fbba3bcae6f/trace.jsonl).

| Step | Tool | Arguments | Observation | Next action | Next model basis |
|---|---|---|---|---|---|
| 1 | search_documents | {"query": "差旅报销提交期限 行程结束后", "top_k": 5} | hits=5 | read_passage | 读取差旅报销提交期限的具体规定原文，以确认适用条件和时间要求 |
| 2 | read_passage | {"document_id": "D01", "passage_id": "P01"} | unavailable | read_passage | 尝试重新读取差旅报销提交期限的相关原文，确保获取准确信息 |
| 3 | read_passage | {"document_id": "D01", "passage_id": "P01"} | Original passage read | finish:answered | 差旅报销应在行程结束后30天内提交。 |

Final answer: 差旅报销应在行程结束后30天内提交 [C1]。

## B12 / round 1

Question: 差旅报销应在行程结束后多久内提交？

Status: answered / None. [Input](verified-candidate/B12/20261028T133829Z-8eeb2a60cb3b/input.json), [Output](verified-candidate/B12/20261028T133829Z-8eeb2a60cb3b/output.json), [Trace](verified-candidate/B12/20261028T133829Z-8eeb2a60cb3b/trace.jsonl).

| Step | Tool | Arguments | Observation | Next action | Next model basis |
|---|---|---|---|---|---|
| 1 | search_documents | {"query": "差旅报销提交期限 行程结束后", "top_k": 5} | hits=0 | search_documents | 尝试不同关键词组合，扩大检索范围以找到差旅报销提交时限的相关规定 |
| 2 | search_documents | {"query": "差旅报销 时限 提交期限", "top_k": 5} | hits=5 | read_passage | 读取差旅报销提交期限的具体规定，以确认行程结束后应在多少天内提交 |
| 3 | read_passage | {"document_id": "D01", "passage_id": "P01"} | Original passage read | finish:answered | 差旅报销应在行程结束后30天内提交。 |

Final answer: 差旅报销应在行程结束后30天内提交 [C1]。

## B02 / round 1

Question: 差旅报销应在行程结束后多久内提交？

Status: incomplete / invalid_model_output. [Input](verified-candidate/B02/20261028T133720Z-f67ee110415e/input.json), [Output](verified-candidate/B02/20261028T133720Z-f67ee110415e/output.json), [Trace](verified-candidate/B02/20261028T133720Z-f67ee110415e/trace.jsonl).

| Step | Tool | Arguments | Observation | Next action | Next model basis |
|---|---|---|---|---|---|
| 1 | search_documents | {"query": "差旅报销提交期限 行程结束后", "top_k": 5} | hits=5 | read_passage | 读取差旅报销提交期限的具体规定，确认30天内的要求 |
| 2 | read_passage | {"document_id": "D01", "passage_id": "P01"} | Original passage read | read_passage | 读取另一份规定中关于差旅报销提交期限的内容，以确认是否存在冲突或优先级关系 |
| 3 | read_passage | {"document_id": "D02", "passage_id": "P01"} | Original passage read | finish:needs_clarification | 差旅报销提交期限存在冲突规定：一份文件要求在行程结束后30天内提交（[D01]），另一份文件要求在15天内提交（[D02]）。需确认适用制度或补充说明具体事件的日期范围以判断应遵循哪一规定。 |

Final answer: 任务未完成：连续相同模型校验错误达到修复上限，未生成可靠结果。
