# Evaluation

Run `bash scripts/evaluate.sh <artifact.jsonl> ...` to score one or more retrieval artifacts. Each artifact row must include a question id, answer, `gold_entry_ids`, a method name, and a ranked `retrieved` list of memory entries.

The primary metric is `hit_at_1`, the percentage of questions whose top retrieved entry is one of the labeled answer-bearing entries. Supporting quality metrics are `hit_at_3` and answer-token F1 over the retrieved text.

Constraint metrics measure the paper's efficiency claim: average retrieved-token footprint, average search time, machine-independent bit-operation count, and approximate storage size. Search time is reported for diagnostics only; `avg_bit_operations` is the preferred hardware-independent efficiency metric.
