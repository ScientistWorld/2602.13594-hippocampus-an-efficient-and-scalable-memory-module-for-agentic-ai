# Evaluation Targets

All targets belong to experiment `locomo_memory_retrieval` (weight 1.0). Scores come from `scripts/evaluate_test.sh` on 6 held-out LoCoMo conversations (659 private questions); `scripts/evaluate_train.sh` gives the same measurement on 4 visible conversations (581 questions).

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
HIPPOCAMPUS: recall@10 26.39, hit@1 9.10, answer-token recall 46.25, worst category 10.49, 507.8 context tokens. Exhaustive BM25 gets 69.05 recall@10 at 349.1 tokens. The most-recent-entries baseline gets 1.13 recall and is scored as failed. Returning the whole history would cost about 20.7K tokens per question.

Not scored: wall-clock latency and operation counts, which cannot be measured method-agnostically without timing.

The final rerun will freeze all five metrics in `reference.json`. Paper-reported answer-quality and latency numbers remain under `_paper_reported`, outside this retrieval scale. This proxy does not establish the paper's full accuracy-and-latency claim; the reference loses to BM25.
