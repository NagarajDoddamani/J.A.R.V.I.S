#!/usr/bin/env bash
# Live Ollama model verification (Phase 01, FND-011).
#
# Exercises the four required offline checks against a real Ollama
# daemon running on the loopback interface:
#
#   1. Model presence + identity
#   2. Deterministic smoke inference per model
#   3. Offline behaviour with no outbound network
#   4. Cold-restart behaviour (the daemon has no internet, so a
#      restart must not attempt to download anything)
#
# This script is the operator-facing wrapper. CI calls it after the
# daemon is up.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

cd "${REPO_ROOT}"

# Make the in-process packages importable.
export PYTHONPATH="${REPO_ROOT}:${PYTHONPATH:-}"

OLLAMA_URL="${OLLAMA_URL:-http://127.0.0.1:11434}"
OUT_DIR="${OUT_DIR:-build/verification}"
mkdir -p "${OUT_DIR}"

# 1. Manifest inspection (no daemon required)
echo "--- Manifest inspection ---"
python -m tools.model_verification.manifest || true

# 2. Live verification
echo "--- Live verification ---"
JARVIS_VERIFY_REPORT="${OUT_DIR}/verification_report.json" \
    OLLAMA_BASE_URL="${OLLAMA_URL}" \
    python -m tools.model_verification.verify_models

# 3. Offline mode (re-run with JARVIS_VERIFY_OFFLINE=1)
echo "--- Offline verification ---"
JARVIS_VERIFY_OFFLINE=1 \
    JARVIS_VERIFY_REPORT="${OUT_DIR}/verification_report_offline.json" \
    OLLAMA_BASE_URL="${OLLAMA_URL}" \
    python -m tools.model_verification.verify_models

echo
echo "Reports written to ${OUT_DIR}/"
