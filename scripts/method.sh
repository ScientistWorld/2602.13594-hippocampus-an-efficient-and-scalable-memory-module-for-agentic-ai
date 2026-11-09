#!/bin/bash
# Run the paper's method (HIPPOCAMPUS) on the visible training conversations.
set -e
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
mkdir -p outputs/hippocampus
python method/wavelet_selftest.py
bash scripts/retrievers/hippocampus.sh data/locomo_train.json outputs/hippocampus/retrieval_results.jsonl
bash scripts/evaluate.sh --artifacts outputs/hippocampus/retrieval_results.jsonl
