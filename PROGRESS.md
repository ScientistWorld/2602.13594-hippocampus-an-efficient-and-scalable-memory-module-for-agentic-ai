# Progress

## What Works

- Implemented HIPPOCAMPUS core mechanics: content token-ID stream, signature stream, Dynamic Wavelet Matrix `access/rank/select`, sparse random indexing, Hamming-ball retrieval, metadata span validation, and exact content reconstruction.
- Added a deterministic long-memory QA benchmark in `data/memory_qa.json`.
- Added a lexical baseline and reusable evaluator that reads method artifacts from `outputs/`.
- Wired `scripts/reproduce.sh` to run data setup, baseline, method, and evaluation.

## Results

Local smoke tests on the full generated benchmark showed HIPPOCAMPUS reaches roughly 58-64% `hit_at_1` and 85-90% `hit_at_3` depending on Hamming radius, with about 64 retrieved tokens per query. The submitted CPU job will write the authoritative `scoring/scores.json`.

## Remaining

- Run the packaged reproduction through the scheduler.
- If the job succeeds, compare `scoring/scores.json` against `scoring/reference.json` and update the milestone to `core_claim` if the same effect holds.

## Issues

- No public upstream HIPPOCAMPUS code release was found. The implementation is from scratch using the paper's algorithms.
- The original LoCoMo and LongMemEval end-to-end LLM judging setup is not bundled here, so the gym uses a deterministic retrieval-focused benchmark.

## Deviations from Paper

- The paper evaluates LoCoMo and LongMemEval with LLM answer generation and LLM-as-a-judge. This workspace uses a deterministic LoCoMo-like QA retrieval benchmark because it is portable, API-free, and keeps evaluation focused on the memory substrate.
- The paper reports wall-clock latency on fixed HPE hardware. This workspace records search time for diagnostics but uses bit-operation count and token footprint as hardware-independent constraint metrics.
