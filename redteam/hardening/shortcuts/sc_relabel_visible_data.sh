#!/bin/bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../../.."
python redteam/hardening/shortcuts.py relabel_visible_data "$1" "$2"
