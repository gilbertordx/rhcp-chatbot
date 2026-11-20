"""Export the saved scikit-learn pipeline (a .joblib pickle) to plain JSON.

Rust cannot unpickle a Python object, so this is the one-way bridge between the
old model file and the Rust app. It writes everything inference needs:
  classes, vocabulary (term -> column), idf, coef (classes x terms), intercept
plus the vectorizer settings (so Rust can check it implements the same ones).

usage: python export_model.py <repo-root> [model.joblib] [out.json]
"""
import json, sys, warnings
import joblib

warnings.filterwarnings("ignore")
root = sys.argv[1]
model_path = sys.argv[2] if len(sys.argv) > 2 else f"{root}/app/models/logistic_regression_classifier.joblib"
out_path = sys.argv[3] if len(sys.argv) > 3 else f"{root}/data/models/classifier_weights.json"
sys.path.insert(0, root)
from app.chatbot import initializer  # noqa: F401  (the pickle refers to initializer.tokenize)

pipeline = joblib.load(model_path)
tfidf, clf = pipeline.named_steps["tfidf"], pipeline.named_steps["classifier"]
assert tfidf.ngram_range == (1, 3) and tfidf.norm == "l2" and tfidf.use_idf and tfidf.smooth_idf
assert not tfidf.sublinear_tf and not tfidf.binary and tfidf.lowercase and tfidf.stop_words is None
assert clf.coef_.shape[0] == len(clf.classes_) > 2, "expected a multinomial (softmax) classifier"

vocab_by_index = [None] * len(tfidf.vocabulary_)
for term, index in tfidf.vocabulary_.items():
    vocab_by_index[int(index)] = term

payload = {
    "format": "rhcp-classifier-v1",
    "source": model_path.split("/")[-1],
    "vectorizer": {"ngram_range": [1, 3], "norm": "l2", "use_idf": True, "smooth_idf": True, "sublinear_tf": False, "lowercase": True},
    "classes": [str(c) for c in clf.classes_],
    "vocabulary": vocab_by_index,          # column i is the term vocabulary[i]
    "idf": [float(x) for x in tfidf.idf_],
    "intercept": [float(x) for x in clf.intercept_],
    "coef": [[float(x) for x in row] for row in clf.coef_],
}
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
print(f"wrote {out_path}: {len(payload['classes'])} classes x {len(vocab_by_index)} terms")
