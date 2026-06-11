#!/bin/bash
# Run a baseline method from the paper.
#
# Baselines are simple reference methods the paper compares against. 
# Implement this only if applicable, i.e. the paper has baselines.
# You do not need to implement all baselines to begin — 
# just enough to validate that the evaluation pipeline works 
# and provide a reference point. You can decide to expand more baselines later.
# Each baseline must be actually run and scored through evaluate.sh
# so the numbers are verified, not self-reported.
# You can decide what this baseline script should do yourself.
#
# Usage:
#   bash scripts/baseline.sh

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p outputs
python baseline/lexical_retriever.py \
  --data data/memory_qa.json \
  --output-dir outputs/lexical_baseline \
  --top-k 3

python baseline/recency_retriever.py \
  --data data/memory_qa.json \
  --output-dir outputs/recency_baseline \
  --top-k 3

bash scripts/evaluate.sh outputs/recency_baseline/retrieval_results.jsonl
