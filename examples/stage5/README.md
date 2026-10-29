# Stage 5 evaluation evidence

Final frozen batch: **verified-candidate**. **30/36** finite checks pass; core A01-A06: **12/12 finite checks**, not full semantic acceptance. **104 local tests** and **9/9 controlled boundary checks** pass. One engine revision and one public model configuration.

The project has **not passed every acceptance check**. AI reading found issues in five runs, including four that passed finite checks. A02 round 2 still asks for time to choose between policies without a temporal precedence rule; B07 round 1 asks for the wrong missing information. Do not report the core finite score as complete semantic correctness.

- [Detailed Chinese report](../../docs/11-effect-evaluation.md)
- [Structured summary](summary.json)
- [All final inputs, outputs and traces](final-audit/README.md)
- [Full saved-evidence audit](final-audit/audit.json)
- [AI answer review](ai-review.json) (not candidate independent review)
- [Selected model paths, including a failed run](paths.md)
- [Local test report](test-results.txt)
- [Controlled boundary experiments](guard-boundaries/boundary-results.json) (Mock, not model reasoning)
- [Source hashes](source-manifest.json)
- [Final documentation, source and secret-value checks](final-inspection.json)

## Final results

| Case | Finite passes | Actual outcomes |
|---|---|---|
| A01 | 2/2 | {"answered": 2} |
| A02 | 2/2 | {"needs_clarification": 2} |
| A03 | 2/2 | {"unanswerable": 2} |
| A04 | 2/2 | {"answered": 2} |
| A05 | 2/2 | {"answered": 2} |
| A06 | 2/2 | {"incomplete": 2} |
| B01 | 2/2 | {"answered": 2} |
| B02 | 1/2 | {"incomplete": 1, "needs_clarification": 1} |
| B03 | 1/2 | {"answered": 1, "incomplete": 1} |
| B04 | 2/2 | {"needs_clarification": 2} |
| B07 | 1/2 | {"needs_clarification": 1, "incomplete": 1} |
| B08 | 2/2 | {"answered": 2} |
| B09 | 2/2 | {"answered": 2} |
| B11 | 1/2 | {"needs_clarification": 1, "answered": 1} |
| B12 | 2/2 | {"answered": 2} |
| B15 | 2/2 | {"answered": 2} |
| B16 | 1/2 | {"incomplete": 1, "needs_clarification": 1} |
| B17 | 1/2 | {"needs_clarification": 1, "incomplete": 1} |

B08 recovered and answered in both final samples; this is not a general recovery guarantee. B02, B03, B07, B11, B16 and B17 each have one failed finite check run. All failures are retained. B11 round 2 guessed the topic. Additional semantic/attribution issues are listed in ai-review.json.

## Development batches

Each row retains all completed runs. Different code versions and prompted checks are not pooled into a success rate. Older batches named final-regression or frozen-regression were superseded; only verified-candidate is the current frozen cohort.

| Batch | Completed | Finite passes |
|---|---|---|
| [action-loop-pilot](action-loop-pilot/evaluation-results.json) | 6 | 5 |
| [boundary-real](boundary-real/evaluation-results.json) | 8 | 0 |
| [conflict-guard-pilot](conflict-guard-pilot/evaluation-results.json) | 4 | 3 |
| [context-review-fix](context-review-fix/evaluation-results.json) | 4 | 3 |
| [final-regression](final-regression/evaluation-results.json) | 36 | 29 |
| [fix-pilot](fix-pilot/evaluation-results.json) | 5 | 2 |
| [frozen-regression](frozen-regression/evaluation-results.json) | 36 | 30 |
| [premature-clarification-fix](premature-clarification-fix/evaluation-results.json) | 2 | 0 |
| [verified-candidate](verified-candidate/evaluation-results.json) | 36 | 30 |

The baseline-audit directory preserves the first audit-tool attempt: it wrongly treated differently phrased A01/A02 as an identical-input experiment. The baseline-recheck corrected that classification. B02 was added for a real identical-input conflict comparison. Historical baseline checks used their then-current validators, not the final stronger numeric-risk rule.

## Reproduce

```text
python -m src.kb_agent.evaluate --mode real --thinking-mode off --cases A01 A02 A03 A04 A05 A06 B01 B02 B03 B04 B07 B08 B09 B11 B12 B15 B16 B17 --repeat 2 --output-dir examples/my-stage5-real
python scripts/audit_evidence.py --report examples/stage5/verified-candidate/evaluation-results.json --require-cases A01 A02 A03 A04 A05 A06 B01 B02 B03 B04 B07 B08 B09 B11 B12 B15 B16 B17 --output-dir examples/my-stage5-audit
python scripts/run_boundary_checks.py --output-dir examples/my-stage5-boundaries
```

The real command makes provider calls. Audit is offline, reuses business validators, and independently checks trace links and tool-result replay. Audit exits 1 for this saved cohort because failures remain; that exit is expected and is not a broken command. Use a new output directory. Original evidence is never rewritten.
