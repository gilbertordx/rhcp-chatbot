//! Maps whatever the user typed to a canonical band member / album / song.
//! Python equivalent: `app/knowledge/resolver.py` (`KnowledgeResolver`).
//!
//! Matching order: exact canonical name, then exact alias, then fuzzy matching
//! (typos, swapped letters, sound-alikes) which must score at least 0.6.
//! The knowledge files are YAML (`data/knowledge/{members,albums,songs}.yml`).

use std::fs;
use std::path::Path;

use regex::Regex;
use serde_json::{Map, Value};
use unicode_normalization::{UnicodeNormalization, char::canonical_combining_class};

pub type Canonical = Map<String, Value>;

pub struct KnowledgeResolver {
    members: Vec<Canonical>,
    albums: Vec<Canonical>,
    songs: Vec<Canonical>,
    whitespace: Regex,
    punctuation: Regex,
}

/// Read `key:` (a list of records) from a YAML file. Missing/bad file -> empty list,
/// like the Python (`logger.error(...)` and carry on).
fn load_list(path: &Path, key: &str) -> Vec<Canonical> {
    let Ok(text) = fs::read_to_string(path) else {
        return Vec::new();
    };
    let Ok(doc) = serde_yaml_ng::from_str::<Value>(&text) else {
        return Vec::new();
    };
    doc.get(key)
        .and_then(Value::as_array)
        .map(|a| a.iter().filter_map(|v| v.as_object().cloned()).collect())
        .unwrap_or_default()
}

fn text_field<'a>(record: &'a Canonical, key: &str) -> &'a str {
    record.get(key).and_then(Value::as_str).unwrap_or("")
}

impl KnowledgeResolver {
    pub fn load(knowledge_dir: &Path) -> Self {
        Self {
            members: load_list(&knowledge_dir.join("members.yml"), "members"),
            albums: load_list(&knowledge_dir.join("albums.yml"), "albums"),
            songs: load_list(&knowledge_dir.join("songs.yml"), "songs"),
            whitespace: Regex::new(r"\s+").expect("valid regex"),
            punctuation: Regex::new(r"[^\w\s]").expect("valid regex"),
        }
    }

    /// Lower-case, strip accents ("Björk" -> "bjork"), squeeze spaces, drop punctuation.
    pub fn normalize_span(&self, span: &str) -> String {
        if span.is_empty() {
            return String::new();
        }
        let lowered = span.to_lowercase();
        let decomposed: String = lowered
            .trim()
            .nfd()
            .filter(|c| canonical_combining_class(*c) == 0)
            .collect();
        let squeezed = self.whitespace.replace_all(&decomposed, " ");
        self.punctuation.replace_all(&squeezed, "").into_owned()
    }

    /// How alike are two strings? 1.0 identical ... 0.0 unrelated.
    pub fn calculate_similarity(&self, span: &str, target: &str) -> f64 {
        if span.is_empty() || target.is_empty() {
            return 0.0;
        }
        let a = self.normalize_span(span);
        let b = self.normalize_span(target);
        if a == b {
            return 1.0;
        }
        if a.contains(&b) || b.contains(&a) {
            return 0.8;
        }
        let (ac, bc): (Vec<char>, Vec<char>) = (a.chars().collect(), b.chars().collect());

        // two neighbouring letters swapped ("teh" -> "the")
        if ac.len() == bc.len() && ac.len() >= 3 {
            for i in 0..ac.len() - 1 {
                let mut swapped = ac.clone();
                swapped.swap(i, i + 1);
                if swapped == bc {
                    return 0.6;
                }
            }
        }

        // sounds alike
        let phonetic = |s: &str| {
            let mut out = s.to_string();
            for (from, to) in [
                ("f", "ph"),
                ("c", "k"),
                ("s", "z"),
                ("x", "ks"),
                ("qu", "kw"),
                ("tion", "shun"),
                ("sion", "zhun"),
            ] {
                out = out.replace(from, to);
            }
            out
        };
        if phonetic(&a) == phonetic(&b) {
            return 0.6;
        }

        // one or two letters different
        if ac.len() == bc.len() {
            match ac.iter().zip(&bc).filter(|(x, y)| x != y).count() {
                1 => return 0.7,
                2 => return 0.5,
                _ => {}
            }
        }

        // one letter missing or extra ("fruciante" vs "frusciante")
        if ac.len().abs_diff(bc.len()) == 1 {
            let (shorter, longer) = if ac.len() < bc.len() { (&ac, &bc) } else { (&bc, &ac) };
            for i in 0..longer.len() {
                let mut candidate = longer.clone();
                candidate.remove(i);
                if &candidate == shorter {
                    return 0.7;
                }
            }
        }
        0.0
    }

    /// Shared by members, albums and songs: exact -> alias -> fuzzy.
    fn resolve(&self, records: &[Canonical], span: &str) -> Option<Canonical> {
        let normalized = self.normalize_span(span);
        let aliases_of = |r: &Canonical| -> Vec<String> {
            r.get("aliases")
                .and_then(Value::as_array)
                .map(|a| a.iter().filter_map(|v| v.as_str().map(str::to_string)).collect())
                .unwrap_or_default()
        };

        for r in records {
            if self.normalize_span(text_field(r, "canonical")) == normalized {
                return Some(r.clone());
            }
        }
        for r in records {
            if aliases_of(r)
                .iter()
                .any(|alias| self.normalize_span(alias) == normalized)
            {
                return Some(r.clone());
            }
        }

        let mut best: Option<&Canonical> = None;
        let mut best_score = 0.0;
        for r in records {
            let score = self.calculate_similarity(&normalized, &self.normalize_span(text_field(r, "canonical")));
            if score > best_score {
                best_score = score;
                best = Some(r);
            }
            for alias in aliases_of(r) {
                let score = self.calculate_similarity(&normalized, &self.normalize_span(&alias));
                if score > best_score {
                    best_score = score;
                    best = Some(r);
                }
            }
        }
        if best_score >= 0.6 { best.cloned() } else { None }
    }

    pub fn resolve_member(&self, span: &str) -> Option<Canonical> {
        self.resolve(&self.members, span)
    }

    pub fn resolve_album(&self, span: &str) -> Option<Canonical> {
        self.resolve(&self.albums, span)
    }

    pub fn resolve_song(&self, span: &str) -> Option<Canonical> {
        self.resolve(&self.songs, span)
    }

    /// Try every kind (members first) when no type is given.
    pub fn resolve_entity(&self, span: &str, kind: Option<&str>) -> Option<Canonical> {
        match kind {
            Some("member") => self.resolve_member(span),
            Some("album") => self.resolve_album(span),
            Some("song") => self.resolve_song(span),
            _ => self
                .resolve_member(span)
                .or_else(|| self.resolve_album(span))
                .or_else(|| self.resolve_song(span)),
        }
    }

    pub fn counts(&self) -> (usize, usize, usize) {
        (self.members.len(), self.albums.len(), self.songs.len())
    }
}
