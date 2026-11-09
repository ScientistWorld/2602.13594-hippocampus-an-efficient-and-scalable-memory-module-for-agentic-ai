#!/bin/bash
# Retriever: most-recent-entries baseline (no semantic index).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
python baseline/recency_retriever.py --input "$1" --output "$2" --top-k 10
