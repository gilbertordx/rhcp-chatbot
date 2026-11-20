"""Compare the original `python cli.py` with `rhcp-chatbot chat` on commands and on
messages that do not contain band/album/song names (those crash the Python CLI).
usage: python compare_cli.py <repo-root> <python> <rust-binary>"""
import json, os, re, subprocess, sys
repo, py, rust = sys.argv[1:4]
os.chdir(repo)
NOISE = re.compile(r'^(\{"ts".*|\[\d\d:\d\d:\d\d\.\d+\].*|\[nltk_data\].*|Initializing chatbot\.\.\.|Loaded static data.*|Loading NLU.*|NLU classifier loaded.*|Static data validation.*|Chatbot initialized.*|Downloading NLTK.*|\s*)$')

def run(cmd, stdin=None):
    p = subprocess.run(cmd, capture_output=True, text=True, input=stdin if stdin is not None else "", env={**os.environ, "PYTHONWARNINGS": "ignore"}, timeout=120)
    lines = [l for l in p.stdout.splitlines() if not NOISE.match(l)]
    return p.returncode, lines

def both(args, stdin=None):
    return run([py, "-W", "ignore", "cli.py", *args], stdin), run([rust, "chat", *args], stdin)

fails = 0
def check(label, a, b, normalise=lambda x: x):
    global fails
    ok = normalise(a) == normalise(b)
    print(("PASS " if ok else "FAIL ") + label)
    if not ok:
        fails += 1; print("   python:", a); print("   rust:  ", b)

for msg in ["help", "commands", "quit", "exit", "bye", "HELP", "  quit  ", "history", "hello", "what is the best pizza", "who are the members of the band", "x", "tell me a joke"]:
    a, b = both(["-m", msg]); check(f"-m {msg!r}", a, b)
# (an empty -m "" is falsy in Python and starts interactive mode, so it is not compared here)
for label, msg in [("spaces", "   "), ("2001 chars", "a" * 2001)]:
    a, b = both(["-m", msg])
    check(f"-m {label}", a, b)
# --json (floats compared approximately)
a, b = both(["--json", "-m", "hello"])
def js(x): 
    rc, lines = x; return rc, json.loads("\n".join(lines))
def close(p, q):
    if isinstance(p, float) or isinstance(q, float): return abs(p - q) < 1e-9
    if isinstance(p, dict): return p.keys() == q.keys() and list(p) == list(q) and all(close(p[k], q[k]) for k in p)
    if isinstance(p, list): return len(p) == len(q) and all(close(x, y) for x, y in zip(p, q))
    return p == q
(ra, ja), (rb, jb) = js(a), js(b)
print(("PASS " if ra == rb and close(ja, jb) else "FAIL ") + "--json -m hello (same keys, order and values)"); fails += not (ra == rb and close(ja, jb))
a, b = both(["--json", "-m", "help"]); print(("PASS " if js(a) == js(b) else "FAIL ") + "--json -m help"); fails += js(a) != js(b)
# --debug adds the intent line
a, b = both(["--debug", "-m", "hello"])
strip_conf = lambda x: (x[0], [re.sub(r"confidence: [0-9.]+", "confidence: N", l) for l in x[1]])
check("--debug -m hello", a, b, strip_conf)
# interactive session via stdin ("Bot:" lines in `history` are intentionally filled in by Rust)
script = "help\nhistory\nhello\nwhat is the best pizza\nhistory\ncommands\n\n   \nquit\nnever reached\n"
a, b = both([], script)
fix_bot = lambda x: (x[0], [re.sub(r"^  Bot: .*$", "  Bot: <reply>", re.sub(r"\((0\.\d{3})\)", "(N)", l)) for l in x[1]])
check("interactive session (help, history, chat, commands, blanks, quit)", a, b, fix_bot)
# the intentional fixes
rc, lines = run([rust, "chat", "-m", "who is flea"])
print(("PASS " if rc == 0 and lines else "FAIL ") + "Rust answers a message with an entity (Python crashes: 'dict' object has no attribute 'dict')"); fails += not (rc == 0 and lines)
rc_p, lines_p = run([py, "-W", "ignore", "cli.py", "-m", "who is flea"])
print("      (Python gives:", lines_p, ")")
sys.exit(1 if fails else 0)
