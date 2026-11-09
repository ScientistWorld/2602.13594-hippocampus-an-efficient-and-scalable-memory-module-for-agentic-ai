#!/bin/bash
# Run the baselines (most-recent entries, exhaustive BM25) on the training conversations.
set -e
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
mkdir -p outputs/recency_baseline outputs/bm25_baseline
bash scripts/retrievers/recency_baseline.sh data/locomo_train.json outputs/recency_baseline/retrieval_results.jsonl
bash scripts/retrievers/bm25_baseline.sh data/locomo_train.json outputs/bm25_baseline/retrieval_results.jsonl
bash scripts/evaluate.sh --artifacts outputs/recency_baseline/retrieval_results.jsonl outputs/bm25_baseline/retrieval_results.jsonl
