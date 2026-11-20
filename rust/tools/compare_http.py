"""Run the ORIGINAL FastAPI app (in-process) and the Rust server (real HTTP) through
the same requests and compare status codes, JSON bodies and key headers.

Dynamic values (uuids, tokens, timestamps, random answers) are normalised first.
Then a cross-compatibility phase checks that each side accepts users, password hashes
and tokens created by the other, via a shared SQLite file and shared secret.

usage: python compare_http.py <repo-root> <path-to-rhcp-chatbot-binary>
"""
import contextlib, io, json, os, re, sqlite3, subprocess, sys, tempfile, time, warnings, logging
warnings.filterwarnings("ignore"); logging.disable(logging.CRITICAL)
repo, binary = sys.argv[1:3]
os.chdir(repo); sys.path.insert(0, repo)

work = tempfile.mkdtemp(prefix="rhcp-http-")
PY_DB, RS_DB = f"{work}/py.db", f"{work}/rs.db"
SECRET = "shared-test-secret"
MODEL = "data/models/classifier_weights.json"
os.environ.update({"DATABASE_URL": f"sqlite:///{PY_DB}", "SECRET_KEY": SECRET, "RHCP_MODEL_PATH": MODEL})

import jwt, requests
from fastapi.testclient import TestClient
with contextlib.redirect_stdout(io.StringIO()):
    from app.main import app
    from app.core.database import create_tables
    create_tables()
    py = TestClient(app, raise_server_exceptions=False); py.__enter__()

import socket
def free_port():
    with socket.socket() as sk:
        sk.bind(("127.0.0.1", 0)); return sk.getsockname()[1]
PORT = free_port()
PORT2 = free_port()
def start_rust(db, port):
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{db}", "SECRET_KEY": SECRET, "RHCP_MODEL_PATH": MODEL, "RHCP_LOG_LEVEL": "ERROR"}
    p = subprocess.Popen([binary, "serve", "--host", "127.0.0.1", "--port", str(port)], cwd=repo, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(100):
        try:
            requests.get(f"http://127.0.0.1:{port}/healthz", timeout=1); return p
        except Exception: time.sleep(0.2)
    raise SystemExit("rust server did not start")
rs_proc = start_rust(RS_DB, PORT)
import atexit; atexit.register(lambda: rs_proc.poll() is None and rs_proc.terminate())
BASE = f"http://127.0.0.1:{PORT}"

def call_py(method, path, **kw):  return py.request(method, path, **kw)
def call_rs(method, path, **kw):
    if "content" in kw:                      # httpx calls it `content`, requests calls it `data`
        kw["data"] = kw.pop("content").encode("utf-8")
    return requests.request(method, BASE + path, **kw)

UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
JWT = re.compile(r"^eyJ[\w-]+\.[\w-]+\.[\w-]+$")
TS = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d+)?$")
def norm(v):
    if isinstance(v, dict): return {k: norm(x) for k, x in v.items()}
    if isinstance(v, list): return [norm(x) for x in v]
    if isinstance(v, str):
        if UUID.match(v): return "<uuid>"
        if JWT.match(v): return "<jwt>"
        m = TS.match(v)
        if m: return "<ts.us>" if m.group(1) else "<ts>"
    return v
def close(a, b):
    if isinstance(a, float) or isinstance(b, float):
        return isinstance(a, (int, float)) and isinstance(b, (int, float)) and abs(a - b) < 1e-9
    if isinstance(a, dict): return isinstance(b, dict) and a.keys() == b.keys() and all(close(a[k], b[k]) for k in a)
    if isinstance(a, list): return isinstance(b, list) and len(a) == len(b) and all(close(x, y) for x, y in zip(a, b))
    return a == b

import yaml
ANS = {}
for key, fn in (("base", "base-corpus.json"), ("rhcp", "rhcp-corpus-v2.json")):
    for it in json.load(open(f"app/chatbot/data/training/{fn}"))["data"]:
        if it.get("answers"): ANS.setdefault(it["intent"], {a.strip() for a in it["answers"]})

failures = 0; total = 0
# Differences that are deliberate (documented in docs/RUST_LEARNING.md): the label -> why.
EXPECTED = {
    "token [sub not int]": "Python raises an unhandled ValueError (500); Rust answers 401 like any other bad token",
}
expected_seen = []
def compare(label, method, path, ctx=None, **kw):
    """Send to both servers; `ctx` may supply per-server kwargs via callables."""
    global failures, total
    total += 1
    kw_py = {k: (v[0] if isinstance(v, tuple) else v) for k, v in kw.items()}
    kw_rs = {k: (v[1] if isinstance(v, tuple) else v) for k, v in kw.items()}
    a, b = call_py(method, path, **kw_py), call_rs(method, path, **kw_rs)
    problems = []
    if a.status_code != b.status_code: problems.append(f"status {a.status_code} vs {b.status_code}")
    try: ja, jb = a.json(), b.json()
    except Exception: ja, jb = a.text, b.text
    ja, jb = norm(ja), norm(jb)
    if not close(ja, jb):
        # chat answers chosen at random from the corpus
        ok = False
        if isinstance(ja, dict) and "response" in ja and isinstance(jb, dict) and "response" in jb:
            ra, rb = dict(ja["response"]), dict(jb["response"])
            fa, fb = ra.pop("final_message"), rb.pop("final_message")
            pool = ANS.get(ra["intent"], set())
            ok = close(ra, rb) and ja["session_id"] == jb["session_id"] or close(ra, rb)
            ok = ok and (fa == fb or (fa.strip() in pool and fb.strip() in pool))
        if not ok: problems.append(f"body\n      py:   {json.dumps(ja)[:330]}\n      rust: {json.dumps(jb)[:330]}")
    for h in ("www-authenticate", "content-type"):
        if a.headers.get(h, "").split(";")[0] != b.headers.get(h, "").split(";")[0]:
            problems.append(f"header {h}: {a.headers.get(h)!r} vs {b.headers.get(h)!r}")
    if problems and label in EXPECTED:
        expected_seen.append(f"{label}: {EXPECTED[label]}")
        return a, b
    if problems:
        failures += 1
        print(f"FAIL {label}: " + "; ".join(problems))
    return a, b

J = {"content-type": "application/json"}
# ---------------- basics ----------------
compare("healthz", "GET", "/healthz")
compare("readyz", "GET", "/readyz")
compare("404", "GET", "/nope")
compare("405 healthz", "DELETE", "/healthz")
compare("405 chat", "GET", "/api/chat")
compare("405 login", "GET", "/api/auth/login")
# ---------------- chat ----------------
compare("chat bye", "POST", "/api/chat", json={"message": "bye"})
compare("chat hello", "POST", "/api/chat", json={"message": "hello"})
compare("chat with session header", "POST", "/api/chat", json={"message": "who is flea"}, headers={"X-Session-ID": "my-session"})
compare("chat entity", "POST", "/api/chat", json={"message": "tell me about californication"})
compare("chat stripped", "POST", "/api/chat", json={"message": "   bye   "})
compare("chat 2000 chars ok", "POST", "/api/chat", json={"message": "a" * 2000})
compare("chat unicode", "POST", "/api/chat", json={"message": "quem é o flea? 🎸 ação"})
compare("chat empty", "POST", "/api/chat", json={"message": ""})
compare("chat spaces", "POST", "/api/chat", json={"message": "   "})
compare("chat 2001", "POST", "/api/chat", json={"message": "a" * 2001})
compare("chat missing", "POST", "/api/chat", json={})
compare("chat int", "POST", "/api/chat", json={"message": 5})
compare("chat null", "POST", "/api/chat", json={"message": None})
compare("chat list msg", "POST", "/api/chat", json={"message": ["a"]})
compare("chat extra field", "POST", "/api/chat", json={"message": "bye", "x": 1})
compare("chat array body", "POST", "/api/chat", json=["bye"])
compare("chat string body", "POST", "/api/chat", content='"bye"', headers=J)
compare("chat number body", "POST", "/api/chat", content="42", headers=J)
compare("chat no content-type", "POST", "/api/chat", content='{"message":"bye"}')
compare("chat text/plain", "POST", "/api/chat", content='{"message":"bye"}', headers={"content-type": "text/plain"})
compare("chat empty body", "POST", "/api/chat", content="", headers=J)
compare("chat bad json 1", "POST", "/api/chat", content="{nope", headers=J)
compare("chat bad json 2", "POST", "/api/chat", content='{"message": "x",}', headers=J)
compare("chat bad json 3", "POST", "/api/chat", content='{"message": "x"', headers=J)
compare("chat bad json 4", "POST", "/api/chat", content="not json at all", headers=J)
compare("chat ct +json", "POST", "/api/chat", content='{"message":"bye"}', headers={"content-type": "application/vnd.api+json"})
# ---------------- auth: unauthenticated ----------------
for label, hdr in [("no header", {}), ("Basic", {"Authorization": "Basic abc"}), ("Bearer only", {"Authorization": "Bearer"}),
                   ("Bearer garbage", {"Authorization": "Bearer abc"}), ("lowercase bearer garbage", {"Authorization": "bearer abc"}),
                   ("two spaces", {"Authorization": "Bearer  abc"}), ("empty", {"Authorization": ""}), ("token only", {"Authorization": "abc"})]:
    compare(f"me [{label}]", "GET", "/api/auth/me", headers=hdr)
compare("logout no token", "POST", "/api/auth/logout")
compare("users no token", "GET", "/api/auth/users")
compare("users/abc no token", "GET", "/api/auth/users/abc")
# ---------------- register ----------------
good = {"username": "alice_1", "email": "alice@example.com", "password": "password123", "first_name": "Al"}
compare("register ok", "POST", "/api/auth/register", json=good)
compare("register dup username", "POST", "/api/auth/register", json={**good, "email": "other@example.com"})
compare("register dup email", "POST", "/api/auth/register", json={**good, "username": "alice_2"})
compare("register bad email", "POST", "/api/auth/register", json={**good, "username": "bob", "email": "nope"})
compare("register short pw", "POST", "/api/auth/register", json={**good, "username": "bob", "password": "short"})
compare("register bad username chars", "POST", "/api/auth/register", json={**good, "username": "a!b"})
compare("register short username", "POST", "/api/auth/register", json={**good, "username": "ab"})
compare("register long username", "POST", "/api/auth/register", json={**good, "username": "x" * 21})
compare("register missing 2", "POST", "/api/auth/register", json={"username": "bob"})
compare("register all missing", "POST", "/api/auth/register", json={})
compare("register wrong types", "POST", "/api/auth/register", json={"username": 5, "email": ["x"], "password": None})
compare("register optional wrong type", "POST", "/api/auth/register", json={**good, "username": "carol", "email": "c@example.com", "first_name": 5})
compare("register optional null", "POST", "/api/auth/register", json={**good, "username": "dave_1", "email": "d@example.com", "first_name": None, "last_name": "D"})
compare("register 80-byte pw", "POST", "/api/auth/register", json={**good, "username": "longpw", "email": "l@example.com", "password": "p" * 80})
compare("register 72-byte pw ok", "POST", "/api/auth/register", json={**good, "username": "pw72", "email": "p72@example.com", "password": "p" * 72})
compare("register unicode pw", "POST", "/api/auth/register", json={**good, "username": "uni", "email": "u@example.com", "password": "pässwörd-ação"})
compare("register array", "POST", "/api/auth/register", json=[1])
# ---------------- login / session ----------------
a, b = compare("login ok", "POST", "/api/auth/login", json={"username": "alice_1", "password": "password123"})
tok = {"py": a.json().get("access_token"), "rs": b.json().get("access_token")}
sid = {"py": a.json().get("session_id"), "rs": b.json().get("session_id")}
def H(extra=None): return {"headers": ({"Authorization": f"Bearer {tok['py']}", **(extra or {})}, {"Authorization": f"Bearer {tok['rs']}", **(extra or {})})}
compare("login wrong pw", "POST", "/api/auth/login", json={"username": "alice_1", "password": "wrong"})
compare("login unknown user", "POST", "/api/auth/login", json={"username": "zed", "password": "x"})
compare("login missing", "POST", "/api/auth/login", json={"username": "alice_1"})
compare("login long pw (500)", "POST", "/api/auth/login", json={"username": "alice_1", "password": "p" * 80})
compare("login unicode pw", "POST", "/api/auth/login", json={"username": "uni", "password": "pässwörd-ação"})
compare("me", "GET", "/api/auth/me", **H())
compare("me lowercase scheme", "GET", "/api/auth/me", headers=({"Authorization": f"bearer {tok['py']}"}, {"Authorization": f"bearer {tok['rs']}"}))
compare("update me", "PUT", "/api/auth/me?first_name=Alicia&last_name=Z", **H())
compare("update me only last", "PUT", "/api/auth/me?last_name=Only", **H())
compare("update me empty string", "PUT", "/api/auth/me?first_name=", **H())
compare("update me unicode", "PUT", "/api/auth/me?first_name=Jos%C3%A9", **H())
compare("update me body ignored", "PUT", "/api/auth/me", json={"first_name": "Q"}, **H())
compare("users non-admin", "GET", "/api/auth/users", **H())
compare("users/1 non-admin", "GET", "/api/auth/users/1", **H())
compare("activate non-admin", "PUT", "/api/auth/users/1/activate", **H())
compare("cleanup non-admin", "POST", "/api/auth/cleanup-sessions", **H())
# promote alice to admin on both databases
for db in (PY_DB, RS_DB):
    c = sqlite3.connect(db); c.execute("UPDATE users SET is_admin = 1 WHERE username = 'alice_1'"); c.commit(); c.close()
# a token minted AFTER promotion carries is_admin (claims are not re-read, but the DB is)
a, b = compare("login again (admin)", "POST", "/api/auth/login", json={"username": "alice_1", "password": "password123"})
tok = {"py": a.json()["access_token"], "rs": b.json()["access_token"]}
sid = {"py": a.json()["session_id"], "rs": b.json()["session_id"]}
compare("users admin", "GET", "/api/auth/users", **H())
compare("users/1 admin", "GET", "/api/auth/users/1", **H())
compare("users/999 admin", "GET", "/api/auth/users/999", **H())
compare("users/abc admin", "GET", "/api/auth/users/abc", **H())
compare("users/1.5 admin", "GET", "/api/auth/users/1.5", **H())
compare("activate 2", "PUT", "/api/auth/users/2/activate", **H())
compare("activate 999", "PUT", "/api/auth/users/999/activate", **H())
compare("activate abc", "PUT", "/api/auth/users/abc/activate", **H())
compare("deactivate 3", "PUT", "/api/auth/users/3/deactivate", **H())
compare("deactivated user cannot login", "POST", "/api/auth/login", json={"username": "dave_1", "password": "password123"})
compare("cleanup sessions", "POST", "/api/auth/cleanup-sessions", **H())
compare("logout with header", "POST", "/api/auth/logout", headers=({"Authorization": f"Bearer {tok['py']}", "X-Session-ID": sid["py"]}, {"Authorization": f"Bearer {tok['rs']}", "X-Session-ID": sid["rs"]}))
compare("logout with query", "POST", f"/api/auth/logout?session_id=nonexistent", **H())
# ---------------- token edge cases (same token to both) ----------------
import datetime as dt
def mint(**over):
    claims = {"sub": "1", "username": "alice_1", "is_admin": True, "exp": int(time.time()) + 600}; claims.update(over)
    return jwt.encode({k: v for k, v in claims.items() if v is not None}, over.pop("_key", SECRET) if False else SECRET, algorithm="HS256")
cases = {
    "valid minted": mint(),
    "expired": mint(exp=int(time.time()) - 5),
    "no exp": mint(exp=None),
    "sub not int": mint(sub="abc"),
    "unknown user": mint(sub="9999"),
    "wrong secret": jwt.encode({"sub": "1", "exp": int(time.time()) + 600}, "other-secret", algorithm="HS256"),
    "alg none": jwt.encode({"sub": "1", "exp": int(time.time()) + 600}, None, algorithm="none"),
    "HS512": jwt.encode({"sub": "1", "exp": int(time.time()) + 600}, SECRET, algorithm="HS512"),
    "tampered": mint()[:-3] + "AAA",
}
for label, t in cases.items():
    compare(f"token [{label}]", "GET", "/api/auth/me", headers={"Authorization": f"Bearer {t}"})

print(f"\nphase 1: {total} requests compared, {failures} failed, {len(expected_seen)} expected deviation(s):")
for line in expected_seen: print("   -", line)

# ---------------- phase 2: cross-compatibility ----------------
f2 = 0
def check(label, ok, extra=""):
    global f2
    print(("PASS " if ok else "FAIL ") + label + (f"  {extra}" if extra and not ok else ""))
    if not ok: f2 += 1
# (a) Rust-created user + Python code on the SAME database file
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.services.auth import AuthService
eng = create_engine(f"sqlite:///{RS_DB}"); S = sessionmaker(bind=eng)()
svc = AuthService(S)
u = svc.authenticate_user("alice_1", "password123")
check("Python verifies a bcrypt hash created by Rust (login)", u is not None)
rs_token = requests.post(BASE + "/api/auth/login", json={"username": "alice_1", "password": "password123"}).json()["access_token"]
check("Python accepts a JWT issued by Rust", svc.get_user_by_token(rs_token) is not None)
check("Rust JWT has the same claim names", set(jwt.decode(rs_token, SECRET, algorithms=["HS256"])) == {"sub", "username", "is_admin", "exp"})
check("Rust JWT header is {alg: HS256, typ: JWT}", jwt.get_unverified_header(rs_token) == {"alg": "HS256", "typ": "JWT"})
row = sqlite3.connect(RS_DB).execute("select password_hash, created_at, last_login from users where username='alice_1'").fetchone()
check("password hash is $2b$12$", row[0].startswith("$2b$12$"), row[0][:10])
check("created_at stored as 'YYYY-MM-DD HH:MM:SS'", re.match(r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d$", row[1]) is not None, row[1])
check("last_login stored with microseconds", re.match(r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d{6}$", row[2]) is not None, row[2])
# (b) Python-created DB served by a second Rust server
py_token = requests.Session()
rs2 = start_rust(PY_DB, PORT2); B2 = f"http://127.0.0.1:{PORT2}"
r = requests.post(B2 + "/api/auth/login", json={"username": "alice_1", "password": "password123"})
check("Rust verifies a bcrypt hash created by Python (login)", r.status_code == 200, r.text[:200])
import app.services.auth as pyauth
with contextlib.redirect_stdout(io.StringIO()):
    from app.core.database import SessionLocal
    db = SessionLocal(); u = pyauth.AuthService(db).authenticate_user("alice_1", "password123")
    ptoken = pyauth.AuthService(db).create_access_token(u)
r = requests.get(B2 + "/api/auth/me", headers={"Authorization": f"Bearer {ptoken}"})
check("Rust accepts a JWT issued by Python", r.status_code == 200 and r.json()["username"] == "alice_1", r.text[:200])
r = requests.get(B2 + "/api/auth/users", headers={"Authorization": f"Bearer {ptoken}"})
n_users = sqlite3.connect(PY_DB).execute("select count(*) from users").fetchone()[0]
check(f"Rust reads every Python-written user row (admin list: {n_users} users)", r.status_code == 200 and len(r.json()) == n_users and n_users >= 4, r.text[:200])
rs2.terminate(); rs_proc.terminate()
print(f"phase 2: {f2} failed")
sys.exit(1 if failures or f2 else 0)
