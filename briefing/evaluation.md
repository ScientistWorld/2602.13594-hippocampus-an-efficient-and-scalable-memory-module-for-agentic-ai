# Evaluation

## Interface
Every method is a retriever script in `scripts/retrievers/<name>.sh`:

    bash scripts/retrievers/<name>.sh <memory_input.json> <results.jsonl>

The input JSON has `conversations` (each with `conversation_id` and `entries`; each entry has `entry_id`, `session`, `turn`, `date_time`, `speaker`, `text`) and label-free `questions` (`question_id`, `conversation_id`, `question`). Write one JSON row per question:

    {"question_id": "...", "retrieved_entry_ids": ["<best entry id>", "..."]}

Other fields in the row are ignored. At most 10 IDs are allowed, with no duplicates, and all from the question's own conversation. The evaluator runs the script itself, from a copy of the workspace, with a fresh input file. The script must not need internet.

## Commands
- `bash scripts/evaluate_train.sh` runs every registered retriever on the visible training conversations and writes `scoring/scores_train.json`.
- `bash scripts/evaluate.sh` does the same and writes `scoring/scores.json`. `bash scripts/evaluate.sh --artifacts <file.jsonl> ...` scores saved outputs produced on `data/locomo_train.json`.
- `bash scripts/evaluate_test.sh` (hidden) runs every registered retriever on held-out conversations with the same protocol and writes `scoring/scores_test.json`.

## Metrics (experiment `locomo_memory_retrieval`)
The evaluator computes every number from the returned entry IDs and its own copy of the corpus and labels. Each entry's delivered context is `[session timestamp] speaker: text`.
- `evidence_recall_at_10` (primary, higher is better): average fraction of a question's evidence turns among the returned entries.
- `evidence_hit_at_1`: the top-ranked entry is an evidence turn.
- `answer_token_recall`: fraction of the gold answer's content words present in the delivered context.
- `worst_category_recall`: lowest evidence recall over the four question groups.
- `avg_context_tokens` (lower is better): word tokens of delivered context per question.

## Failure rules
A run that crashes, misses or duplicates a question, returns more than 10 entries, or returns unknown or cross-conversation IDs is scored as failed. A run whose `evidence_recall_at_10` is below 5% is also failed (random entries give about 1.7%). A failed run gets 0 on every quality metric and the largest context the budget allows. Its reason is recorded under `_status`.

Wall-clock latency and self-reported operation counts are not scored, because they cannot be measured independently of hardware and code.
