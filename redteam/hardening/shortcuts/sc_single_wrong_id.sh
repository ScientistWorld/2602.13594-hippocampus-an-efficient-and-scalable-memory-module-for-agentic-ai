#!/bin/bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../../.."
python redteam/hardening/shortcuts.py single_wrong_id "$1" "$2"
