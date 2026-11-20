//! Training the intent classifier. Python equivalent: `train_new_model` in
//! `app/chatbot/initializer.py`:
//!
//! ```python
//! Pipeline([
//!   ("tfidf", TfidfVectorizer(tokenizer=tokenize, ngram_range=(1, 3),
//!                             max_features=5000, min_df=1, max_df=0.95)),
//!   ("classifier", LogisticRegression(random_state=42, max_iter=1000, C=1.0)),
//! ]).fit(texts, intents)
//! ```
//!
//! Two steps, both reproduced here:
//!
//! 1. **Vectorizer fit**: count every 1-, 2- and 3-gram, drop ones that appear in
//!    more than 95% of the documents, keep the 5000 most frequent, number the kept
//!    terms alphabetically, and compute `idf = ln((1 + n) / (1 + df)) + 1`. This is
//!    deterministic and matches scikit-learn exactly.
//! 2. **Logistic regression fit**: minimise
//!    `sum(-log p[correct class]) + (1 / 2C) * sum(weights^2)` with L-BFGS (a
//!    standard quasi-Newton optimiser). The problem is convex, so any good optimiser
//!    reaches the same minimum; scikit-learn stops early (at tolerance 1e-4) so a
//!    default-tolerance model differs slightly from one trained to convergence.
//!
//! Verified against scikit-learn in `tools/compare_training.py`.

use std::collections::{BTreeMap, HashMap};

use super::classifier::{ModelFile, VectorizerSettings};
use super::tokenizer::TextAnalyzer;

pub struct TrainConfig {
    pub max_features: usize,
    pub max_df: f64,
    pub min_df: usize,
    /// Inverse regularisation strength (scikit-learn `C`).
    pub c: f64,
    pub max_iter: usize,
    /// Stop when the largest gradient entry (of the *per-sample average* loss, like
    /// scikit-learn) falls below this.
    pub tol: f64,
}

impl Default for TrainConfig {
    fn default() -> Self {
        Self {
            max_features: 5000,
            max_df: 0.95,
            min_df: 1,
            c: 1.0,
            max_iter: 1000,
            tol: 1e-4,
        }
    }
}

/// n-grams of 1..=3 tokens, unigrams first (scikit-learn `_word_ngrams`).
fn ngrams(tokens: &[String]) -> Vec<String> {
    let mut out: Vec<String> = tokens.to_vec();
    for n in 2..=3usize {
        if tokens.len() >= n {
            out.extend(tokens.windows(n).map(|w| w.join(" ")));
        }
    }
    out
}

/// A sparse row: `(column, value)` pairs in ascending column order.
type Row = Vec<(usize, f64)>;

struct FittedVectorizer {
    vocabulary: Vec<String>,
    idf: Vec<f64>,
}

fn fit_vectorizer(docs: &[Vec<String>], cfg: &TrainConfig) -> FittedVectorizer {
    let n_docs = docs.len();
    // term -> (document frequency, total count); BTreeMap keeps terms alphabetical
    let mut stats: BTreeMap<&str, (usize, usize)> = BTreeMap::new();
    for doc in docs {
        let mut seen_in_doc: HashMap<&str, usize> = HashMap::new();
        for gram in doc {
            *seen_in_doc.entry(gram.as_str()).or_insert(0) += 1;
        }
        for (term, count) in seen_in_doc {
            let e = stats.entry(term).or_insert((0, 0));
            e.0 += 1;
            e.1 += count;
        }
    }

    let max_doc_count = cfg.max_df * n_docs as f64;
    let mut kept: Vec<(&str, usize, usize)> = stats
        .into_iter()
        .filter(|(_, (df, _))| (*df as f64) <= max_doc_count && *df >= cfg.min_df)
        .map(|(t, (df, tf))| (t, df, tf))
        .collect();

    if kept.len() > cfg.max_features {
        // keep the most frequent terms; ties broken by alphabetical order (scikit-learn's
        // tie order comes from an unstable sort, so it is only guaranteed when no ties
        // straddle the cut-off)
        let mut by_freq: Vec<usize> = (0..kept.len()).collect();
        by_freq.sort_by(|&a, &b| kept[b].2.cmp(&kept[a].2).then(a.cmp(&b)));
        let mut keep_mask = vec![false; kept.len()];
        for &i in by_freq.iter().take(cfg.max_features) {
            keep_mask[i] = true;
        }
        let mut i = 0;
        kept.retain(|_| {
            let k = keep_mask[i];
            i += 1;
            k
        });
    }

    let vocabulary: Vec<String> = kept.iter().map(|(t, _, _)| t.to_string()).collect();
    let idf: Vec<f64> = kept
        .iter()
        .map(|(_, df, _)| ((1.0 + n_docs as f64) / (1.0 + *df as f64)).ln() + 1.0)
        .collect();
    FittedVectorizer { vocabulary, idf }
}

fn transform(docs: &[Vec<String>], v: &FittedVectorizer) -> Vec<Row> {
    let index: HashMap<&str, usize> = v.vocabulary.iter().enumerate().map(|(i, t)| (t.as_str(), i)).collect();
    docs.iter()
        .map(|doc| {
            let mut counts: BTreeMap<usize, f64> = BTreeMap::new();
            for gram in doc {
                if let Some(&col) = index.get(gram.as_str()) {
                    *counts.entry(col).or_insert(0.0) += 1.0;
                }
            }
            let mut row: Row = counts.into_iter().map(|(col, c)| (col, c * v.idf[col])).collect();
            let norm = row.iter().map(|(_, x)| x * x).sum::<f64>().sqrt();
            if norm != 0.0 {
                row.iter_mut().for_each(|(_, x)| *x /= norm);
            }
            row
        })
        .collect()
}

/// Loss and gradient of `mean(-log p[y]) + (1/(2 C n)) * ||W||^2` at `params`.
/// `params` = class-major weights (`k * n_features`) then `k` intercepts.
fn objective(rows: &[Row], labels: &[usize], k: usize, f: usize, c: f64, params: &[f64], grad: &mut [f64]) -> f64 {
    let n = rows.len() as f64;
    grad.iter_mut().for_each(|g| *g = 0.0);
    let (w, b) = params.split_at(k * f);
    let mut loss = 0.0;
    let mut scores = vec![0.0; k];
    for (row, &y) in rows.iter().zip(labels) {
        for class in 0..k {
            let wc = &w[class * f..(class + 1) * f];
            scores[class] = row.iter().fold(0.0, |acc, (col, x)| acc + x * wc[*col]) + b[class];
        }
        let max = scores.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
        let total: f64 = scores.iter().map(|s| (s - max).exp()).sum();
        let log_total = total.ln() + max;
        loss += log_total - scores[y];
        for class in 0..k {
            let p = (scores[class] - max).exp() / total;
            let residual = p - if class == y { 1.0 } else { 0.0 };
            let gc = &mut grad[class * f..(class + 1) * f];
            for (col, x) in row {
                gc[*col] += residual * x;
            }
            grad[k * f + class] += residual;
        }
    }
    let reg = 0.5 / (c * n);
    let penalty: f64 = w.iter().map(|x| x * x).sum::<f64>() * reg;
    for (g, wi) in grad[..k * f].iter_mut().zip(w) {
        *g = *g / n + 2.0 * reg * wi;
    }
    grad[k * f..].iter_mut().for_each(|g| *g /= n);
    loss / n + penalty
}

/// Limited-memory BFGS with a backtracking (Armijo) line search.
fn lbfgs(mut x: Vec<f64>, cfg: &TrainConfig, mut eval: impl FnMut(&[f64], &mut [f64]) -> f64) -> (Vec<f64>, usize) {
    const MEMORY: usize = 10;
    let dim = x.len();
    let mut g = vec![0.0; dim];
    let mut fx = eval(&x, &mut g);
    let dot = |a: &[f64], b: &[f64]| a.iter().zip(b).map(|(p, q)| p * q).sum::<f64>();

    let mut history: Vec<(Vec<f64>, Vec<f64>, f64)> = Vec::new(); // (s, y, 1/(y.s))
    let mut iterations = 0;
    for iter in 0..cfg.max_iter {
        iterations = iter;
        if g.iter().fold(0.0_f64, |m, v| m.max(v.abs())) <= cfg.tol {
            break;
        }
        // two-loop recursion: direction = -H * g
        let mut q = g.clone();
        let mut alphas = vec![0.0; history.len()];
        for i in (0..history.len()).rev() {
            let (s, y, rho) = &history[i];
            alphas[i] = rho * dot(s, &q);
            q.iter_mut().zip(y).for_each(|(qi, yi)| *qi -= alphas[i] * yi);
        }
        let gamma = history
            .last()
            .map(|(s, y, _)| dot(s, y) / dot(y, y))
            .unwrap_or(1.0 / dot(&g, &g).sqrt().max(1e-12));
        q.iter_mut().for_each(|qi| *qi *= gamma);
        for i in 0..history.len() {
            let (s, y, rho) = &history[i];
            let beta = rho * dot(y, &q);
            q.iter_mut().zip(s).for_each(|(qi, si)| *qi += (alphas[i] - beta) * si);
        }
        let direction: Vec<f64> = q.iter().map(|v| -v).collect();
        let slope = dot(&g, &direction);
        if slope >= 0.0 {
            history.clear(); // not a descent direction: restart from steepest descent
            continue;
        }

        // backtracking line search
        let mut step = 1.0;
        let mut x_new = vec![0.0; dim];
        let mut g_new = vec![0.0; dim];
        let mut f_new;
        let mut tries = 0;
        loop {
            for i in 0..dim {
                x_new[i] = x[i] + step * direction[i];
            }
            f_new = eval(&x_new, &mut g_new);
            if f_new <= fx + 1e-4 * step * slope || tries >= 40 {
                break;
            }
            step *= 0.5;
            tries += 1;
        }
        if tries >= 40 && f_new > fx {
            break; // no progress possible
        }

        let s: Vec<f64> = x_new.iter().zip(&x).map(|(a, b)| a - b).collect();
        let y: Vec<f64> = g_new.iter().zip(&g).map(|(a, b)| a - b).collect();
        let sy = dot(&s, &y);
        let relative_drop = (fx - f_new).abs() / fx.abs().max(f_new.abs()).max(1.0);
        x = x_new;
        g = g_new.clone();
        fx = f_new;
        if sy > 1e-12 {
            if history.len() == MEMORY {
                history.remove(0);
            }
            history.push((s, y, 1.0 / sy));
        }
        if relative_drop <= 64.0 * f64::EPSILON {
            break; // scipy's `ftol`: the objective stopped changing
        }
    }
    (x, iterations)
}

pub struct TrainReport {
    pub samples: usize,
    pub classes: usize,
    pub terms: usize,
    pub iterations: usize,
    pub train_accuracy: f64,
}

/// Fit the whole pipeline. `texts[i]` has intent `intents[i]`.
pub fn train(analyzer: &TextAnalyzer, texts: &[&str], intents: &[&str], cfg: &TrainConfig) -> (ModelFile, TrainReport) {
    let docs: Vec<Vec<String>> = texts.iter().map(|t| ngrams(&analyzer.tokenize_and_stem(t))).collect();
    let vectorizer = fit_vectorizer(&docs, cfg);
    let rows = transform(&docs, &vectorizer);

    let mut classes: Vec<String> = intents.iter().map(|s| s.to_string()).collect();
    classes.sort();
    classes.dedup();
    let labels: Vec<usize> = intents
        .iter()
        .map(|i| classes.binary_search(&i.to_string()).expect("class exists"))
        .collect();
    let (k, f) = (classes.len(), vectorizer.vocabulary.len());

    let (params, iterations) = lbfgs(vec![0.0; k * f + k], cfg, |p, g| {
        objective(&rows, &labels, k, f, cfg.c, p, g)
    });

    // training accuracy, as a sanity figure
    let (w, b) = params.split_at(k * f);
    let correct = rows
        .iter()
        .zip(&labels)
        .filter(|(row, y)| {
            let best = (0..k)
                .map(|c| (c, row.iter().fold(0.0, |a, (col, x)| a + x * w[c * f + *col]) + b[c]))
                .max_by(|a, b| a.1.partial_cmp(&b.1).unwrap())
                .map(|(c, _)| c);
            best == Some(**y)
        })
        .count();

    let coef: Vec<Vec<f64>> = (0..k).map(|c| w[c * f..(c + 1) * f].to_vec()).collect();
    let model = ModelFile {
        format: "rhcp-classifier-v1".into(),
        source: "trained by rhcp-chatbot".into(),
        vectorizer: VectorizerSettings::standard(),
        classes,
        vocabulary: vectorizer.vocabulary,
        idf: vectorizer.idf,
        intercept: b.to_vec(),
        coef,
    };
    let report = TrainReport {
        samples: texts.len(),
        classes: k,
        terms: f,
        iterations,
        train_accuracy: correct as f64 / texts.len() as f64,
    };
    (model, report)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn grams(words: &[&str]) -> Vec<String> {
        ngrams(&words.iter().map(|w| w.to_string()).collect::<Vec<_>>())
    }

    #[test]
    fn ngrams_are_unigrams_then_bigrams_then_trigrams() {
        assert_eq!(grams(&["a", "b", "c"]), ["a", "b", "c", "a b", "b c", "a b c"]);
        assert_eq!(grams(&["a"]), ["a"]);
        assert!(grams(&[]).is_empty());
    }

    #[test]
    fn vocabulary_is_alphabetical_and_idf_uses_the_smoothed_formula() {
        let docs: Vec<Vec<String>> = [vec!["b", "a"], vec!["b", "c"], vec!["b"]]
            .into_iter()
            .map(|d| d.into_iter().map(String::from).collect())
            .collect();
        // max_df = 1.0 so "b" (in all 3 documents) is kept
        let cfg = TrainConfig {
            max_df: 1.0,
            ..Default::default()
        };
        let v = fit_vectorizer(&docs, &cfg);
        assert_eq!(v.vocabulary, ["a", "b", "c"]);
        // idf = ln((1 + n) / (1 + df)) + 1
        assert!((v.idf[0] - (4.0_f64 / 2.0).ln() - 1.0).abs() < 1e-15); // "a": df 1
        assert!((v.idf[1] - 1.0).abs() < 1e-15); // "b": df 3 -> ln(1) + 1
    }

    #[test]
    fn terms_in_more_than_max_df_of_documents_are_dropped() {
        let docs: Vec<Vec<String>> = (0..20)
            .map(|i| vec!["common".to_string(), format!("rare{i}")])
            .collect();
        let v = fit_vectorizer(&docs, &TrainConfig::default()); // max_df 0.95
        assert!(!v.vocabulary.contains(&"common".to_string()));
        assert_eq!(v.vocabulary.len(), 20);
    }

    #[test]
    fn the_optimiser_learns_a_separable_toy_problem() {
        // two classes, two features: class 0 uses feature 0, class 1 uses feature 1
        let rows: Vec<Row> = vec![vec![(0, 1.0)], vec![(0, 1.0)], vec![(1, 1.0)], vec![(1, 1.0)]];
        let labels = [0usize, 0, 1, 1];
        let cfg = TrainConfig {
            tol: 1e-8,
            ..Default::default()
        };
        let (params, _) = lbfgs(vec![0.0; 2 * 2 + 2], &cfg, |p, g| {
            objective(&rows, &labels, 2, 2, cfg.c, p, g)
        });
        let (w, _b) = params.split_at(4);
        assert!(
            w[0] > w[2] && w[3] > w[1],
            "weights should favour the matching class: {w:?}"
        );
    }

    #[test]
    fn the_gradient_matches_a_numerical_estimate() {
        let rows: Vec<Row> = vec![vec![(0, 0.6), (1, 0.8)], vec![(1, 1.0)], vec![(0, 1.0)]];
        let labels = [0usize, 1, 1];
        let params: Vec<f64> = (0..(2 * 2 + 2)).map(|i| 0.1 * i as f64 - 0.2).collect();
        let mut grad = vec![0.0; params.len()];
        objective(&rows, &labels, 2, 2, 1.0, &params, &mut grad);
        for i in 0..params.len() {
            let (mut hi, mut lo) = (params.clone(), params.clone());
            hi[i] += 1e-6;
            lo[i] -= 1e-6;
            let mut scratch = vec![0.0; params.len()];
            let numeric = (objective(&rows, &labels, 2, 2, 1.0, &hi, &mut scratch)
                - objective(&rows, &labels, 2, 2, 1.0, &lo, &mut scratch))
                / 2e-6;
            assert!(
                (numeric - grad[i]).abs() < 1e-7,
                "gradient {i}: analytic {} vs numeric {numeric}",
                grad[i]
            );
        }
    }
}
