"""Component-level comparisons of the ORIGINAL Python code against Rust:
  forced : every intent forced onto messages that contain entities (reaches answer
           builders the model almost never selects: album/song facts, ambiguity, ...)
  facts  : the DB fact rows and the four answer formatters for every canonical name
  resolver: fuzzy entity resolution (typos, accents, aliases)
  search : FTS5 full-text queries
usage: python compare_components.py <repo-root> <path-to-components_diff-binary>
"""
import io, json, os, random, subprocess, sys, tempfile, warnings, contextlib, asyncio, logging
warnings.filterwarnings("ignore"); logging.disable(logging.CRITICAL)
repo, binary = sys.argv[1:3]
os.chdir(repo); sys.path.insert(0, repo); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yaml
from app.chatbot.initializer import initialize_chatbot
from app.chatbot.memory import ConversationMemory
import app.core.inference as inf
from app.knowledge import search, resolver as res

def rust(*args):
    out = subprocess.run([binary, *args], capture_output=True, text=True, cwd=repo)
    if out.returncode != 0: print(out.stderr[-2500:]); sys.exit(2)
    return json.loads(out.stdout.split("@@JSON@@", 1)[1])

def close(a, b):
    """Equal, treating floats within 1e-9 as equal (two correct implementations differ at ~1e-16)."""
    if isinstance(a, float) or isinstance(b, float):
        return isinstance(a, (int, float)) and isinstance(b, (int, float)) and abs(a - b) < 1e-9
    if isinstance(a, dict): return isinstance(b, dict) and a.keys() == b.keys() and all(close(a[k], b[k]) for k in a)
    if isinstance(a, list): return isinstance(b, list) and len(a) == len(b) and all(close(x, y) for x, y in zip(a, b))
    return a == b


def tmpjson(obj):
    p = tempfile.mktemp(suffix=".json"); json.dump(obj, open(p, "w")); return p

with contextlib.redirect_stdout(io.StringIO()):
    processor = asyncio.run(initialize_chatbot())
    inf.initialize_inference(processor, ConversationMemory())
rng = random.Random(5)
failures = 0
def report(name, n, bad, shown):
    global failures
    failures += bad
    print(f"{name:9} {n:6} cases, {bad} mismatches")
    for s in shown[:5]: print("   ", s)

# ---------------- forced intents ----------------
band = json.load(open("app/chatbot/data/static/band-info.json")); disco = json.load(open("app/chatbot/data/static/discography.json"))
names = [m["name"] for k in ("currentMembers", "formerMembers") for m in band[k]] + ["flea", "kiedis", "john", "chad", "hillel"]
for k in ("studioAlbums", "compilationAlbums", "liveAlbums"):
    for a in disco[k]: names += [a["name"]] + a.get("tracks", [])
names += ["bssm", "cali", "btw", "utb", "scar", "otherside", "dani", "snow", "gia", "californication", "by the way", "stadium", "unlimited love"]
intents = ["greetings.hello","greetings.bye","member.biography","band.members","album.info","song.info","band.history","intent.outofscope","unknown"]
pairs = [[f"tell me about {n} and {rng.choice(names)}", i] for n in sorted(set(names)) for i in intents]
exp = []
for m, i in pairs:
    ri, rc, re_ = inf.classify(m); ents = inf.canonicalize_entities(re_)
    exp.append(inf.build_response(i, 0.9, ents, ri, rc, None).model_dump())
got = rust("forced", tmpjson(pairs))
def answers(intent):
    for key in ("base", "rhcp"):
        for it in processor.training_data[key]["data"]:
            if it["intent"] == intent and it.get("answers"): return {a.strip() for a in it["answers"]}
    return set()
bad, shown = 0, []
kinds = {}
for (m, i), e, g in zip(pairs, exp, got):
    same = close(e, g)
    if not same and e["final_message"] != g["final_message"] and close({k: v for k, v in e.items() if k != "final_message"}, {k: v for k, v in g.items() if k != "final_message"}):
        same = e["final_message"].strip() in answers(i) and g["final_message"] in answers(i)
    kinds[e["final_message"][:34]] = kinds.get(e["final_message"][:34], 0) + 1
    if not same:
        bad += 1; shown.append(f"{m!r} / {i}: py={e['final_message'][:120]!r} rust={g['final_message'][:120]!r}")
report("forced", len(pairs), bad, shown)
print("          distinct reply openings exercised:", len(kinds))

# ---------------- facts ----------------
exp = {}
for kind in ("member", "album", "song"):
    for c in sorted({f.canonical for f in search.get_facts_by_type(kind, 100000)}):
        facts = search.get_facts_by_canonical(c, kind)
        exp[f"{kind}|{c}"] = {
            "facts": [[f.id, f.type, f.canonical, f.field, f.value, f.year, f.source] for f in facts],
            "member": inf._build_member_response(facts, c), "album": inf._build_album_response(facts, c),
            "song": inf._build_song_response(facts, c), "generic": inf._build_generic_response(facts, c, kind)}
got = rust("facts")
bad, shown = 0, []
for k in exp:
    g = got.get(k)
    for field in exp[k]:
        e = exp[k][field]
        # the generic formatter de-duplicates through a Python set (unordered): compare as word multisets
        if field == "generic":
            ok = g and sorted(e.replace(",", "").split()) == sorted(g[field].replace(",", "").split())
        else:
            ok = g and e == g[field]
        if not ok: bad += 1; shown.append(f"{k} [{field}]: py={str(e)[:130]!r} rust={str(g and g[field])[:130]!r}")
report("facts", len(exp), bad + (len(exp) != len(got)), shown)

# ---------------- resolver ----------------
spans = []
canon = []
for f in ("members", "albums", "songs"):
    for r in yaml.safe_load(open(f"data/knowledge/{f}.yml"))[f]: canon += [r["canonical"], *r.get("aliases", [])]
for c in canon:
    spans += [c, c.upper(), c + "x", c[1:], c[:-1], c.replace("a", "e", 1), (c[1] + c[0] + c[2:]) if len(c) > 2 else c, c.replace("s", "z"), " " + c + " ", c.replace("e", "é")]
spans += ["", " ", "bjork", "Björk", "fruciante", "flee", "kiedus", "caliphornication", "!!!", "x", "under bridge", "qu", "nation", "ação"]
spans = sorted(set(spans))
r = res.get_knowledge_resolver()
exp = []
for s in spans:
    n = lambda v: v["canonical"] if v else None
    exp.append({"member": n(r.resolve_member(s)), "album": n(r.resolve_album(s)), "song": n(r.resolve_song(s)), "any": n(r.resolve_entity(s)), "norm": r._normalize_span(s)})
got = rust("resolver", tmpjson(spans))
bad = [f"{s!r}: py={e} rust={g}" for s, e, g in zip(spans, exp, got) if e != g]
report("resolver", len(spans), len(bad), bad)

# ---------------- search ----------------
queries = ["flea", "bass", "californication", "1991", "under the bridge", "funk", "album", "anthony kiedis", "Red Hot", "founding member", "\"lead guitarist\"", "bass AND trumpet", "drum*", "NEAR(a b)", "(((", "\"", "AND", "year:1999", "notes:ballad", "", "  "]
exp = []
for q in queries:
    for t in (None, "member", "song"):
        exp.append([f.id for f in search.search_facts(q, 5, t)])
got = rust("search", tmpjson(queries))
bad = [f"{q!r}: py={e} rust={g}" for (q, e, g) in zip([q for q in queries for _ in range(3)], exp, got) if e != g]
report("search", len(exp), len(bad), bad)
sys.exit(1 if failures else 0)
