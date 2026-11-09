#!/bin/bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../../.."
python method/hippocampus.py --input "$1" --output "$2" --dimension 512 --signature-bits 32 --radius 8 --window 1 --query-window 0 --seed 14 --top-k 10
