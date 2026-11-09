#!/bin/bash
# Train-split evaluation (same protocol as the hidden test).
#
#   bash scripts/evaluate_train.sh                # every retriever in scripts/retrievers/
#   bash scripts/evaluate_train.sh path/to/x.sh   # explicit retriever scripts
#
# Runs each retriever on the visible conversations in data/locomo_train.json
# and writes scoring/scores_train.json.
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
mkdir -p scoring
python eval/train/evaluate_retrieval.py "$@" --output scoring/scores_train.json
