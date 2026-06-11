#!/bin/bash
# Run the paper's proposed method.
#
# This script trains/runs the paper's method using code in method/.
#
# Usage:
#   bash scripts/method.sh

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p outputs
python method/hippocampus.py \
  --data data/memory_qa.json \
  --output-dir outputs/hippocampus \
  --dimension 512 \
  --signature-bits 32 \
  --radius 7 \
  --window 2 \
  --top-k 3

bash scripts/evaluate.sh outputs/hippocampus/retrieval_results.jsonl
