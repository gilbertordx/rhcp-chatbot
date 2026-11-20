"""Build the fact database with the ORIGINAL scripts/build_fts.py and with `rhcp-chatbot build-fts`
and require identical rows (and identical to the committed database).
usage: python compare_fts.py <repo-root> <rhcp-chatbot-binary>"""
import os, sqlite3, subprocess, sys, tempfile
repo, binary = sys.argv[1:3]; os.chdir(repo)
work = tempfile.mkdtemp()
subprocess.run([sys.executable, "-W", "ignore", "scripts/build_fts.py", "--db-path", f"{work}/py.sqlite", "--knowledge-dir", "data/knowledge"], capture_output=True, check=True)
subprocess.run([binary, "build-fts", "--db-path", f"{work}/rs.sqlite", "--knowledge-dir", "data/knowledge"], capture_output=True, check=True)
q = "SELECT id,type,canonical,field,value,year,source FROM facts ORDER BY id"
rows = lambda p: sqlite3.connect(p).execute(q).fetchall()
py, rs, committed = rows(f"{work}/py.sqlite"), rows(f"{work}/rs.sqlite"), rows("data/rhcp_fts.sqlite")
hits = lambda p: [len(sqlite3.connect(p).execute("SELECT rowid FROM facts_fts WHERE facts_fts MATCH ?", (t,)).fetchall()) for t in ["flea", "bass", "californication", "1991", "funk"]]
print(f"facts: python {len(py)}, rust {len(rs)}, committed {len(committed)}")
ok = py == rs == committed and hits(f"{work}/py.sqlite") == hits(f"{work}/rs.sqlite")
print("PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
