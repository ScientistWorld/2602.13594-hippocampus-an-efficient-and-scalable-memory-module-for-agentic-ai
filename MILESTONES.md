# Reproduction Milestones

**Current: core_claim**

## Progress Log

### [2026-06-11 20:35] - none
- Read the paper and identified the core method: dual Dynamic Wavelet Matrices, sparse random indexing, Hamming-ball search, metadata validation, and exact token reconstruction.
- Confirmed by web search that no public implementation was available.

### [2026-06-11 21:10] - method_runs
- Implemented the paper's actual memory algorithm in `method/hippocampus.py`.
- Verified DWM `access`, `rank`, and `select` on a small sequence.
- Ran local smoke tests showing the method executes end-to-end on the generated memory QA benchmark.

### [2026-06-11 20:02] - core_claim
- Reviewed the completed scheduler job and fixed retrieval scope so questions only search their own conversation history.
- Re-ran the packaged reproduction locally with conversation-scoped HIPPOCAMPUS retrieval and a recency baseline.
- HIPPOCAMPUS reached 93.06% hit@1 and 97.22% hit@3 with 61.50 retrieved tokens/query, while the recency baseline reached 0.00% hit@1/hit@3 on the same delayed-recall benchmark.

## Stop Justification
- Not stopped. A scheduler job is being submitted to confirm the corrected packaged reproduction.
