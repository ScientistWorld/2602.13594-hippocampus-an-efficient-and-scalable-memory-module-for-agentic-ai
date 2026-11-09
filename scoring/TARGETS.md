# Evaluation Targets

All targets belong to experiment `locomo_memory_retrieval` (weight 1.0). Scores come from `scripts/evaluate_test.sh` on 6 held-out LoCoMo conversations (955 questions); `scripts/evaluate_train.sh` gives the same measurement on 4 visible conversations (581 questions).

## Primary
- `evidence_recall_at_10` (higher is better, coefficient 1.0): average fraction of labelled evidence turns among the at most 10 returned entries.

## Supporting quality
- `evidence_hit_at_1` (higher, 0.4): the top-ranked entry is evidence.
- `answer_token_recall` (higher, 0.4): the gold answer's content words appear in the delivered context.
- `worst_category_recall` (higher, 0.3): lowest evidence recall over single-hop, multi-hop, temporal and open-domain questions.

## Constraint (efficiency)
- `avg_context_tokens` (lower, coefficient magnitude 0.2): delivered context tokens per question (per-query token footprint).
- Hard budget: at most 10 entries per question. Over-budget, malformed, or near-zero-recall runs (below 5% evidence recall) are scored as failed.

## Reference (hidden test, seed 13)
HIPPOCAMPUS: recall@10 24.42, hit@1 9.32, answer-token recall 39.60, worst category 12.71, 491.1 context tokens. Exhaustive BM25 gets 55.97 recall@10 at 332.4 tokens. The most-recent-entries baseline gets 1.05 recall and is scored as failed. Returning the whole history would cost about 20.7K tokens per question.

Not scored: wall-clock latency and operation counts, which cannot be measured method-agnostically without timing.
