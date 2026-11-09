#!/bin/bash
# Development evaluation on the visible training conversations.
#
#   bash scripts/evaluate.sh                                  # run + score every scripts/retrievers/*.sh
#   bash scripts/evaluate.sh --artifacts outputs/x/results.jsonl ...   # score saved outputs
#
# Saved outputs must be produced on data/locomo_train.json with the retriever
# contract: one JSON row per question {"question_id", "retrieved_entry_ids"}
# with at most 10 ranked entry IDs from the question's own conversation.
# Self-contained in eval/ (never imports method/). Writes scoring/scores.json.
set -e
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
mkdir -p scoring
python eval/evaluate_retrieval.py "$@" --output scoring/scores.json
