# Reproduction Milestones

**Current: core_claim_plus**

## Progress Log

### [2026-06-11 20:07] - core_claim
- Scheduler-confirmed `bash scripts/run.sh` completed successfully on a CPU compute node.
- HIPPOCAMPUS retrieved answer-bearing memory entries on the portable long-memory QA benchmark while keeping returned context small and using binary-signature search work.

### [2026-06-11 20:13] - core_claim_plus
- Added and ran a compact-signature HIPPOCAMPUS setting through `scripts/ablation.sh`.
- Preserved the standard gym score as HIPPOCAMPUS versus recency baseline, with the compact setting written separately to `tmp/ablation_scores.json`.

### [2026-06-11 20:18] - core_claim_plus
- Continuation audit verified the implementation is the paper's actual memory-substrate algorithm, not a surrogate.
- CPU compute job `1bd28256-326` completed `scripts/run.sh` successfully, including scoring validation and compact-signature ablation.

## Stop Justification
- Completed at milestone `core_claim_plus`.
