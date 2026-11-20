"""Compare scikit-learn's predict_proba (the saved .joblib pipeline, i.e. the
ORIGINAL behaviour) with the Rust classifier on the same inputs.

usage: python compare_classifier.py <repo-root> <path-to-clf_diff-binary>
"""
import json, os, subprocess, sys, tempfile, warnings
import numpy as np
import joblib

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
repo, binary = sys.argv[1:3]
sys.path.insert(0, repo)
from app.chatbot import initializer  # noqa: F401  (pickle needs initializer.tokenize)
from _cases import make_cases

pipeline = joblib.load(os.path.join(repo, "app/models/logistic_regression_classifier.joblib"))
cases = make_cases(repo)
# the app lower-cases before classifying (inference.classify: message.lower())
texts = [c.lower() for c in cases]
print(f"{len(texts)} inputs, {len(pipeline.classes_)} classes")

expected = pipeline.predict_proba(texts)
tmp = tempfile.mktemp(suffix=".json")
json.dump(texts, open(tmp, "w"))
model_json = os.path.join(repo, "data/models/classifier_weights.json")
got = np.array(json.loads(subprocess.run([binary, model_json, tmp], capture_output=True, text=True, check=True).stdout))
os.unlink(tmp)

diff = np.abs(expected - got)
same_top = (expected.argmax(1) == got.argmax(1))
# exact label order too (ties matter to `sorted`)
print(f"max |probability difference| over all inputs and classes: {diff.max():.3e}")
print(f"mean difference: {diff.mean():.3e}")
print(f"top-1 class identical: {same_top.sum()} / {len(texts)}")
gate = lambda p: (p.max(1) >= 0.60)
print(f"inputs passing the 0.60 gate: sklearn {int(gate(expected).sum())}, rust {int(gate(got).sum())}")
ok = diff.max() < 1e-9 and same_top.all() and (gate(expected) == gate(got)).all()
print("PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
