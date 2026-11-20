"""Compare NLTK (the original Python behaviour) with the Rust text pipeline.

For every input string both sides produce:
  * `words`: nltk.word_tokenize(text)               (sentence split + word tokenize)
  * `stems`: the vectorizer's tokenize(text)         (lower-case, tokenize, Porter-stem)
and they must be identical.

usage: python compare_nlp.py <repo-root> <path-to-nlp_diff-binary>
Needs: pip install nltk ; NLTK punkt data in ~/nltk_data (see `rhcp-chatbot setup-nltk`).
"""
import json, os, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize

repo, binary = sys.argv[1:3]
stemmer = PorterStemmer()


def py_tokenize(text):                      # copied from app/chatbot/initializer.py
    return [stemmer.stem(t) for t in word_tokenize(text.lower())]


from _cases import make_cases
cases = make_cases(repo)
print(f"{len(cases)} inputs")
tmp = tempfile.mktemp(suffix=".json")
json.dump(cases, open(tmp, "w"))
rust = json.loads(subprocess.run([binary, tmp], capture_output=True, text=True, check=True, env={**os.environ}).stdout)
os.unlink(tmp)

bad = {"words": 0, "stems": 0}
shown = 0
for text, r in zip(cases, rust):
    exp_words, exp_stems = word_tokenize(text), py_tokenize(text)
    for kind, exp in (("words", exp_words), ("stems", exp_stems)):
        if exp != r[kind]:
            bad[kind] += 1
            if shown < 8:
                shown += 1
                print(f"MISMATCH [{kind}] input={text!r}\n   nltk: {exp}\n   rust: {r[kind]}")
print(f"word_tokenize mismatches: {bad['words']} / {len(cases)}")
print(f"tokenize+stem mismatches: {bad['stems']} / {len(cases)}")
sys.exit(1 if any(bad.values()) else 0)
