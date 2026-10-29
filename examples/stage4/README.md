# Stage 4 evidence index

Final batch: **verified-release**. 26/26 finite checks passed (13 cases, two repetitions); core A01-A06: 12/12. One engine revision and one model configuration. See [summary.json](summary.json), [local test report](test-results.txt) (81 passed) and [Chinese report](../../docs/10-reliability.md).

Automatic pass is not full semantic verification. B08 permits bounded incomplete: both final runs are incomplete, so recovery is not proven. The previous release-validation batch passed automatic checks but AI review found unsupported date calculations; its original outputs and [review findings](release-validation/manual-review.json) are preserved. No historical output was rewritten.

Reproduction from repository root:

```text
python -m src.kb_agent.evaluate --mode real --thinking-mode off --cases A01 A02 A03 A04 A05 A06 B01 B03 B04 B08 B11 B12 B15 --repeat 2 --output-dir examples/my-stage4-run
```

Qwen qwen-flash; native action protocol; thinking off; action streaming off; other requests follow stream configuration. Model/tool budgets: 12/6. All resolver and review calls count. Credentials stay in local .env.

## Final runs

| Case | Round | Status | Reason | Model/tool calls | Input | Output | Trace |
|---|---|---|---|---|---|---|---|
| A01 | 1 | answered | - | 8/2 | [input](verified-release/A01/20261028T105940Z-e980e0c567a1/input.json) | [output](verified-release/A01/20261028T105940Z-e980e0c567a1/output.json) | [trace](verified-release/A01/20261028T105940Z-e980e0c567a1/trace.jsonl) |
| A02 | 1 | needs_clarification | document_conflict | 8/4 | [input](verified-release/A02/20261028T105946Z-2938ac7a2ea6/input.json) | [output](verified-release/A02/20261028T105946Z-2938ac7a2ea6/output.json) | [trace](verified-release/A02/20261028T105946Z-2938ac7a2ea6/trace.jsonl) |
| A03 | 1 | unanswerable | insufficient_evidence | 6/3 | [input](verified-release/A03/20261028T105959Z-08512463e5a3/input.json) | [output](verified-release/A03/20261028T105959Z-08512463e5a3/output.json) | [trace](verified-release/A03/20261028T105959Z-08512463e5a3/trace.jsonl) |
| A04 | 1 | answered | - | 7/2 | [input](verified-release/A04/20261028T110005Z-e681265ede4b/input.json) | [output](verified-release/A04/20261028T110005Z-e681265ede4b/output.json) | [trace](verified-release/A04/20261028T110005Z-e681265ede4b/trace.jsonl) |
| A05 | 1 | answered | - | 10/3 | [input](verified-release/A05/20261028T110010Z-80e47ae266ab/input.json) | [output](verified-release/A05/20261028T110010Z-80e47ae266ab/output.json) | [trace](verified-release/A05/20261028T110010Z-80e47ae266ab/trace.jsonl) |
| A06 | 1 | incomplete | tool_failure | 10/5 | [input](verified-release/A06/20261028T110023Z-2de350b4f35b/input.json) | [output](verified-release/A06/20261028T110023Z-2de350b4f35b/output.json) | [trace](verified-release/A06/20261028T110023Z-2de350b4f35b/trace.jsonl) |
| B01 | 1 | answered | - | 8/2 | [input](verified-release/B01/20261028T110034Z-b4766b4caf79/input.json) | [output](verified-release/B01/20261028T110034Z-b4766b4caf79/output.json) | [trace](verified-release/B01/20261028T110034Z-b4766b4caf79/trace.jsonl) |
| B03 | 1 | answered | - | 8/3 | [input](verified-release/B03/20261028T110041Z-0738b31f21ce/input.json) | [output](verified-release/B03/20261028T110041Z-0738b31f21ce/output.json) | [trace](verified-release/B03/20261028T110041Z-0738b31f21ce/trace.jsonl) |
| B04 | 1 | needs_clarification | missing_user_context | 9/3 | [input](verified-release/B04/20261028T110051Z-0c10ffd187e2/input.json) | [output](verified-release/B04/20261028T110051Z-0c10ffd187e2/output.json) | [trace](verified-release/B04/20261028T110051Z-0c10ffd187e2/trace.jsonl) |
| B08 | 1 | incomplete | budget_exhausted | 12/5 | [input](verified-release/B08/20261028T110105Z-2c3f71733cbd/input.json) | [output](verified-release/B08/20261028T110105Z-2c3f71733cbd/output.json) | [trace](verified-release/B08/20261028T110105Z-2c3f71733cbd/trace.jsonl) |
| B11 | 1 | needs_clarification | ambiguous_reference | 1/0 | [input](verified-release/B11/20261028T110117Z-ead754d4eba3/input.json) | [output](verified-release/B11/20261028T110117Z-ead754d4eba3/output.json) | [trace](verified-release/B11/20261028T110117Z-ead754d4eba3/trace.jsonl) |
| B12 | 1 | answered | - | 9/3 | [input](verified-release/B12/20261028T110118Z-38dd69de8b3b/input.json) | [output](verified-release/B12/20261028T110118Z-38dd69de8b3b/output.json) | [trace](verified-release/B12/20261028T110118Z-38dd69de8b3b/trace.jsonl) |
| B15 | 1 | answered | - | 9/3 | [input](verified-release/B15/20261028T110127Z-813a8eabce61/input.json) | [output](verified-release/B15/20261028T110127Z-813a8eabce61/output.json) | [trace](verified-release/B15/20261028T110127Z-813a8eabce61/trace.jsonl) |
| A01 | 2 | answered | - | 8/2 | [input](verified-release/A01/20261028T110138Z-e6a628c62750/input.json) | [output](verified-release/A01/20261028T110138Z-e6a628c62750/output.json) | [trace](verified-release/A01/20261028T110138Z-e6a628c62750/trace.jsonl) |
| A02 | 2 | needs_clarification | document_conflict | 8/4 | [input](verified-release/A02/20261028T110145Z-0f91971048db/input.json) | [output](verified-release/A02/20261028T110145Z-0f91971048db/output.json) | [trace](verified-release/A02/20261028T110145Z-0f91971048db/trace.jsonl) |
| A03 | 2 | unanswerable | insufficient_evidence | 4/2 | [input](verified-release/A03/20261028T110157Z-5e9741fc5110/input.json) | [output](verified-release/A03/20261028T110157Z-5e9741fc5110/output.json) | [trace](verified-release/A03/20261028T110157Z-5e9741fc5110/trace.jsonl) |
| A04 | 2 | answered | - | 8/2 | [input](verified-release/A04/20261028T110200Z-35136318fc22/input.json) | [output](verified-release/A04/20261028T110200Z-35136318fc22/output.json) | [trace](verified-release/A04/20261028T110200Z-35136318fc22/trace.jsonl) |
| A05 | 2 | answered | - | 8/2 | [input](verified-release/A05/20261028T110207Z-4f02eb8ffcb0/input.json) | [output](verified-release/A05/20261028T110207Z-4f02eb8ffcb0/output.json) | [trace](verified-release/A05/20261028T110207Z-4f02eb8ffcb0/trace.jsonl) |
| A06 | 2 | incomplete | tool_failure | 8/5 | [input](verified-release/A06/20261028T110216Z-48dfb3af7d8c/input.json) | [output](verified-release/A06/20261028T110216Z-48dfb3af7d8c/output.json) | [trace](verified-release/A06/20261028T110216Z-48dfb3af7d8c/trace.jsonl) |
| B01 | 2 | answered | - | 8/2 | [input](verified-release/B01/20261028T110223Z-cee50445d561/input.json) | [output](verified-release/B01/20261028T110223Z-cee50445d561/output.json) | [trace](verified-release/B01/20261028T110223Z-cee50445d561/trace.jsonl) |
| B03 | 2 | answered | - | 9/3 | [input](verified-release/B03/20261028T110230Z-798621f19c69/input.json) | [output](verified-release/B03/20261028T110230Z-798621f19c69/output.json) | [trace](verified-release/B03/20261028T110230Z-798621f19c69/trace.jsonl) |
| B04 | 2 | needs_clarification | missing_user_context | 9/3 | [input](verified-release/B04/20261028T110243Z-595a21696775/input.json) | [output](verified-release/B04/20261028T110243Z-595a21696775/output.json) | [trace](verified-release/B04/20261028T110243Z-595a21696775/trace.jsonl) |
| B08 | 2 | incomplete | tool_failure | 11/6 | [input](verified-release/B08/20261028T110257Z-d19a1324c54e/input.json) | [output](verified-release/B08/20261028T110257Z-d19a1324c54e/output.json) | [trace](verified-release/B08/20261028T110257Z-d19a1324c54e/trace.jsonl) |
| B11 | 2 | needs_clarification | ambiguous_reference | 1/0 | [input](verified-release/B11/20261028T110310Z-d91886bc1ae7/input.json) | [output](verified-release/B11/20261028T110310Z-d91886bc1ae7/output.json) | [trace](verified-release/B11/20261028T110310Z-d91886bc1ae7/trace.jsonl) |
| B12 | 2 | answered | - | 9/3 | [input](verified-release/B12/20261028T110311Z-c8a98f2263ca/input.json) | [output](verified-release/B12/20261028T110311Z-c8a98f2263ca/output.json) | [trace](verified-release/B12/20261028T110311Z-c8a98f2263ca/trace.jsonl) |
| B15 | 2 | answered | - | 9/3 | [input](verified-release/B15/20261028T110319Z-2b8709ddea04/input.json) | [output](verified-release/B15/20261028T110319Z-2b8709ddea04/output.json) | [trace](verified-release/B15/20261028T110319Z-2b8709ddea04/trace.jsonl) |

## Development batches (failures retained)

Counts are completed records, not planned runs. The regression batch was interrupted; unexecuted cases are not passes. Early pilot checks were weaker, so cross-batch pass counts are not a controlled comparison.

| Batch | Completed | Automatic passes | Notes |
|---|---|---|---|
| [acceptance](acceptance/evaluation-results.json) | 26 | 23 | finite assertions |
| [context-isolation](context-isolation/evaluation-results.json) | 5 | 4 | finite assertions |
| [final-regression](final-regression/evaluation-results.json) | 26 | 23 | finite assertions |
| [native-pilot](native-pilot/evaluation-results.json) | 6 | 2 | finite assertions |
| [pilot](pilot/evaluation-results.json) | 13 | 10 | early weaker checks |
| [regression](regression/evaluation-results.json) | 5 | 0 | finite assertions; interrupted |
| [release-validation](release-validation/evaluation-results.json) | 26 | 26 | finite assertions; manual review found unsupported dates |
| [reviewer-fix](reviewer-fix/evaluation-results.json) | 4 | 1 | finite assertions |
| [verified-release](verified-release/evaluation-results.json) | 26 | 26 | finite assertions |

The [retrieval comparison](retrieval-filter-comparison.json) covers one real out-of-corpus query only. Historical stage 3 runs are indexed [separately](../qwen-validation/README.md). No model internal reasoning or secret is recorded.
