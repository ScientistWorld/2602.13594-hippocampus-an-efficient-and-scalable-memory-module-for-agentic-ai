#!/bin/bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../../.."
python redteam/hardening/better_rerank.py --input "$1" --output "$2"
