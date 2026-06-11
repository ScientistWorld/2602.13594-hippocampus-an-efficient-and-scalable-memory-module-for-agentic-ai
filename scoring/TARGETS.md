# Evaluation Targets

## Primary: memory_retrieval_efficiency
Tests whether a long-memory system returns answer-bearing memory entries for natural-language questions.
- **Metric**: `hit_at_1` (higher is better)

## Constraint: memory_retrieval_efficiency
Tests whether retrieval remains efficient instead of solving the task by returning large amounts of memory.
- **Metrics**: `avg_token_footprint` and `avg_bit_operations` (lower is better)
- `avg_search_time_ms` may appear in artifacts as a diagnostic only; it is not a scored target because wall-clock speed depends on hardware.

## Supporting: memory_retrieval_efficiency
Tests whether useful evidence appears anywhere in a small retrieved set and whether the returned text contains answer tokens.
- **Metrics**: `hit_at_3` and `answer_token_f1` (higher is better)

Run `bash scripts/reproduce.sh` to generate method and baseline artifacts, then `bash scripts/evaluate.sh outputs/hippocampus/retrieval_results.jsonl outputs/recency_baseline/retrieval_results.jsonl`.
