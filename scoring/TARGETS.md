# Evaluation Targets

## Primary: memory_retrieval_efficiency
Tests whether a long-memory system returns answer-bearing memory entries for natural-language questions.
- **Metric**: `hit_at_1` (higher is better)

## Constraint: memory_retrieval_efficiency
Tests whether retrieval remains efficient instead of solving the task by returning large amounts of memory.
- **Metrics**: `avg_token_footprint` and `avg_bit_operations` (lower is better)
- `avg_search_time_ms` may appear in artifacts as a diagnostic only; it is not a scored target because wall-clock speed depends on hardware.

## Supporting: memory_retrieval_efficiency
Tests whether useful evidence appears anywhere in a small retrieved set, whether all labeled supporting entries are recovered, whether returned text contains answer tokens, and whether performance is not concentrated in only one question category.
- **Metrics**: `hit_at_3`, `gold_entry_recall`, `answer_token_f1`, and `worst_category_hit_at_1` (higher is better)

## Benchmark Limitation
This portable benchmark is intentionally small and API-free. It validates selective long-memory retrieval and efficiency constraints, but it is easier than the paper's full LoCoMo/LongMemEval setup; surface lexical matching is a known strong sanity baseline on this synthetic data.

Run `bash scripts/reproduce.sh` to generate method and baseline artifacts, then `bash scripts/evaluate.sh outputs/hippocampus/retrieval_results.jsonl outputs/recency_baseline/retrieval_results.jsonl`.
