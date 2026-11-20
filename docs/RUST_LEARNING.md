# Learning Rust through the RHCP chatbot

This branch (`rust-remaster`) holds a Rust rewrite of the whole app in [`rust/`](../rust): the
text pipeline, the intent classifier (including **training** it), the entity matching, the
SQLite fact search, the HTTP API with login/JWT, and the command-line chat. The Python code is
untouched next to it so you can read both versions side by side.

This guide covers: what you should know about the original first, how to run it, what maps to
what, the Rust ideas (with the file where each one appears), every deliberate difference, and
how correctness was checked.

---

## 0. Read this first: what the original actually does

Porting a project forces you to read it closely. These are facts about the **original Python
code**, measured while porting. The Rust version reproduces them (on purpose, so the port can be
checked), and flags them so you can decide what to change.

1. **Almost every question is answered with "I'm not sure what you mean".** The API only accepts
   an intent when the classifier is at least 60% sure (`inference.py`), but the model is a
   63-70-class logistic regression trained on ~1,080 sentences, and its probabilities are rarely
   that high. A model freshly trained with the project's own recipe clears 60% on only **59 of
   its own 1,080 training sentences (5%)**. Over 10,285 test messages, **11** got a real intent.
   "who is flea" and "tell me about californication" both come back as "I'm not sure". This is
   not a scikit-learn version problem; it is the 0.60 threshold against this model. (The legacy
   `process_message` uses 0.05, which is why the code comment says "adjusted based on actual
   model performance".) Set `RHCP_CONFIDENCE_THRESHOLD` to try another value without editing code.
2. **Entities are found but never resolved.** The code asks for `raw_value["text"]`, which no
   record has, so the "span" is always empty and the fuzzy resolver never matches anything.
3. **Fact answers rarely find facts.** They look up the display name ("Anthony Kiedis") but the
   database keys are lower-case canonical names ("anthony kiedis"). For albums and songs the code
   even looks for a `title` key the record does not have.
4. **The command-line chat crashed on every message that contained a band member, album or song**
   (`'dict' object has no attribute 'dict'`). Fixed in Rust.
5. **`/readyz` always said "not ready"** because it checked a `data/model.bin` file that nothing
   creates, while the model really loads from `app/models/*.joblib`. Fixed in Rust.
6. **Conversation memory never records anything over HTTP.** Sessions must be created first, and
   the API never creates them.
7. The original's own test suite does not fully pass either (127 passed, 31 failed, 12 errors in
   this environment), so tests could not serve as the specification; the code's behaviour did.

None of this is a criticism: it is a learning project and the README says so. It does mean "make
it answer questions" is a separate, interesting next task. The cheapest first experiment is
`RHCP_CONFIDENCE_THRESHOLD=0.05`.

---

## 1. Running it

Rust toolchain from <https://rustup.rs>. From the repository root:

```bash
cargo build --release --manifest-path rust/Cargo.toml
```

```bash
# one-time: the sentence-splitter data the text pipeline needs (the Python app downloaded it too)
rust/target/release/rhcp-chatbot setup-nltk
```

```bash
rust/target/release/rhcp-chatbot chat                   # interactive
rust/target/release/rhcp-chatbot chat -m "hello" --json # one message, JSON out
rust/target/release/rhcp-chatbot serve                  # HTTP API on RHCP_HOST:RHCP_PORT (default 0.0.0.0:3000)
rust/target/release/rhcp-chatbot build-fts              # rebuild data/rhcp_fts.sqlite from data/knowledge/*.yml
rust/target/release/rhcp-chatbot train                  # retrain the classifier from the corpora
```

All the environment variables (`RHCP_*`, `SECRET_KEY`, `DATABASE_URL`, ...) keep their original
names, and a `.env` file is read like before. Only SQLite is supported (`sqlite:///...`).

The classifier lives in `data/models/classifier_weights.json` (6.4 MB). It was exported from the
original `.joblib` file by `rust/tools/export_model.py`, so **the Rust app answers exactly like the
Python app did**. If that file is missing the app trains a new model, as the Python did.

Run the unit and golden tests with `cargo test --release --manifest-path rust/Cargo.toml`.
Run **every** comparison against the original Python (about 3 minutes):

```bash
PYTHON=/path/to/python rust/tools/run_checks.sh
```

---

## 2. Python file → Rust file

| Python | Rust | What it does |
|---|---|---|
| NLTK `word_tokenize` + `PorterStemmer` | `nlp/tokenizer.rs`, `nlp/punkt.rs`, `nlp/porter.rs` | Turn a message into stemmed words, exactly like NLTK |
| scikit-learn pipeline (`predict_proba`) | `nlp/classifier.rs` | TF-IDF features + softmax regression |
| `train_new_model` | `nlp/trainer.rs` | Fit the vectorizer and the logistic regression |
| `app/chatbot/initializer.py` | `app.rs`, `data.rs` | Load data and the model; start-up |
| `app/chatbot/processor.py` | `processor.rs` | Find entities in text, write replies |
| `app/chatbot/memory.py` | `memory.rs` | Per-session conversation memory |
| `app/core/inference.py` | `inference.rs` | classify → gate → canonicalize → reply |
| `app/knowledge/resolver.py` | `resolver.rs` | Fuzzy matching against the YAML knowledge files |
| `app/knowledge/search.py` | `search.rs` | SQLite full-text fact lookup |
| `scripts/build_fts.py` | `fts_builder.rs` | Build that database |
| `app/models/user.py`, `app/services/auth.py`, `app/core/database.py` | `auth.rs` | Users, bcrypt, JWT, login sessions |
| `app/main.py`, `app/api/routes/*.py`, `app/core/auth.py` | `api.rs` | The HTTP API |
| `app/schemas.py` | `schemas.rs` | Request/response shapes and rules |
| `app/config.py`, `app/core/config.py` | `config.rs` | Environment configuration |
| `app/errors.py` | `errors.rs` | Error types |
| `cli.py` | `cli.rs`, `main.rs` | The terminal chat and all subcommands |
| `app/scripts/setup_nltk.py` | `nltk_setup.rs` | Download the NLTK data |
| (Python's text formatting) | `pyfmt.rs`, `pyjson.rs` | `str()`/`repr()`/`json.dumps` look-alikes (see §5) |

Suggested reading order: `schemas.rs` → `errors.rs` → `config.rs` → `data.rs` → `nlp/porter.rs` →
`nlp/tokenizer.rs` → `nlp/classifier.rs` → `processor.rs` → `inference.rs` → `search.rs` →
`auth.rs` → `api.rs` → `main.rs`. Leave `nlp/punkt.rs` and `nlp/trainer.rs` for last; they are the
longest.

---

## 3. The Rust ideas, where you will meet them

### 3.1 Types that describe the data (`schemas.rs`)
`Intent` is an `enum` of exactly nine values, so "an intent the API cannot return" cannot be
written. `serde` turns the enum to and from JSON strings (`#[serde(rename = "greetings.hello")]`)
and a `struct` into a JSON object. Pydantic validated at run time; here most of that is the type
system, and `ResponseModel::new` checks the few rules a type cannot express.

### 3.2 `Result` and `?` instead of exceptions (`auth.rs`, `search.rs`)
A function that can fail returns `Result<T, E>`. `?` means "if this failed, return the error to
my caller now". `AuthError` has two variants (`Invalid` shown as a 400, `Internal` shown as a
500), and the HTTP layer turns each into the right response with one `match`.

### 3.3 `Option` instead of `None`/`KeyError` (`processor.rs`)
`member.get("memberSince")` returns an `Option`; you must decide what happens when it is absent.
Look at how `member_since` is read with `.map(py_str).unwrap_or_else(|| "unknown year".into())`.

### 3.4 Ownership and borrowing (`nlp/porter.rs`, `nlp/tokenizer.rs`)
`&str` borrows text someone else owns; `String` owns it. The Porter stemmer works on `char`s
because a Rust `String` is UTF-8 bytes and "the 3rd letter" must mean a letter, not a byte. You
will see `drop_last` (Python `word[:-n]`) written out by hand for exactly that reason.

### 3.5 Closures stored in lists (`nlp/porter.rs`)
Each stemming rule is `(suffix, replacement, condition)` where the condition is a closure
(`Box<dyn Fn(&Porter, &str) -> bool>`). This is the Rust spelling of Python's list of lambdas, and
the place the borrow checker (the compiler's rules about who may use what) asks the most questions.

### 3.6 Pattern matching with `match` and `let ... else` (`api.rs`)
`let Some(x) = value else { return ...; }` reads: "get it, or give up here". The request handlers
are made of these, so each failure case is visible at the top of the function.

### 3.7 Iterators (`resolver.rs`, `classifier.rs`)
`.iter().filter(..).map(..).collect()` replaces list comprehensions. `classifier.rs` computes a
sparse dot product with `fold`.

### 3.8 `async` and the web server (`api.rs`, `main.rs`)
The server uses `axum` on the `tokio` runtime. CPU-bound work (classifying a message, bcrypt) goes
through `spawn_blocking` so it cannot stall other requests. Everything else (the CLI, training,
building the database) is plain synchronous code.

### 3.9 Shared state without globals (`api.rs`, `inference.rs`)
Python used module-level globals (`chatbot_processor`, `memory_manager`). Rust passes an
`AppState` that holds `Arc<Inference>` (a shared, reference-counted handle) and gets the same
effect with no global. `Mutex` protects the pieces that change (conversation memory, the opened
database connection).

### 3.10 Testing at several levels (`tests/golden.rs`, unit tests, `tools/`)
Unit tests sit next to the code (`#[cfg(test)]`). `tests/golden.rs` checks the port against values
recorded from the Python. `tools/*.py` run the *original* Python and the Rust on the same inputs
and compare (see §6).

### 3.11 Numbers and maths (`nlp/trainer.rs`)
The trainer is L-BFGS (a standard optimiser) written from scratch in ~80 lines. A unit test
checks the analytic gradient against a numerical estimate, which is the standard way to catch a
sign or scaling mistake in this kind of code.

---

## 4. Deliberate differences from the Python version

**Fixes** (the Python looked like a bug):
- The terminal chat no longer crashes on messages with entities (§0.4), and `history` now shows
  the bot's reply (Python stored an empty one).
- `/readyz` checks the file the app really loads: default `RHCP_MODEL_PATH` is
  `data/models/classifier_weights.json` (§0.5).
- A signed token whose `sub` is not a number gives `401` (Python raised an unhandled error, `500`).
- The user tables are created at start-up if missing (`CREATE TABLE IF NOT EXISTS`, identical
  schema); Python needed a manual step.
- Reaching the end of input in the interactive chat ends cleanly. The Python version looped forever
  printing `Unexpected error: EOF when reading a line` (about 900,000 lines in 5 seconds).

**Different by construction:**
- The classifier is read from JSON, not a Python pickle (no Rust can read a pickle). The export
  script is `rust/tools/export_model.py`.
- Only the NLTK `punkt_tab` data is downloaded; the Python also fetched `wordnet` and `omw-1.4`
  but never used them.
- Logging uses `tracing` (JSON lines with different field names than the Python formatter).
- Only SQLite databases are supported (the Python code mentioned PostgreSQL but `psycopg2` was
  never wired up).
- Sets that Python printed in arbitrary order (`mentioned_members`, the generic fact formatter)
  are sorted, so output is stable.
- `BCRYPT_ROUNDS` is read but, as in the Python, not used (hashes use cost 12).
- Extra environment variables for paths that were hard-coded: `RHCP_TRAINING_DIR`,
  `RHCP_KNOWLEDGE_DIR`, `RHCP_FTS_DB_PATH`, and `RHCP_CONFIDENCE_THRESHOLD`.
- One secret: `SECRET_KEY`. (`RHCP_SECRET_KEY` existed in the Python but was never used.)

**Behaviour kept even though it looks wrong:** everything in §0 except the items fixed above,
plus: `bye` in the terminal chat is a quit command before it reaches the model; the "who wrote"
follow-up always answers "I don't have writer information" (song records have no `details` key);
a login with a password over 72 bytes is a `500` (bcrypt 5 raises, nothing catches it) while
registering with one is a `400`.

**Not ported:** `scripts/evaluate*.py`, `enhance_data.py`, `validate_data.py`, `load_data.py`,
`performance_test.py`, the notebooks, and `psycopg2`/PostgreSQL support. They are development
tooling around training and evaluation; `rhcp-chatbot train` covers what `train_new_model` did; the richer experiment scripts
(cross-validation, plots) are not ported.

---

## 5. Python habits the Rust code has to imitate

A faithful port is mostly the small things. Examples worth looking at:
- **`pyfmt.rs`**: some answers embed a value with an f-string. Python prints `True`, `None`, and
  dictionaries as `{'name': 'Flea'}` (single quotes). Rust would print `true`. To keep answers
  identical there is a `repr()` look-alike.
- **`pyjson.rs`**: the CLI's `--json` output escapes every non-ASCII character (`é`), and
  FastAPI reported bad-JSON errors using Python's own error text and character offset
  (`"Expecting ',' delimiter"` at offset 15). `serde_json` words these differently, so
  `python_json_error` re-implements CPython's decoder error reporting (fuzz-tested against the
  real thing on 80,007 inputs).
- **`nlp/punkt.rs`**: NLTK splits `"going. use your brain"` into two sentences even in lower
  case, which changes the tokens the model sees (`going` + `.` instead of `going.`). Reproducing
  that required porting the Punkt algorithm.

---

## 6. How correctness was checked

`rust/tools/run_checks.sh` runs all of this against the **original Python code**, side by side.
Each comparison file explains itself at the top.

| Check | Result |
|---|---|
| Unit + golden tests (`cargo test`) | 21 + 5 pass |
| Text pipeline: NLTK vs Rust, 49,395 inputs (real sentences, joined sentences, abbreviations, quotes, unicode, random punctuation, stemmer stress) | **0 differences** |
| Classifier: scikit-learn `predict_proba` vs Rust, 49,395 inputs × 70 classes | largest difference **7.8e-16**; same top class every time |
| Whole inference pipeline, 10,285 messages at thresholds 0.60 / 0.05 / 0.00 | **0 differences** |
| Reply builders: every intent forced onto every entity message (810); fact formatters for all 46 database entities; resolver (1,442 spans); full-text search (63 queries) | **0 differences** |
| HTTP API: 100 requests incl. every validation error, every auth route, odd headers and tokens | **0 differences** (1 documented deviation) |
| Interoperability: a user, bcrypt hash and JWT made by Python work in Rust and the reverse, on the same SQLite file | all pass |
| Bad-JSON error text/offset, 80,007 fuzzed inputs vs CPython | **0 differences** |
| Command-line chat: 20 checks (commands, errors, `--json`, `--debug`, an interactive session) | all pass |
| Fact database built by Rust vs the original script vs the committed file | identical, 513 rows |
| Training vs scikit-learn (converged): vocabulary, IDF, weights, predictions | vocabulary and IDF **identical**; weights within 3.4e-6; predictions within 1e-6 |
| Training at scikit-learn's default tolerance (it stops early) | same top class on 99.8%; same share of messages pass the 0.60 gate |

Things the checks do **not** cover: the model *file* is the Python one, converted; a freshly
trained Rust model is a (very close) sibling of a scikit-learn one, not a byte copy. The
Docker file and GitHub Actions workflow in this repo still describe the Python app. Behaviour
under load and long-running memory use were not measured.

One mistake worth knowing about, because it is a good lesson: while building the HTTP comparison
the first run crashed and left a Rust server running on the test port; the next run then talked
to that stale server and reported many "failures" that were really a leftover process. The
harness now picks free ports and always shuts its servers down.

---

## 7. Exercises

1. Run `RHCP_CONFIDENCE_THRESHOLD=0.05 rust/target/release/rhcp-chatbot chat -m "tell me about anthony kiedis"` and compare with the default. What does the answer say, and why does it
   not mention his facts (§0.3)?
2. Make `canonicalize_entities` in `inference.rs` pass the matched text as the span (§0.2). Which
   of the comparison tools now reports a difference, and is that difference an improvement?
3. In `inference.rs` (`build_factual_response`), make the fact lookup use the entity's name in lower
   case (§0.3). Which messages start returning facts? Look at which formatter ran (it is chosen by
   the *intent*, not by the entity type) and whether it fits the facts it was given.
4. Add `--tol` and `--c` experiments: train with `--tol 1e-9` and with a different `C` in
   `TrainConfig`, and watch the share of training sentences above 0.60 change.
5. Delete a `.clone()` in `processor.rs` and read the compiler's message.

Good references: *The Rust Programming Language* (doc.rust-lang.org/book), *Rust by Example*, and
the axum and serde documentation.
