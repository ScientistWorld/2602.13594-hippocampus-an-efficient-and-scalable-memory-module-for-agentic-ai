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

## Stop Justification
- Completed at milestone `core_claim_plus`.
