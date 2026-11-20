//! The intent classifier: TF-IDF features + multinomial logistic regression.
//!
//! Python equivalent: the scikit-learn `Pipeline([("tfidf", TfidfVectorizer(...)),
//! ("classifier", LogisticRegression(...))])` that `initializer.py` loaded with
//! `joblib` and called as `predict_proba`. A Python pickle cannot be read from
//! Rust, so `tools/export_model.py` writes the fitted numbers to JSON and this
//! module reproduces the three steps scikit-learn performed:
//!
//! 1. **n-grams**: the stemmed tokens, then every run of 2 and of 3 tokens
//!    joined by a space (`"tell me about"`), in that order.
//! 2. **TF-IDF**: count each n-gram that is in the vocabulary, multiply by its
//!    IDF weight, then scale the vector to length 1 (L2 norm).
//! 3. **Softmax regression**: one score per class = dot product with that
//!    class's weights + intercept, turned into probabilities with softmax.
//!
//! Sums are accumulated in the same order scikit-learn uses (ascending column),
//! so results match to ~1e-15.

use std::collections::HashMap;
use std::fs;
use std::path::Path;

use anyhow::{Context, Result, bail, ensure};
use serde::{Deserialize, Serialize};

use super::tokenizer::TextAnalyzer;

/// The on-disk format written by `tools/export_model.py` (and by `train`).
#[derive(Serialize, Deserialize)]
pub struct ModelFile {
    pub format: String,
    #[serde(default)]
    pub source: String,
    /// Settings this code implements; loading refuses anything else.
    pub vectorizer: VectorizerSettings,
    pub classes: Vec<String>,
    /// Column `i` of the feature matrix is the n-gram `vocabulary[i]`.
    pub vocabulary: Vec<String>,
    pub idf: Vec<f64>,
    pub intercept: Vec<f64>,
    /// `coef[class][column]`
    pub coef: Vec<Vec<f64>>,
}

#[derive(Serialize, Deserialize, PartialEq, Debug, Clone)]
pub struct VectorizerSettings {
    pub ngram_range: [usize; 2],
    pub norm: String,
    pub use_idf: bool,
    pub smooth_idf: bool,
    pub sublinear_tf: bool,
    pub lowercase: bool,
}

impl VectorizerSettings {
    pub fn standard() -> Self {
        Self {
            ngram_range: [1, 3],
            norm: "l2".into(),
            use_idf: true,
            smooth_idf: true,
            sublinear_tf: false,
            lowercase: true,
        }
    }
}

/// Write a model as compact JSON (creating the folder if needed).
pub fn save_model(model: &ModelFile, path: &Path) -> Result<()> {
    if let Some(dir) = path.parent() {
        fs::create_dir_all(dir)?;
    }
    fs::write(path, serde_json::to_string(model)?).with_context(|| format!("writing {}", path.display()))
}

pub struct Classifier {
    classes: Vec<String>,
    vocabulary: HashMap<String, usize>,
    idf: Vec<f64>,
    intercept: Vec<f64>,
    /// Row-major `classes x terms`, so one class's weights are contiguous.
    coef: Vec<f64>,
    n_terms: usize,
}

impl Classifier {
    pub fn load(path: &Path) -> Result<Self> {
        let text = fs::read_to_string(path).with_context(|| format!("reading model {}", path.display()))?;
        let file: ModelFile =
            serde_json::from_str(&text).with_context(|| format!("parsing model {}", path.display()))?;
        Self::from_file(file)
    }

    pub fn from_file(file: ModelFile) -> Result<Self> {
        ensure!(
            file.format == "rhcp-classifier-v1",
            "unknown model format {:?}",
            file.format
        );
        if file.vectorizer != VectorizerSettings::standard() {
            bail!(
                "model uses vectorizer settings this code does not implement: {:?}",
                file.vectorizer
            );
        }
        let n_terms = file.vocabulary.len();
        ensure!(
            file.idf.len() == n_terms,
            "idf length {} != vocabulary {}",
            file.idf.len(),
            n_terms
        );
        ensure!(file.coef.len() == file.classes.len(), "coef rows != classes");
        ensure!(
            file.intercept.len() == file.classes.len(),
            "intercept length != classes"
        );
        ensure!(
            file.coef.iter().all(|row| row.len() == n_terms),
            "a coef row has the wrong length"
        );

        let vocabulary = file
            .vocabulary
            .into_iter()
            .enumerate()
            .map(|(i, term)| (term, i))
            .collect();
        Ok(Self {
            classes: file.classes,
            vocabulary,
            idf: file.idf,
            intercept: file.intercept,
            coef: file.coef.into_iter().flatten().collect(),
            n_terms,
        })
    }

    pub fn classes(&self) -> &[String] {
        &self.classes
    }

    /// All 1-, 2- and 3-grams of `tokens` (scikit-learn `_word_ngrams`).
    fn ngrams(tokens: &[String]) -> Vec<String> {
        let mut out: Vec<String> = tokens.to_vec();
        for n in 2..=3usize {
            if tokens.len() >= n {
                for window in tokens.windows(n) {
                    out.push(window.join(" "));
                }
            }
        }
        out
    }

    /// TF-IDF vector as `(column, value)` pairs in ascending column order.
    pub fn vectorize(&self, analyzer: &TextAnalyzer, text: &str) -> Vec<(usize, f64)> {
        let tokens = analyzer.tokenize_and_stem(text);
        let mut counts: HashMap<usize, f64> = HashMap::new();
        for gram in Self::ngrams(&tokens) {
            if let Some(&col) = self.vocabulary.get(&gram) {
                *counts.entry(col).or_insert(0.0) += 1.0;
            }
        }
        let mut row: Vec<(usize, f64)> = counts
            .into_iter()
            .map(|(col, count)| (col, count * self.idf[col]))
            .collect();
        row.sort_by_key(|(col, _)| *col);

        let sum_sq: f64 = row.iter().map(|(_, v)| v * v).sum();
        let norm = sum_sq.sqrt();
        if norm != 0.0 {
            for (_, v) in row.iter_mut() {
                *v /= norm;
            }
        }
        row
    }

    /// Probability of every class, in `classes()` order.
    pub fn predict_proba(&self, analyzer: &TextAnalyzer, text: &str) -> Vec<f64> {
        let row = self.vectorize(analyzer, text);
        let mut scores: Vec<f64> = (0..self.classes.len())
            .map(|class| {
                let weights = &self.coef[class * self.n_terms..(class + 1) * self.n_terms];
                let dot: f64 = row.iter().fold(0.0, |acc, (col, v)| acc + v * weights[*col]);
                dot + self.intercept[class]
            })
            .collect();
        // softmax, shifted by the max for numerical stability
        let max = scores.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
        let mut total = 0.0;
        for s in scores.iter_mut() {
            *s = (*s - max).exp();
            total += *s;
        }
        for s in scores.iter_mut() {
            *s /= total;
        }
        scores
    }

    /// `(label, probability)` sorted best first (Python: `get_classifications`).
    /// Ties keep class order, like Python's stable `sorted(..., reverse=True)`.
    pub fn classifications(&self, analyzer: &TextAnalyzer, text: &str) -> Vec<(String, f64)> {
        let probs = self.predict_proba(analyzer, text);
        let mut pairs: Vec<(String, f64)> = self.classes.iter().cloned().zip(probs).collect();
        pairs.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
        pairs
    }
}
