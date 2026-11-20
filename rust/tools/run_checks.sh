#!/usr/bin/env bash
# Run every check that compares the Rust port with the ORIGINAL Python code.
#
#   PYTHON=/path/to/python rust/tools/run_checks.sh
#
# The Python must have the original app's dependencies installed:
#   pip install fastapi "uvicorn[standard]" nltk scikit-learn SQLAlchemy bcrypt PyJWT python-dotenv \
#               httpx requests pyyaml pandas numpy joblib email-validator
# and NLTK's Punkt data must be present (`rhcp-chatbot setup-nltk` installs it).
# Run from anywhere; it works from the repository root.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PY="${PYTHON:-python3}"
BIN="$ROOT/rust/target/release"
cd "$ROOT"
failed=()

step() { # step "name" command...
  local name="$1"; shift
  echo; echo "================ $name"
  if "$@"; then echo "---- $name: OK"; else echo "---- $name: FAILED"; failed+=("$name"); fi
}

echo "building (release)..."
(cd rust && cargo build --release --quiet && cargo build --release --quiet --examples) || { echo "build failed"; exit 2; }
[ -f data/models/classifier_weights.json ] || "$PY" rust/tools/export_model.py "$ROOT"

step "cargo test (unit + golden)"                    bash -c "cd rust && cargo test --release --quiet 2>&1 | tail -15"
step "text pipeline: NLTK vs Rust (49,395 inputs)"   "$PY" rust/tools/compare_nlp.py "$ROOT" "$BIN/examples/nlp_diff"
step "classifier: scikit-learn vs Rust"              "$PY" rust/tools/compare_classifier.py "$ROOT" "$BIN/examples/clf_diff"
step "inference pipeline (3 thresholds)"             "$PY" rust/tools/compare_inference.py "$ROOT" "$BIN/examples/infer_diff"
step "components (forced intents, facts, resolver, search)" "$PY" rust/tools/compare_components.py "$ROOT" "$BIN/examples/components_diff"
step "JSON error messages: CPython fuzz"             "$PY" rust/tools/compare_json_errors.py "$BIN/examples/json_err_diff"
step "HTTP API + auth cross-compatibility"           "$PY" rust/tools/compare_http.py "$ROOT" "$BIN/rhcp-chatbot"
step "command-line chat"                             "$PY" rust/tools/compare_cli.py "$ROOT" "$PY" "$BIN/rhcp-chatbot"
step "fact database builder"                         "$PY" rust/tools/compare_fts.py "$ROOT" "$BIN/rhcp-chatbot"
step "training: scikit-learn vs Rust"                "$PY" rust/tools/compare_training.py "$ROOT" "$BIN/rhcp-chatbot" "$BIN/examples/clf_diff"

echo
if [ ${#failed[@]} -eq 0 ]; then echo "ALL CHECKS PASSED"; else echo "FAILED: ${failed[*]}"; exit 1; fi
