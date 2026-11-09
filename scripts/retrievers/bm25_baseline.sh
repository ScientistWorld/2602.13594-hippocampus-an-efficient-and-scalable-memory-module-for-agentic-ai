#!/bin/bash
# Retriever: exhaustive BM25 over the raw text of every entry (brute-force lexical check).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
python baseline/lexical_retriever.py --input "$1" --output "$2" --top-k 10
