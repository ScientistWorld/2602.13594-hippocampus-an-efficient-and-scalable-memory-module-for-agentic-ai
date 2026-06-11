# Progress

## What Works

- Implemented HIPPOCAMPUS core mechanics: content token-ID stream, signature stream, Dynamic Wavelet Matrix `access/rank/select`, sparse random indexing, Hamming-ball retrieval, metadata span validation, and exact content reconstruction.
- Added a deterministic long-memory QA benchmark in `data/memory_qa.json`.
- Added recency and lexical baselines plus a reusable evaluator that reads method artifacts from `outputs/`. The default scored baseline is recency-based to keep the synthetic benchmark non-trivial.
- Wired `scripts/reproduce.sh` to run data setup, baseline, method, and evaluation.

## Results

The completed CPU job showed the full pipeline runs and originally produced HIPPOCAMPUS at 58.33% `hit_at_1` and 88.89% `hit_at_3`. Inspecting the artifacts showed cross-conversation retrieval, so the method and baselines now constrain search to the labeled conversation history.

After that fix, `bash scripts/reproduce.sh && python validate.py --compare` passes locally. Corrected scores are:

- `hippocampus`: 93.06% `hit_at_1`, 97.22% `hit_at_3`, 61.50 retrieved tokens/query, 125.73 ms diagnostic search time/query, and 5,249.74 bit operations/query.
- `recency_baseline`: 0.00% `hit_at_1`, 0.00% `hit_at_3`, 39.00 retrieved tokens/query, 0.02 ms diagnostic search time/query, and 45.00 bit operations/query.

This supports the core claim on the portable delayed-recall benchmark: the paper's DWM plus sparse random-indexing memory retrieves old relevant facts under a small token footprint, while a lightweight recency memory fails.

## Remaining

- Run the corrected packaged reproduction through the scheduler.
- If budget allows after scheduler confirmation, add one extra setting such as a signature-bit/radius ablation or a larger generated memory stream.

## Issues

- No public upstream HIPPOCAMPUS code release was found. The implementation is from scratch using the paper's algorithms.
- The original LoCoMo and LongMemEval end-to-end LLM judging setup is not bundled here, so the gym uses a deterministic retrieval-focused benchmark.

## Deviations from Paper

- The paper evaluates LoCoMo and LongMemEval with LLM answer generation and LLM-as-a-judge. This workspace uses a deterministic LoCoMo-like QA retrieval benchmark because it is portable, API-free, and keeps evaluation focused on the memory substrate.
- The paper reports wall-clock latency on fixed HPE hardware. This workspace records search time for diagnostics but uses bit-operation count and token footprint as hardware-independent constraint metrics.
