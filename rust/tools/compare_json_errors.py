"""Fuzz Python's json decoder against the Rust re-implementation of its error reporting.
usage: python compare_json_errors.py <path-to-json_err_diff-binary>"""
import json, random, subprocess, sys, tempfile, os
binary = sys.argv[1]
rng = random.Random(3)
seeds = ['{"message": "hello"}', '{"a": [1, 2.5, -3e4, true, false, null, {"b": "c\\n\\u00e9\\ud83d\\ude00"}], "d": {}}', '[1,2,[3,[4]],{"x":[]}]', '"str"', '12', '{"message": "x", "y": 1}', '  {\n "k" : \t "v" \r\n}  ']
alphabet = list('{}[]",:\\ \n\t\rtrufalsenNI-+.eE0123456789abcxyzé\x01\x1f') + ['\\u', '\\ud83d', '\\n', 'null', 'true', 'NaN', 'Infinity', '-Infinity', '"\\x"', '\\u12', '\\uZZZZ', '"', "'"]
cases = list(seeds)
for _ in range(60000):
    s = list(rng.choice(seeds)); k = rng.random()
    for _ in range(rng.randint(1, 3)):
        op = rng.choice(["ins", "del", "rep", "trunc"])
        if not s: break
        i = rng.randrange(len(s) + (op == "ins"))
        if op == "ins": s.insert(i, rng.choice(alphabet))
        elif op == "del": del s[i]
        elif op == "rep": s[i] = rng.choice(alphabet)
        else: s = s[:i]
    cases.append("".join(s))
cases += ["".join(rng.choice(alphabet) for _ in range(rng.randint(0, 12))) for _ in range(20000)]
tmp = tempfile.mktemp(suffix=".json"); json.dump(cases, open(tmp, "w"))
rust = json.loads(subprocess.run([binary, tmp], capture_output=True, text=True, check=True).stdout); os.unlink(tmp)
bad = shown = errs = 0
from collections import Counter
kinds = Counter()
for text, r in zip(cases, rust):
    try: json.loads(text); exp = None
    except json.JSONDecodeError as e: exp = [e.pos, e.msg]; errs += 1
    got = r
    if exp != got:
        bad += 1
        kinds[(exp[1] if exp else None, got[1] if got else None)] += 1
        if shown < 8: shown += 1; print(f"MISMATCH {text!r}\n   python: {exp}\n   rust:   {got}")
for k, n in kinds.most_common(8): print("   ", n, "x", k)
print(f"{len(cases)} inputs ({errs} invalid per Python), {bad} mismatches")
sys.exit(1 if bad else 0)
