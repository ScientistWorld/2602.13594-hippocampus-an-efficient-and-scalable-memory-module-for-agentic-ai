#!/bin/bash
# Fetch every external artifact this environment needs (idempotent).
#
# Estimated download size: 3 MB (LoCoMo locomo10.json); disk after setup: ~3 MB.
#
# Source: LoCoMo (Maharana et al., 2024), the long-conversation memory
# benchmark used by the paper, pinned to a fixed commit and checksum.
# Only the four TRAIN conversations are extracted into data/locomo_train.json;
# the raw download is deleted afterwards so held-out conversations never sit
# in data/. The hidden test split (held-out conversation text + the private
# question set in eval/test/private_questions.json) is built only by
# eval/test/prepare_test_split.py.
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
mkdir -p data/downloads

LOCOMO_URL="https://raw.githubusercontent.com/snap-research/locomo/cbfbc1dba6bc53d00625212a0f22d55ffee7c1fc/data/locomo10.json"
LOCOMO_SHA256="79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4"

if [ ! -f data/locomo_train.json ]; then
  TMP_DIR="$(mktemp -d)"
  trap 'rm -rf "$TMP_DIR"' EXIT
  curl -fsSL "$LOCOMO_URL" -o "$TMP_DIR/locomo10.json"
  echo "$LOCOMO_SHA256  $TMP_DIR/locomo10.json" | sha256sum -c -
  python data/prepare_locomo.py --source "$TMP_DIR/locomo10.json" --output data/locomo_train.json
fi

# Hidden evaluator only (absent from scientist workspaces).
if [ -f eval/test/prepare_test_split.py ] && [ ! -f eval/test/locomo_test.json ]; then
  python eval/test/prepare_test_split.py
fi
