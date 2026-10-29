# Qwen real-run evidence

All runs, including failures and configuration differences: [review-index.json](review-index.json).

These are representative observed behaviors, not a stable pass-rate claim. Candidate review is still required.

| Case | Thinking | Status | Input | Output | Trace |
|---|---|---|---|---|---|
| A01 | True | answered | [input.json](final/A01/20261028T093754Z-782bf7566e70/input.json) | [output.json](final/A01/20261028T093754Z-782bf7566e70/output.json) | [trace.jsonl](final/A01/20261028T093754Z-782bf7566e70/trace.jsonl) |
| A02 | True | needs_clarification | [input.json](corrected-conflict/A02/20261028T094214Z-4981ef906ebc/input.json) | [output.json](corrected-conflict/A02/20261028T094214Z-4981ef906ebc/output.json) | [trace.jsonl](corrected-conflict/A02/20261028T094214Z-4981ef906ebc/trace.jsonl) |
| A03 | True | unanswerable | [input.json](final/A03/20261028T093908Z-f90f662b31b8/input.json) | [output.json](final/A03/20261028T093908Z-f90f662b31b8/output.json) | [trace.jsonl](final/A03/20261028T093908Z-f90f662b31b8/trace.jsonl) |
| A04 | True | answered | [input.json](final/A04/20261028T093923Z-fd7f67861d28/input.json) | [output.json](final/A04/20261028T093923Z-fd7f67861d28/output.json) | [trace.jsonl](final/A04/20261028T093923Z-fd7f67861d28/trace.jsonl) |
| A05 | False | answered | [input.json](nonthinking-comparison/A05/20261028T094750Z-7a5a32b9523a/input.json) | [output.json](nonthinking-comparison/A05/20261028T094750Z-7a5a32b9523a/output.json) | [trace.jsonl](nonthinking-comparison/A05/20261028T094750Z-7a5a32b9523a/trace.jsonl) |
| A06 | True | incomplete | [input.json](revised/A06/20261028T093535Z-8085bf41ce81/input.json) | [output.json](revised/A06/20261028T093535Z-8085bf41ce81/output.json) | [trace.jsonl](revised/A06/20261028T093535Z-8085bf41ce81/trace.jsonl) |
| B01 | True | answered | [input.json](final/B01/20261028T094038Z-c844610e1822/input.json) | [output.json](final/B01/20261028T094038Z-c844610e1822/output.json) | [trace.jsonl](final/B01/20261028T094038Z-c844610e1822/trace.jsonl) |
| B03 | False | answered | [input.json](nonthinking-comparison/B03/20261028T094754Z-37d8b620a012/input.json) | [output.json](nonthinking-comparison/B03/20261028T094754Z-37d8b620a012/output.json) | [trace.jsonl](nonthinking-comparison/B03/20261028T094754Z-37d8b620a012/trace.jsonl) |

## Batch results

Counts below reflect only automatic status/document-ID checks, not complete semantic acceptance.

| Summary | Runs | Automatic checks passed |
|---|---:|---:|
| [../evaluation-results.json](../evaluation-results.json) | 15 | 10 |
| [acceptance/evaluation-results.json](acceptance/evaluation-results.json) | 13 | 9 |
| [context-and-replacement/evaluation-results.json](context-and-replacement/evaluation-results.json) | 2 | 1 |
| [corrected-conflict/evaluation-results.json](corrected-conflict/evaluation-results.json) | 1 | 1 |
| [final/evaluation-results.json](final/evaluation-results.json) | 9 | 8 |
| [nonthinking-comparison/evaluation-results.json](nonthinking-comparison/evaluation-results.json) | 2 | 2 |
| [protocol-repair/evaluation-results.json](protocol-repair/evaluation-results.json) | 3 | 0 |
| [revised/evaluation-results.json](revised/evaluation-results.json) | 2 | 2 |

## Other evidence

- [Local tests](test-results.txt)
- [Retrieval before/after](retrieval-comparison.json)

Reasoning content and local credentials are excluded from saved traces.
