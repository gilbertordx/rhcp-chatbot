"""Compare the ORIGINAL Python inference pipeline with the Rust one, message by message.

Both produce a ResponseModel (intent, confidence, entities, final_message, raw_*).
Run at several confidence thresholds: the real one (0.60) rejects ~95% of
messages as "unknown", so lower thresholds are needed to exercise the answer-building code.

Some answers are chosen with random.choice from a list in the training corpus;
for those, both sides just have to pick *a* valid answer for the intent.

usage: python compare_inference.py <repo-root> <path-to-infer_diff-binary>   (run with cwd = repo root)
"""
import asyncio, json, os, random, subprocess, sys, tempfile, warnings
warnings.filterwarnings("ignore")
repo, binary = sys.argv[1:3]
os.chdir(repo); sys.path.insert(0, repo); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import logging; logging.disable(logging.CRITICAL)

import yaml
from app.chatbot.initializer import initialize_chatbot
from app.chatbot.memory import ConversationMemory
import app.core.inference as inf
from _cases import make_cases

# ---- build the message list ------------------------------------------------
rng = random.Random(11)
band = json.load(open("app/chatbot/data/static/band-info.json"))
disco = json.load(open("app/chatbot/data/static/discography.json"))
names = [m["name"] for k in ("currentMembers", "formerMembers") for m in band[k]]
names += ["flea", "anthony", "kiedis", "tony", "ak", "john", "frusciante", "johnny", "jf", "chad", "smith", "chadwick", "hillel", "slovak", "jack", "irons", "josh", "klinghoffer", "jk", "dave", "navarro", "fruciante", "kiedus"]
for k in ("studioAlbums", "compilationAlbums", "liveAlbums"):
    for a in disco[k]:
        names.append(a["name"]); names += a.get("tracks", [])
names += ["bssm", "blood sugar", "cali", "btw", "stadium", "ul", "getaway", "iwy", "ohm", "mothers milk", "umpp", "freaky", "debut", "utb", "scar", "otherside", "dani cali", "snow", "gia", "atw", "californication", "by the way", "road trippin", "black summer"]
for f in ("members", "albums", "songs"):
    for r in yaml.safe_load(open(f"data/knowledge/{f}.yml"))[f]:
        names += [r.get("title") or r.get("name"), *r.get("aliases", [])]
names = sorted({n for n in names if n})
templates = ["who is {x}", "tell me about {x}", "{x}", "what year was {x} released", "who wrote {x}", "play {x} please", "is {x} a good one?", "i love {x}!", "what is the story of {x}.", "TELL ME ABOUT {x}", "{x} and {y}", "compare {x} with {y}", "who are the members of the band {x}"]
msgs = []
for x in names:
    for t in rng.sample(templates, 5):
        msgs.append(t.format(x=x, y=rng.choice(names)))
cases = make_cases(repo)
utts = [c for c in cases[:7000]]                     # real utterances + variants
fuzz = rng.sample(cases, 3500)
msgs = list(dict.fromkeys(m for m in msgs + utts + fuzz + ["bye", "hello", "thanks", "", " ", "who is flea", "tell me about californication"] if m.strip()))[:14000]
print(f"{len(msgs)} messages")

# ---- the original pipeline ---------------------------------------------------
async def boot():
    return await initialize_chatbot()
import io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    processor = asyncio.run(boot())
    mem = ConversationMemory(max_sessions=100, session_timeout_hours=24)
    inf.initialize_inference(processor, mem)

def gate_at(threshold):
    valid = ["greetings.hello","greetings.bye","member.biography","band.members","album.info","song.info","band.history","intent.outofscope","unknown"]
    def gate(raw_intent, raw_confidence):
        if raw_confidence >= threshold:
            return (raw_intent if raw_intent in valid else "unknown"), raw_confidence
        return "unknown", raw_confidence
    return gate

def answers_for(intent):
    for key in ("base", "rhcp"):
        for item in processor.training_data[key]["data"]:
            if item["intent"] == intent and item.get("answers"):
                return set(item["answers"])
    return set()

failures = 0
for threshold in (0.60, 0.05, 0.0):
    inf.apply_confidence_gating = gate_at(threshold)
    expected = [inf.run_inference(m).model_dump() for m in msgs]
    tmp = tempfile.mktemp(suffix=".json"); json.dump(msgs, open(tmp, "w"))
    out = subprocess.run([binary, tmp, str(threshold)], capture_output=True, text=True, cwd=repo)
    if out.returncode != 0:
        print(out.stderr[-2000:]); sys.exit(2)
    got = json.loads(out.stdout.split("@@JSON@@", 1)[1]); os.unlink(tmp)

    bad = 0; random_ok = 0; shown = 0; intents = {}
    for m, e, g in zip(msgs, expected, got):
        intents[e["intent"]] = intents.get(e["intent"], 0) + 1
        problems = []
        for k in ("intent", "raw_intent"):
            if e[k] != g[k]: problems.append(k)
        for k in ("confidence", "raw_confidence"):
            if abs(e[k] - g[k]) > 1e-9: problems.append(k)
        if e["entities"] != g["entities"]:
            problems.append("entities")
        if e["final_message"] != g["final_message"]:
            pool = answers_for(e["intent"])
            if e["final_message"].strip() in {a.strip() for a in pool} and g["final_message"] in {a.strip() for a in pool}:
                random_ok += 1
            else:
                problems.append("final_message")
        if problems:
            bad += 1
            if shown < 6:
                shown += 1
                print(f"  MISMATCH {problems} for {m!r}")
                for k in problems[:2]:
                    print(f"    python[{k}]: {str(e[k])[:230]}\n    rust  [{k}]: {str(g[k])[:230]}")
    failures += bad
    print(f"threshold {threshold:.2f}: {len(msgs)} messages, {bad} mismatches ({random_ok} random-choice answers differed legitimately); intents seen: {dict(sorted(intents.items(), key=lambda kv: -kv[1])[:6])}")
sys.exit(1 if failures else 0)
