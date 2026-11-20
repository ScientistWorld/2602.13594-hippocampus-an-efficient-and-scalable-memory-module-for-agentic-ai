# Reproduction Milestones

**Current: none**

## Progress Log

### [2026-06-11 20:07] - core_claim
- Scheduler-confirmed `bash scripts/run.sh` completed successfully on a CPU compute node.
- HIPPOCAMPUS retrieved answer-bearing memory entries on the portable long-memory QA benchmark while keeping returned context small and using binary-signature search work.

### [2026-06-11 20:13] - core_claim_plus
- Added and ran a compact-signature HIPPOCAMPUS setting through `scripts/ablation.sh`.
- Preserved the standard gym score as HIPPOCAMPUS versus recency baseline, with the compact setting written separately to `scoring/ablation_scores.json`.

### [2026-06-11 20:31] - core_claim_plus
- Replaced lazy static DWM materialization with append-time level insertion and a reusable DWM primitive self-test.
- Hardened evaluation to reload gold labels from `data/memory_qa.json` and recompute token footprint from returned text.
- Removed content-token lexical reranking from HIPPOCAMPUS retrieval; candidate span validation now uses Signature-DWM rank checks.
- Local `scripts/reproduce.sh`, `python validate.py --compare`, and compact-signature ablation all pass after the integrity fixes.

### [2026-06-11 20:35] - core_claim_plus
- CPU validation job `3ddccb10-194` failed before reproduction because the DWM self-test was run as a file under a clean container environment, leaving the repository root off `sys.path`.
- Patched `method/wavelet_selftest.py` to add the repository root explicitly before importing `method.hippocampus`; the same entrypoint now passes under a clean local environment.

### [2026-06-11 20:38] - core_claim_plus
- Scheduler-confirmed CPU validation job `d64d2a90-2ab` completed successfully in the clean container.
- The job ran the DWM self-test, standard HIPPOCAMPUS reproduction, `python validate.py --compare`, and compact-signature ablation without errors.
- Confirmed standard reproduced scores: HIPPOCAMPUS 43.06% `hit_at_1`, 62.50% `hit_at_3`, 62.68 retrieved tokens/query, and 7,640.38 bit operations/query.
- Confirmed compact-signature setting: 50.00% `hit_at_1`, 73.61% `hit_at_3`, 63.76 retrieved tokens/query, and 7,640.38 bit operations/query.

### [2026-06-11 21:00] - core_claim_plus
- Hardened the main reusable evaluator to enforce top-3 retrieval, known entry IDs, no duplicate retrieved entries, and per-conversation memory boundaries.
- Added reproduced `gold_entry_recall` and `worst_category_hit_at_1` to `scoring/scores.json`, matching the declared metrics in `scoring/reference.json`.
- Local `bash scripts/reproduce.sh`, `python method/wavelet_selftest.py`, and `python validate.py --compare` pass after the evaluator update.

### [2026-06-11 21:10] - core_claim_plus
- Final verification confirmed the workspace validates, train/test scoring is wired correctly, and the method/problem separation is clean.
- Documented the benchmark limitation: the portable synthetic dataset validates the memory-substrate claim but remains easier than LoCoMo/LongMemEval and is vulnerable to lexical matching.
- Refreshed the optional compact-signature ablation score with the current evaluator schema and removed the stale wall-clock metric from the tracked ablation artifact.

### [2026-06-11 21:12] - core_claim_plus
- Final verifier fixed train/test scoring so arbitrary future method names are evaluated instead of filtered to `reference.json` methods.
- Updated `scripts/run.sh` to pass official artifacts explicitly, avoiding stale ignored output files in split scores.
- Reran `bash scripts/run.sh`; validation passed with the current core-claim scores.

### [2026-11-09 07:20] - core_claim_plus (iteration 11, hardening)
- Moved the gym to the paper's LoCoMo benchmark: 4 visible training conversations (581 questions) and 6 held-out test conversations (955 questions), with test labels only in `eval/test/`.
- The hidden test runs every `scripts/retrievers/*.sh` on label-free held-out inputs and scores only the returned entry IDs. Failure gates: 10-entry budget and a 5% recall floor.
- HIPPOCAMPUS reference (fidelity fixes: dense Gaussian hyperplanes per Appendix G, keyword co-occurrence ranking, per-conversation DWMs): hidden-test recall@10 24.42 (train 23.80) at 491 context tokens.
- Comparisons: recency 1.05 (failed); full history about 20.7K tokens; exhaustive BM25 55.97. Seed range 1.84 recall points.
- Signature-length ablation: 16-bit 10.87, 1-bit fails the floor. A better variant (BM25 re-ranking of signature candidates) reaches 36.95. Details in `HARDENING.md`.

### [2026-11-20] - none (final integrity correction)
- Job `370ea91b-ced` passed: final reference/baselines, private-question checks, sequential paired variant/shortcut audit and validation.
- Stored private reference recall@10 is 26.39; better reranking 38.34; weaker 16-bit 10.96; seed range 1.58 points. Required isolation and complete failure scores are verified.
- Withdrew the earlier `core_claim_plus` assessment. The implementation omits the paper's LLM keyword extraction and uses its Appendix G hashing formulation instead of Section 3.3's construction. Under the strict reproduction-integrity rule, a higher milestone is not justified.
- BM25 still outranks the reference (69.05 versus 26.39), and embedded public-label priors remain profitable. The full scientific hardening goal is not achieved; `HARDENING.md` records these failures.

## Stop Justification
- Packaged the completed final audit at milestone `none`, with unresolved requirements explicitly recorded. No claim of a full scientific reproduction is made.
