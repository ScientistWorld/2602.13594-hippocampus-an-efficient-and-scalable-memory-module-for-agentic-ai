#!/bin/bash
# Reproduce the paper's results end-to-end.
#
# This script runs inside the compute container and should call
# scripts/baseline.sh and scripts/method.sh to run baselines and
# the paper's method, each of which calls scripts/evaluate.sh.
#
# Assumes:
#   - Container is built (environment/container.sif)
#   - Data and models are downloaded (via scripts/download.sh)
#   - Working directory is the repository root
#
# This is the "gold standard" reproduction — 
# You do not need to run this, but keep this in good shape
# so other agents can easily run a full loop of reproduction and get the paper's numbers.

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

bash scripts/download.sh

mkdir -p outputs
python baseline/recency_retriever.py \
  --data data/memory_qa.json \
  --output-dir outputs/recency_baseline \
  --top-k 3
python method/hippocampus.py \
  --data data/memory_qa.json \
  --output-dir outputs/hippocampus \
  --dimension 512 \
  --signature-bits 32 \
  --radius 7 \
  --window 2 \
  --top-k 3

bash scripts/evaluate.sh \
  outputs/hippocampus/retrieval_results.jsonl \
  outputs/recency_baseline/retrieval_results.jsonl
