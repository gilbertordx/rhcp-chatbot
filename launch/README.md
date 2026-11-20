# Desktop shortcut and test menu

One shortcut opens a menu to run the Rust remaster **and** the development tasks (run the tests,
rebuild after editing, retrain, open the folder or the guide). It rebuilds when needed, so after you
edit code you just pick an option again.

**Windows** (needs [Rust](https://rustup.rs), installed once):
1. Double-click `launch\windows\create-desktop-shortcut.bat` (once).
2. Use the new **RHCP Chatbot (Rust)** shortcut on your desktop.

**macOS / Linux:** run `launch/unix/create-desktop-shortcut.sh` once, then use the launcher it creates.

Testing creates a throw-away user database at `data/dev_auth.db` and, if you retrain,
`data/models/classifier_retrained.json`; both are ignored by git.
