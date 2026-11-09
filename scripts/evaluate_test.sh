#!/bin/bash
# Hidden-test evaluation.
#
#   bash scripts/evaluate_test.sh                 # every retriever in scripts/retrievers/
#   bash scripts/evaluate_test.sh path/to/x.sh    # explicit retriever scripts
#
# Each retriever is RUN on held-out LoCoMo conversations that exist only in
# eval/test/ (label-free input, sandboxed workspace view); its returned entry
# IDs are scored against hidden evidence labels. Writes scoring/scores_test.json.
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
mkdir -p scoring
python eval/test/evaluate_retrieval.py "$@" --output scoring/scores_test.json
