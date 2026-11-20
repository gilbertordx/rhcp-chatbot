#!/usr/bin/env bash
# Menu for the RHCP chatbot (Rust remaster): run it, test it, rebuild it.
cd "$(dirname "$0")/../.." || exit 1
BIN=rust/target/release/rhcp-chatbot

if ! command -v cargo >/dev/null 2>&1; then
  echo "Rust is not installed yet. Install it from https://rustup.rs and run this again."
  read -r -p "Press Enter to close..." _; exit 1
fi

build() {
  echo; echo "=== Building (the first time takes a few minutes) ==="
  cargo build --release --manifest-path rust/Cargo.toml || { echo "The build failed - read the messages above."; return 1; }
  if [ ! -f "${NLTK_DATA:-$HOME/nltk_data}/tokenizers/punkt_tab/english/abbrev_types.txt" ]; then
    echo; echo "=== One-time download of the sentence-splitter data ==="
    "$BIN" setup-nltk || echo "The download failed."
  fi
}
open_path() { if command -v xdg-open >/dev/null 2>&1; then xdg-open "$1"; else open "$1"; fi; }

build
while true; do
  clear 2>/dev/null
  cat <<'MENU'
============================================================
  RHCP chatbot - Rust remaster
============================================================
  [1] Chat in this window
  [2] Chat, but answer more often   (threshold 0.05 - see the guide, section 0)
  [3] Start the web API             (http://127.0.0.1:3000/healthz)
  [4] Run the tests
  [5] Retrain the classifier        (writes data/models/classifier_retrained.json)
  [6] Rebuild after editing code
  [7] Open the project folder
  [8] Open the learning guide
  [9] Quit
MENU
  read -r -p "Choose 1-9: " choice || exit 0   # end of input: leave instead of looping
  case "$choice" in
    1) echo; echo "Type a message, or  help / history / quit"; "$BIN" chat ;;
    2) echo; echo "Threshold 0.05: the bot answers far more often."; RHCP_CONFIDENCE_THRESHOLD=0.05 "$BIN" chat ;;
    3) echo; echo "API on http://127.0.0.1:3000  (Ctrl+C to stop)"; echo '  chat: POST /api/chat with {"message": "bye"}'
       DATABASE_URL=sqlite:///./data/dev_auth.db "$BIN" serve --host 127.0.0.1 ;;   # throw-away user database
    4) cargo test --release --manifest-path rust/Cargo.toml ;;
    5) "$BIN" train --out data/models/classifier_retrained.json
       echo "To try it: RHCP_MODEL_PATH=data/models/classifier_retrained.json $BIN chat" ;;
    6) build ;;
    7) open_path . ;;
    8) open_path docs/RUST_LEARNING.md ;;
    9) exit 0 ;;
    *) echo "Please type a number from 1 to 9." ;;
  esac
  echo; read -r -p "Press Enter to return to the menu..." _ || exit 0
done
