@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0..\.."
title RHCP Chatbot (Rust) - menu
set "BIN=rust\target\release\rhcp-chatbot.exe"

where cargo >nul 2>nul
if errorlevel 1 (
  echo.
  echo Rust is not installed yet.
  echo Install it from https://rustup.rs  ^(it also asks for the Visual Studio C++ Build Tools^),
  echo then double-click this shortcut again.
  pause
  exit /b 1
)

:build
echo.
echo === Building ^(the first time takes a few minutes, later runs are quick^) ===
cargo build --release --manifest-path rust\Cargo.toml
if errorlevel 1 (
  echo.
  echo The build failed - read the messages above.
  pause
  goto menu
)
if not exist "%USERPROFILE%\nltk_data\tokenizers\punkt_tab\english\abbrev_types.txt" (
  echo.
  echo === One-time download of the sentence-splitter data ===
  "%BIN%" setup-nltk
  if errorlevel 1 ( echo The download failed. & pause )
)

:menu
cls
echo ============================================================
echo   RHCP chatbot - Rust remaster
echo ============================================================
echo   [1] Chat in this window
echo   [2] Chat, but answer more often   ^(threshold 0.05 - see the guide, section 0^)
echo   [3] Start the web API             ^(http://127.0.0.1:3000/healthz^)
echo   [4] Run the tests
echo   [5] Retrain the classifier        ^(writes data\models\classifier_retrained.json^)
echo   [6] Rebuild after editing code
echo   [7] Open the project folder
echo   [8] Open the learning guide
echo   [9] Quit
echo.
choice /c 123456789 /n /m "Choose 1-9: "
if errorlevel 9 goto quit
if errorlevel 8 goto guide
if errorlevel 7 goto folder
if errorlevel 6 goto build
if errorlevel 5 goto retrain
if errorlevel 4 goto tests
if errorlevel 3 goto serve
if errorlevel 2 goto chatlow
if errorlevel 1 goto chat

:chat
echo.
echo Type a message, or  help  /  history  /  quit
"%BIN%" chat
pause
goto menu

:chatlow
setlocal
set RHCP_CONFIDENCE_THRESHOLD=0.05
echo.
echo Threshold 0.05: the bot answers far more often. Type  help  /  quit
"%BIN%" chat
endlocal
pause
goto menu

:serve
setlocal
rem a separate throw-away user database, so testing never changes files tracked by git
set DATABASE_URL=sqlite:///./data/dev_auth.db
echo.
echo API on http://127.0.0.1:3000   ^(press Ctrl+C to stop^)
echo   try:  http://127.0.0.1:3000/healthz
echo   chat: POST /api/chat  with  {"message": "bye"}
start "" cmd /c "timeout /t 3 >nul & start http://127.0.0.1:3000/healthz"
"%BIN%" serve --host 127.0.0.1
endlocal
pause
goto menu

:tests
cargo test --release --manifest-path rust\Cargo.toml
pause
goto menu

:retrain
"%BIN%" train --out data\models\classifier_retrained.json
echo.
echo To try it:  set RHCP_MODEL_PATH=data\models\classifier_retrained.json   and start option 1/2/3 from that window.
pause
goto menu

:folder
start "" "%CD%"
goto menu

:guide
start "" "docs\RUST_LEARNING.md"
goto menu

:quit
endlocal
exit /b 0
