# Saved-evidence audit

Offline recheck; no model requests. Business validators are reused; trace integrity and paired comparisons are additional checks.

Finite checks do not establish full semantic correctness or causal model reasoning. AI review is separate from candidate independent verification.

Recorded runs: 26; audit passes: 26. Not-executed, missing, malformed and duplicate records fail closed.

## Outcomes by case

| Case | Records | Audit passes | Actual outcomes |
|---|---|---|---|
| A01 | 2 | 2 | {"answered": 2} |
| A02 | 2 | 2 | {"needs_clarification": 2} |
| A03 | 2 | 2 | {"unanswerable": 2} |
| A04 | 2 | 2 | {"answered": 2} |
| A05 | 2 | 2 | {"answered": 2} |
| A06 | 2 | 2 | {"incomplete": 2} |
| B01 | 2 | 2 | {"answered": 2} |
| B03 | 2 | 2 | {"answered": 2} |
| B04 | 2 | 2 | {"needs_clarification": 2} |
| B08 | 2 | 2 | {"incomplete": 2} |
| B11 | 2 | 2 | {"needs_clarification": 2} |
| B12 | 2 | 2 | {"answered": 2} |
| B15 | 2 | 2 | {"answered": 2} |

## Run evidence

| Case | Round | Status | Audit | Model/tools | Input | Output | Trace |
|---|---|---|---|---|---|---|---|
| A01 | 1 | answered | PASS | 8/2 | [input](../../stage4/verified-release/A01/20261028T105940Z-e980e0c567a1/input.json) | [output](../../stage4/verified-release/A01/20261028T105940Z-e980e0c567a1/output.json) | [trace](../../stage4/verified-release/A01/20261028T105940Z-e980e0c567a1/trace.jsonl) |
| A02 | 1 | needs_clarification | PASS | 8/4 | [input](../../stage4/verified-release/A02/20261028T105946Z-2938ac7a2ea6/input.json) | [output](../../stage4/verified-release/A02/20261028T105946Z-2938ac7a2ea6/output.json) | [trace](../../stage4/verified-release/A02/20261028T105946Z-2938ac7a2ea6/trace.jsonl) |
| A03 | 1 | unanswerable | PASS | 6/3 | [input](../../stage4/verified-release/A03/20261028T105959Z-08512463e5a3/input.json) | [output](../../stage4/verified-release/A03/20261028T105959Z-08512463e5a3/output.json) | [trace](../../stage4/verified-release/A03/20261028T105959Z-08512463e5a3/trace.jsonl) |
| A04 | 1 | answered | PASS | 7/2 | [input](../../stage4/verified-release/A04/20261028T110005Z-e681265ede4b/input.json) | [output](../../stage4/verified-release/A04/20261028T110005Z-e681265ede4b/output.json) | [trace](../../stage4/verified-release/A04/20261028T110005Z-e681265ede4b/trace.jsonl) |
| A05 | 1 | answered | PASS | 10/3 | [input](../../stage4/verified-release/A05/20261028T110010Z-80e47ae266ab/input.json) | [output](../../stage4/verified-release/A05/20261028T110010Z-80e47ae266ab/output.json) | [trace](../../stage4/verified-release/A05/20261028T110010Z-80e47ae266ab/trace.jsonl) |
| A06 | 1 | incomplete | PASS | 10/5 | [input](../../stage4/verified-release/A06/20261028T110023Z-2de350b4f35b/input.json) | [output](../../stage4/verified-release/A06/20261028T110023Z-2de350b4f35b/output.json) | [trace](../../stage4/verified-release/A06/20261028T110023Z-2de350b4f35b/trace.jsonl) |
| B01 | 1 | answered | PASS | 8/2 | [input](../../stage4/verified-release/B01/20261028T110034Z-b4766b4caf79/input.json) | [output](../../stage4/verified-release/B01/20261028T110034Z-b4766b4caf79/output.json) | [trace](../../stage4/verified-release/B01/20261028T110034Z-b4766b4caf79/trace.jsonl) |
| B03 | 1 | answered | PASS | 8/3 | [input](../../stage4/verified-release/B03/20261028T110041Z-0738b31f21ce/input.json) | [output](../../stage4/verified-release/B03/20261028T110041Z-0738b31f21ce/output.json) | [trace](../../stage4/verified-release/B03/20261028T110041Z-0738b31f21ce/trace.jsonl) |
| B04 | 1 | needs_clarification | PASS | 9/3 | [input](../../stage4/verified-release/B04/20261028T110051Z-0c10ffd187e2/input.json) | [output](../../stage4/verified-release/B04/20261028T110051Z-0c10ffd187e2/output.json) | [trace](../../stage4/verified-release/B04/20261028T110051Z-0c10ffd187e2/trace.jsonl) |
| B08 | 1 | incomplete | PASS | 12/5 | [input](../../stage4/verified-release/B08/20261028T110105Z-2c3f71733cbd/input.json) | [output](../../stage4/verified-release/B08/20261028T110105Z-2c3f71733cbd/output.json) | [trace](../../stage4/verified-release/B08/20261028T110105Z-2c3f71733cbd/trace.jsonl) |
| B11 | 1 | needs_clarification | PASS | 1/0 | [input](../../stage4/verified-release/B11/20261028T110117Z-ead754d4eba3/input.json) | [output](../../stage4/verified-release/B11/20261028T110117Z-ead754d4eba3/output.json) | [trace](../../stage4/verified-release/B11/20261028T110117Z-ead754d4eba3/trace.jsonl) |
| B12 | 1 | answered | PASS | 9/3 | [input](../../stage4/verified-release/B12/20261028T110118Z-38dd69de8b3b/input.json) | [output](../../stage4/verified-release/B12/20261028T110118Z-38dd69de8b3b/output.json) | [trace](../../stage4/verified-release/B12/20261028T110118Z-38dd69de8b3b/trace.jsonl) |
| B15 | 1 | answered | PASS | 9/3 | [input](../../stage4/verified-release/B15/20261028T110127Z-813a8eabce61/input.json) | [output](../../stage4/verified-release/B15/20261028T110127Z-813a8eabce61/output.json) | [trace](../../stage4/verified-release/B15/20261028T110127Z-813a8eabce61/trace.jsonl) |
| A01 | 2 | answered | PASS | 8/2 | [input](../../stage4/verified-release/A01/20261028T110138Z-e6a628c62750/input.json) | [output](../../stage4/verified-release/A01/20261028T110138Z-e6a628c62750/output.json) | [trace](../../stage4/verified-release/A01/20261028T110138Z-e6a628c62750/trace.jsonl) |
| A02 | 2 | needs_clarification | PASS | 8/4 | [input](../../stage4/verified-release/A02/20261028T110145Z-0f91971048db/input.json) | [output](../../stage4/verified-release/A02/20261028T110145Z-0f91971048db/output.json) | [trace](../../stage4/verified-release/A02/20261028T110145Z-0f91971048db/trace.jsonl) |
| A03 | 2 | unanswerable | PASS | 4/2 | [input](../../stage4/verified-release/A03/20261028T110157Z-5e9741fc5110/input.json) | [output](../../stage4/verified-release/A03/20261028T110157Z-5e9741fc5110/output.json) | [trace](../../stage4/verified-release/A03/20261028T110157Z-5e9741fc5110/trace.jsonl) |
| A04 | 2 | answered | PASS | 8/2 | [input](../../stage4/verified-release/A04/20261028T110200Z-35136318fc22/input.json) | [output](../../stage4/verified-release/A04/20261028T110200Z-35136318fc22/output.json) | [trace](../../stage4/verified-release/A04/20261028T110200Z-35136318fc22/trace.jsonl) |
| A05 | 2 | answered | PASS | 8/2 | [input](../../stage4/verified-release/A05/20261028T110207Z-4f02eb8ffcb0/input.json) | [output](../../stage4/verified-release/A05/20261028T110207Z-4f02eb8ffcb0/output.json) | [trace](../../stage4/verified-release/A05/20261028T110207Z-4f02eb8ffcb0/trace.jsonl) |
| A06 | 2 | incomplete | PASS | 8/5 | [input](../../stage4/verified-release/A06/20261028T110216Z-48dfb3af7d8c/input.json) | [output](../../stage4/verified-release/A06/20261028T110216Z-48dfb3af7d8c/output.json) | [trace](../../stage4/verified-release/A06/20261028T110216Z-48dfb3af7d8c/trace.jsonl) |
| B01 | 2 | answered | PASS | 8/2 | [input](../../stage4/verified-release/B01/20261028T110223Z-cee50445d561/input.json) | [output](../../stage4/verified-release/B01/20261028T110223Z-cee50445d561/output.json) | [trace](../../stage4/verified-release/B01/20261028T110223Z-cee50445d561/trace.jsonl) |
| B03 | 2 | answered | PASS | 9/3 | [input](../../stage4/verified-release/B03/20261028T110230Z-798621f19c69/input.json) | [output](../../stage4/verified-release/B03/20261028T110230Z-798621f19c69/output.json) | [trace](../../stage4/verified-release/B03/20261028T110230Z-798621f19c69/trace.jsonl) |
| B04 | 2 | needs_clarification | PASS | 9/3 | [input](../../stage4/verified-release/B04/20261028T110243Z-595a21696775/input.json) | [output](../../stage4/verified-release/B04/20261028T110243Z-595a21696775/output.json) | [trace](../../stage4/verified-release/B04/20261028T110243Z-595a21696775/trace.jsonl) |
| B08 | 2 | incomplete | PASS | 11/6 | [input](../../stage4/verified-release/B08/20261028T110257Z-d19a1324c54e/input.json) | [output](../../stage4/verified-release/B08/20261028T110257Z-d19a1324c54e/output.json) | [trace](../../stage4/verified-release/B08/20261028T110257Z-d19a1324c54e/trace.jsonl) |
| B11 | 2 | needs_clarification | PASS | 1/0 | [input](../../stage4/verified-release/B11/20261028T110310Z-d91886bc1ae7/input.json) | [output](../../stage4/verified-release/B11/20261028T110310Z-d91886bc1ae7/output.json) | [trace](../../stage4/verified-release/B11/20261028T110310Z-d91886bc1ae7/trace.jsonl) |
| B12 | 2 | answered | PASS | 9/3 | [input](../../stage4/verified-release/B12/20261028T110311Z-c8a98f2263ca/input.json) | [output](../../stage4/verified-release/B12/20261028T110311Z-c8a98f2263ca/output.json) | [trace](../../stage4/verified-release/B12/20261028T110311Z-c8a98f2263ca/trace.jsonl) |
| B15 | 2 | answered | PASS | 9/3 | [input](../../stage4/verified-release/B15/20261028T110319Z-2b8709ddea04/input.json) | [output](../../stage4/verified-release/B15/20261028T110319Z-2b8709ddea04/output.json) | [trace](../../stage4/verified-release/B15/20261028T110319Z-2b8709ddea04/trace.jsonl) |

## Paired comparisons

| Comparison | Left run | Right run | Result |
|---|---|---|---|
| paraphrase | 20261028T105940Z-e980e0c567a1 | 20261028T110005Z-e681265ede4b | PASS |
| replacement | 20261028T105940Z-e980e0c567a1 | 20261028T110034Z-b4766b4caf79 | PASS |
| conflict_scenario | 20261028T105940Z-e980e0c567a1 | 20261028T105946Z-2938ac7a2ea6 | PASS |
| paraphrase | 20261028T110138Z-e6a628c62750 | 20261028T110200Z-35136318fc22 | PASS |
| replacement | 20261028T110138Z-e6a628c62750 | 20261028T110223Z-cee50445d561 | PASS |
| conflict_scenario | 20261028T110138Z-e6a628c62750 | 20261028T110145Z-0f91971048db | PASS |

Every tool argument, observation summary and next model action is indexed in audit.json under runs[].transitions. Artifact hashes are audit-time checksums, not signatures or proof against deliberate forgery.
