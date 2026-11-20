"""Train with scikit-learn (the ORIGINAL recipe from initializer.train_new_model) and with
`rhcp-chatbot train`, then compare the fitted models.

Vectorizer (vocabulary + idf) must match EXACTLY. The logistic regression is convex, so
when both optimisers run to convergence (tiny tolerance) they reach the same minimum and the
weights/probabilities must agree closely. Also reports the default-tolerance (1e-4) case,
where scikit-learn stops early and the two models legitimately differ a little.

usage: python compare_training.py <repo-root> <rhcp-chatbot-binary> <clf_diff-binary>
"""
import json, os, subprocess, sys, tempfile, time, warnings
import numpy as np
warnings.filterwarnings("ignore")
repo, binary, clf_diff = sys.argv[1:4]
os.chdir(repo); sys.path.insert(0, repo); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from app.chatbot.initializer import tokenize
from _cases import make_cases

texts, intents = [], []
for fn in ("base-corpus.json", "rhcp-corpus-v2.json"):
    for item in json.load(open(f"app/chatbot/data/training/{fn}", encoding="utf-8"))["data"]:
        if item["intent"] != "None":
            for u in item["utterances"]: texts.append(u); intents.append(item["intent"])
print(f"{len(texts)} training samples")

def fit(**lr):
    p = Pipeline([("tfidf", TfidfVectorizer(tokenizer=tokenize, ngram_range=(1, 3), max_features=5000, min_df=1, max_df=0.95)),
                  ("classifier", LogisticRegression(random_state=42, C=1.0, **lr))])
    t = time.time(); p.fit(texts, intents); return p, time.time() - t

def rust_train(tol, max_iter):
    out = tempfile.mktemp(suffix=".json")
    t = time.time()
    r = subprocess.run([binary, "train", "--out", out, "--tol", str(tol), "--max-iter", str(max_iter)], capture_output=True, text=True)
    if r.returncode: print(r.stdout[-800:], r.stderr[-800:]); sys.exit(2)
    return json.load(open(out)), out, time.time() - t, r.stdout.strip().splitlines()[-2]

cases = [c.lower() for c in make_cases(repo)[:30000]]
def rust_probs(model_path):
    tmp = tempfile.mktemp(suffix=".json"); json.dump(cases, open(tmp, "w"))
    return np.array(json.loads(subprocess.run([clf_diff, model_path, tmp], capture_output=True, text=True, check=True).stdout))

ok = True
# ---------- converged ----------
sk, sk_t = fit(max_iter=20000, tol=1e-10)
model, path, rs_t, summary = rust_train(1e-9, 20000)
tf, lr = sk.named_steps["tfidf"], sk.named_steps["classifier"]
vocab_sk = [None] * len(tf.vocabulary_)
for term, i in tf.vocabulary_.items(): vocab_sk[i] = term
print(f"\nconverged fits  (sklearn {sk_t:.1f}s, rust {rs_t:.1f}s)  rust: {summary}")
same_vocab = vocab_sk == model["vocabulary"]
print("vocabulary identical (same terms, same order):", same_vocab, f"({len(vocab_sk)} terms)")
idf_diff = np.max(np.abs(tf.idf_ - np.array(model["idf"]))) if same_vocab else float("nan")
print(f"idf max |diff|: {idf_diff:.2e}")
same_classes = [str(c) for c in lr.classes_] == model["classes"]
print("classes identical:", same_classes)
coef_diff = np.max(np.abs(lr.coef_ - np.array(model["coef"]))) if same_vocab and same_classes else float("nan")
icpt_diff = np.max(np.abs(lr.intercept_ - np.array(model["intercept"]))) if same_classes else float("nan")
print(f"coef max |diff|: {coef_diff:.2e}   intercept max |diff|: {icpt_diff:.2e}")
exp = sk.predict_proba(cases); got = rust_probs(path)
d = np.abs(exp - got)
print(f"predict_proba on {len(cases)} inputs: max |diff| {d.max():.2e}, mean {d.mean():.2e}, top-1 identical {(exp.argmax(1) == got.argmax(1)).mean()*100:.3f}%")
ok &= same_vocab and same_classes and idf_diff < 1e-12 and d.max() < 1e-4 and (exp.argmax(1) == got.argmax(1)).all()

# ---------- default tolerance ----------
sk0, _ = fit(max_iter=1000)
model0, path0, _, summary0 = rust_train(1e-4, 1000)
exp0 = sk0.predict_proba(cases); got0 = rust_probs(path0)
d0 = np.abs(exp0 - got0)
print(f"\ndefault tolerance (1e-4: scikit-learn's own default, stops early)  rust: {summary0}")
print(f"  sklearn used {sk0.named_steps['classifier'].n_iter_[0]} iterations")
print(f"  predict_proba max |diff| {d0.max():.2e}, mean {d0.mean():.2e}; top-1 identical {(exp0.argmax(1) == got0.argmax(1)).mean()*100:.1f}%")
print(f"  share of inputs passing the 0.60 gate: sklearn {(exp0.max(1)>=0.6).mean()*100:.2f}%  rust {(got0.max(1)>=0.6).mean()*100:.2f}%")
print("\nPASS" if ok else "\nFAIL")
sys.exit(0 if ok else 1)
