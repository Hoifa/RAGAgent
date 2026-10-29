# Saved-evidence audit

Offline recheck; no model requests. Business validators are reused; trace integrity and paired comparisons are additional checks.

Finite checks do not establish full semantic correctness or causal model reasoning. AI review is separate from candidate independent verification.

Recorded runs: 36; audit passes: 30. Not-executed, missing, malformed and duplicate records fail closed.

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
| B02 | 2 | 1 | {"incomplete": 1, "needs_clarification": 1} |
| B03 | 2 | 1 | {"answered": 1, "incomplete": 1} |
| B04 | 2 | 2 | {"needs_clarification": 2} |
| B07 | 2 | 1 | {"needs_clarification": 1, "incomplete": 1} |
| B08 | 2 | 2 | {"answered": 2} |
| B09 | 2 | 2 | {"answered": 2} |
| B11 | 2 | 1 | {"needs_clarification": 1, "answered": 1} |
| B12 | 2 | 2 | {"answered": 2} |
| B15 | 2 | 2 | {"answered": 2} |
| B16 | 2 | 1 | {"incomplete": 1, "needs_clarification": 1} |
| B17 | 2 | 1 | {"needs_clarification": 1, "incomplete": 1} |

## Run evidence

| Case | Round | Status | Audit | Model/tools | Input | Output | Trace |
|---|---|---|---|---|---|---|---|
| A01 | 1 | answered | PASS | 6/2 | [input](../verified-candidate/A01/20261028T133634Z-52e3eb66263c/input.json) | [output](../verified-candidate/A01/20261028T133634Z-52e3eb66263c/output.json) | [trace](../verified-candidate/A01/20261028T133634Z-52e3eb66263c/trace.jsonl) |
| A02 | 1 | needs_clarification | PASS | 7/4 | [input](../verified-candidate/A02/20261028T133640Z-4b2da5066d92/input.json) | [output](../verified-candidate/A02/20261028T133640Z-4b2da5066d92/output.json) | [trace](../verified-candidate/A02/20261028T133640Z-4b2da5066d92/trace.jsonl) |
| A03 | 1 | unanswerable | PASS | 3/2 | [input](../verified-candidate/A03/20261028T133653Z-9b96fa9fb31a/input.json) | [output](../verified-candidate/A03/20261028T133653Z-9b96fa9fb31a/output.json) | [trace](../verified-candidate/A03/20261028T133653Z-9b96fa9fb31a/trace.jsonl) |
| A04 | 1 | answered | PASS | 6/2 | [input](../verified-candidate/A04/20261028T133656Z-d65c230ff125/input.json) | [output](../verified-candidate/A04/20261028T133656Z-d65c230ff125/output.json) | [trace](../verified-candidate/A04/20261028T133656Z-d65c230ff125/trace.jsonl) |
| A05 | 1 | answered | PASS | 7/2 | [input](../verified-candidate/A05/20261028T133702Z-563e68aea4b2/input.json) | [output](../verified-candidate/A05/20261028T133702Z-563e68aea4b2/output.json) | [trace](../verified-candidate/A05/20261028T133702Z-563e68aea4b2/trace.jsonl) |
| A06 | 1 | incomplete | PASS | 4/3 | [input](../verified-candidate/A06/20261028T133710Z-a60b8e25c113/input.json) | [output](../verified-candidate/A06/20261028T133710Z-a60b8e25c113/output.json) | [trace](../verified-candidate/A06/20261028T133710Z-a60b8e25c113/trace.jsonl) |
| B01 | 1 | answered | PASS | 6/2 | [input](../verified-candidate/B01/20261028T133714Z-184a6c191a77/input.json) | [output](../verified-candidate/B01/20261028T133714Z-184a6c191a77/output.json) | [trace](../verified-candidate/B01/20261028T133714Z-184a6c191a77/trace.jsonl) |
| B02 | 1 | incomplete | FAIL | 6/3 | [input](../verified-candidate/B02/20261028T133720Z-f67ee110415e/input.json) | [output](../verified-candidate/B02/20261028T133720Z-f67ee110415e/output.json) | [trace](../verified-candidate/B02/20261028T133720Z-f67ee110415e/trace.jsonl) |
| B03 | 1 | answered | PASS | 12/5 | [input](../verified-candidate/B03/20261028T133731Z-785f64426a7c/input.json) | [output](../verified-candidate/B03/20261028T133731Z-785f64426a7c/output.json) | [trace](../verified-candidate/B03/20261028T133731Z-785f64426a7c/trace.jsonl) |
| B04 | 1 | needs_clarification | PASS | 5/3 | [input](../verified-candidate/B04/20261028T133756Z-29723d35caaa/input.json) | [output](../verified-candidate/B04/20261028T133756Z-29723d35caaa/output.json) | [trace](../verified-candidate/B04/20261028T133756Z-29723d35caaa/trace.jsonl) |
| B07 | 1 | needs_clarification | PASS | 2/0 | [input](../verified-candidate/B07/20261028T133805Z-2453116cf334/input.json) | [output](../verified-candidate/B07/20261028T133805Z-2453116cf334/output.json) | [trace](../verified-candidate/B07/20261028T133805Z-2453116cf334/trace.jsonl) |
| B08 | 1 | answered | PASS | 10/3 | [input](../verified-candidate/B08/20261028T133808Z-5fbba3bcae6f/input.json) | [output](../verified-candidate/B08/20261028T133808Z-5fbba3bcae6f/output.json) | [trace](../verified-candidate/B08/20261028T133808Z-5fbba3bcae6f/trace.jsonl) |
| B09 | 1 | answered | PASS | 7/2 | [input](../verified-candidate/B09/20261028T133818Z-4298cfa6a2e1/input.json) | [output](../verified-candidate/B09/20261028T133818Z-4298cfa6a2e1/output.json) | [trace](../verified-candidate/B09/20261028T133818Z-4298cfa6a2e1/trace.jsonl) |
| B11 | 1 | needs_clarification | PASS | 2/0 | [input](../verified-candidate/B11/20261028T133827Z-3e9b5ff15eaf/input.json) | [output](../verified-candidate/B11/20261028T133827Z-3e9b5ff15eaf/output.json) | [trace](../verified-candidate/B11/20261028T133827Z-3e9b5ff15eaf/trace.jsonl) |
| B12 | 1 | answered | PASS | 8/3 | [input](../verified-candidate/B12/20261028T133829Z-8eeb2a60cb3b/input.json) | [output](../verified-candidate/B12/20261028T133829Z-8eeb2a60cb3b/output.json) | [trace](../verified-candidate/B12/20261028T133829Z-8eeb2a60cb3b/trace.jsonl) |
| B15 | 1 | answered | PASS | 7/3 | [input](../verified-candidate/B15/20261028T133838Z-d351bf9112b7/input.json) | [output](../verified-candidate/B15/20261028T133838Z-d351bf9112b7/output.json) | [trace](../verified-candidate/B15/20261028T133838Z-d351bf9112b7/trace.jsonl) |
| B16 | 1 | incomplete | FAIL | 12/6 | [input](../verified-candidate/B16/20261028T133852Z-b418bde02633/input.json) | [output](../verified-candidate/B16/20261028T133852Z-b418bde02633/output.json) | [trace](../verified-candidate/B16/20261028T133852Z-b418bde02633/trace.jsonl) |
| B17 | 1 | needs_clarification | PASS | 10/6 | [input](../verified-candidate/B17/20261028T133919Z-897870b9f7fb/input.json) | [output](../verified-candidate/B17/20261028T133919Z-897870b9f7fb/output.json) | [trace](../verified-candidate/B17/20261028T133919Z-897870b9f7fb/trace.jsonl) |
| A01 | 2 | answered | PASS | 6/2 | [input](../verified-candidate/A01/20261028T133943Z-14688063edbe/input.json) | [output](../verified-candidate/A01/20261028T133943Z-14688063edbe/output.json) | [trace](../verified-candidate/A01/20261028T133943Z-14688063edbe/trace.jsonl) |
| A02 | 2 | needs_clarification | PASS | 7/4 | [input](../verified-candidate/A02/20261028T133949Z-55c7e0c57d0d/input.json) | [output](../verified-candidate/A02/20261028T133949Z-55c7e0c57d0d/output.json) | [trace](../verified-candidate/A02/20261028T133949Z-55c7e0c57d0d/trace.jsonl) |
| A03 | 2 | unanswerable | PASS | 3/2 | [input](../verified-candidate/A03/20261028T134003Z-70352deb6f5d/input.json) | [output](../verified-candidate/A03/20261028T134003Z-70352deb6f5d/output.json) | [trace](../verified-candidate/A03/20261028T134003Z-70352deb6f5d/trace.jsonl) |
| A04 | 2 | answered | PASS | 6/2 | [input](../verified-candidate/A04/20261028T134005Z-ba1782acf2aa/input.json) | [output](../verified-candidate/A04/20261028T134005Z-ba1782acf2aa/output.json) | [trace](../verified-candidate/A04/20261028T134005Z-ba1782acf2aa/trace.jsonl) |
| A05 | 2 | answered | PASS | 7/2 | [input](../verified-candidate/A05/20261028T134014Z-42f22f0d6a1c/input.json) | [output](../verified-candidate/A05/20261028T134014Z-42f22f0d6a1c/output.json) | [trace](../verified-candidate/A05/20261028T134014Z-42f22f0d6a1c/trace.jsonl) |
| A06 | 2 | incomplete | PASS | 4/3 | [input](../verified-candidate/A06/20261028T134022Z-7e7a009a6c2c/input.json) | [output](../verified-candidate/A06/20261028T134022Z-7e7a009a6c2c/output.json) | [trace](../verified-candidate/A06/20261028T134022Z-7e7a009a6c2c/trace.jsonl) |
| B01 | 2 | answered | PASS | 6/2 | [input](../verified-candidate/B01/20261028T134027Z-3212459699f1/input.json) | [output](../verified-candidate/B01/20261028T134027Z-3212459699f1/output.json) | [trace](../verified-candidate/B01/20261028T134027Z-3212459699f1/trace.jsonl) |
| B02 | 2 | needs_clarification | PASS | 7/4 | [input](../verified-candidate/B02/20261028T134034Z-cc3ccb590691/input.json) | [output](../verified-candidate/B02/20261028T134034Z-cc3ccb590691/output.json) | [trace](../verified-candidate/B02/20261028T134034Z-cc3ccb590691/trace.jsonl) |
| B03 | 2 | incomplete | FAIL | 6/3 | [input](../verified-candidate/B03/20261028T134049Z-59c3b363a105/input.json) | [output](../verified-candidate/B03/20261028T134049Z-59c3b363a105/output.json) | [trace](../verified-candidate/B03/20261028T134049Z-59c3b363a105/trace.jsonl) |
| B04 | 2 | needs_clarification | PASS | 5/3 | [input](../verified-candidate/B04/20261028T134102Z-945fb249df89/input.json) | [output](../verified-candidate/B04/20261028T134102Z-945fb249df89/output.json) | [trace](../verified-candidate/B04/20261028T134102Z-945fb249df89/trace.jsonl) |
| B07 | 2 | incomplete | FAIL | 12/3 | [input](../verified-candidate/B07/20261028T134111Z-b24d3ef2a623/input.json) | [output](../verified-candidate/B07/20261028T134111Z-b24d3ef2a623/output.json) | [trace](../verified-candidate/B07/20261028T134111Z-b24d3ef2a623/trace.jsonl) |
| B08 | 2 | answered | PASS | 10/3 | [input](../verified-candidate/B08/20261028T134127Z-ee346a0bc7f0/input.json) | [output](../verified-candidate/B08/20261028T134127Z-ee346a0bc7f0/output.json) | [trace](../verified-candidate/B08/20261028T134127Z-ee346a0bc7f0/trace.jsonl) |
| B09 | 2 | answered | PASS | 7/2 | [input](../verified-candidate/B09/20261028T134137Z-d610353527d7/input.json) | [output](../verified-candidate/B09/20261028T134137Z-d610353527d7/output.json) | [trace](../verified-candidate/B09/20261028T134137Z-d610353527d7/trace.jsonl) |
| B11 | 2 | answered | FAIL | 6/2 | [input](../verified-candidate/B11/20261028T134147Z-9d457b3d21fd/input.json) | [output](../verified-candidate/B11/20261028T134147Z-9d457b3d21fd/output.json) | [trace](../verified-candidate/B11/20261028T134147Z-9d457b3d21fd/trace.jsonl) |
| B12 | 2 | answered | PASS | 7/3 | [input](../verified-candidate/B12/20261028T134157Z-faaa6e05ca7f/input.json) | [output](../verified-candidate/B12/20261028T134157Z-faaa6e05ca7f/output.json) | [trace](../verified-candidate/B12/20261028T134157Z-faaa6e05ca7f/trace.jsonl) |
| B15 | 2 | answered | PASS | 8/3 | [input](../verified-candidate/B15/20261028T134205Z-1acb80d3e271/input.json) | [output](../verified-candidate/B15/20261028T134205Z-1acb80d3e271/output.json) | [trace](../verified-candidate/B15/20261028T134205Z-1acb80d3e271/trace.jsonl) |
| B16 | 2 | needs_clarification | PASS | 6/4 | [input](../verified-candidate/B16/20261028T134219Z-718e7c44d8ed/input.json) | [output](../verified-candidate/B16/20261028T134219Z-718e7c44d8ed/output.json) | [trace](../verified-candidate/B16/20261028T134219Z-718e7c44d8ed/trace.jsonl) |
| B17 | 2 | incomplete | FAIL | 10/5 | [input](../verified-candidate/B17/20261028T134232Z-219d3a8ccab6/input.json) | [output](../verified-candidate/B17/20261028T134232Z-219d3a8ccab6/output.json) | [trace](../verified-candidate/B17/20261028T134232Z-219d3a8ccab6/trace.jsonl) |

## Paired comparisons

| Comparison | Left run | Right run | Result |
|---|---|---|---|
| paraphrase | 20261028T133634Z-52e3eb66263c | 20261028T133656Z-d65c230ff125 | PASS |
| replacement | 20261028T133634Z-52e3eb66263c | 20261028T133714Z-184a6c191a77 | PASS |
| conflict | 20261028T133634Z-52e3eb66263c | 20261028T133720Z-f67ee110415e | FAIL |
| conflict_scenario | 20261028T133634Z-52e3eb66263c | 20261028T133640Z-4b2da5066d92 | PASS |
| paraphrase | 20261028T133943Z-14688063edbe | 20261028T134005Z-ba1782acf2aa | PASS |
| replacement | 20261028T133943Z-14688063edbe | 20261028T134027Z-3212459699f1 | PASS |
| conflict | 20261028T133943Z-14688063edbe | 20261028T134034Z-cc3ccb590691 | PASS |
| conflict_scenario | 20261028T133943Z-14688063edbe | 20261028T133949Z-55c7e0c57d0d | PASS |

Every tool argument, observation summary and next model action is indexed in audit.json under runs[].transitions. Artifact hashes are audit-time checksums, not signatures or proof against deliberate forgery.
