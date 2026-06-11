# Reproduction Milestones

**Current: core_claim_plus**

## Progress Log

### [2026-06-11 20:07] - core_claim
- Scheduler-confirmed `bash scripts/run.sh` completed successfully on a CPU compute node.
- HIPPOCAMPUS retrieved answer-bearing memory entries on the portable long-memory QA benchmark while keeping returned context small and using binary-signature search work.

### [2026-06-11 20:13] - core_claim_plus
- Added and ran a compact-signature HIPPOCAMPUS setting through `scripts/ablation.sh`.
- Preserved the standard gym score as HIPPOCAMPUS versus recency baseline, with the compact setting written separately to `tmp/ablation_scores.json`.

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

## Stop Justification
- Completed at milestone `core_claim_plus`: the real HIPPOCAMPUS memory substrate runs end-to-end in-container, beats the recency baseline on the portable retrieval benchmark, preserves token/search-efficiency constraints, and includes one additional compact-signature setting. Higher milestones would require the paper's broader LLM-answering benchmark surface.
