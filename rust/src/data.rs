//! Loading the static knowledge files and the training corpora.
//!
//! Python equivalent: the loading code in `app/chatbot/initializer.py`.
//! The band and album records are kept as raw JSON (`serde_json::Value`) rather
//! than fixed structs, because the app copies whole records into its answers and
//! different records have different optional keys (`periods`, `deathDate`, ...).

use std::fs;
use std::path::Path;

use anyhow::Context;
use serde::Deserialize;
use serde_json::{Map, Value};

/// `band-info.json` + `discography.json`.
#[derive(Debug, Clone, Default)]
pub struct StaticData {
    pub band_info: Option<Value>,
    pub discography: Option<Value>,
}

impl StaticData {
    /// Missing or unreadable files are reported and skipped, not fatal
    /// ("Chatbot will operate with limited functionality").
    pub fn load(band_info_path: &Path, discography_path: &Path) -> Self {
        let read = |path: &Path, label: &str| -> Option<Value> {
            match fs::read_to_string(path) {
                Ok(text) => match serde_json::from_str(&text) {
                    Ok(v) => {
                        println!("Loaded static data: {label}");
                        Some(v)
                    }
                    Err(e) => {
                        println!("Error loading {}: {e}", path.display());
                        None
                    }
                },
                Err(_) => {
                    println!("Warning: Static data file {} not found", path.display());
                    None
                }
            }
        };
        Self {
            band_info: read(band_info_path, "bandInfo"),
            discography: read(discography_path, "discography"),
        }
    }

    /// `static_data.get("bandInfo", {}).get(key, [])` as a list of JSON objects.
    pub fn band_list(&self, key: &str) -> Vec<&Map<String, Value>> {
        list_of_objects(self.band_info.as_ref(), key)
    }

    pub fn album_list(&self, key: &str) -> Vec<&Map<String, Value>> {
        list_of_objects(self.discography.as_ref(), key)
    }

    /// Python `validate_static_data`: human-readable problems, empty if fine.
    pub fn validation_issues(&self) -> Vec<String> {
        let mut issues = Vec::new();
        if self.band_info.is_none() && self.discography.is_none() {
            issues.push("No static data provided".to_string());
            return issues;
        }
        match &self.band_info {
            None => issues.push("bandInfo not found in static data".into()),
            Some(_) => {
                if self.band_list("currentMembers").is_empty() {
                    issues.push("No current members found in bandInfo".into());
                }
                if self.band_list("formerMembers").is_empty() {
                    issues.push("No former members found in bandInfo".into());
                }
            }
        }
        match &self.discography {
            None => issues.push("discography not found in static data".into()),
            Some(_) => {
                for kind in ["studioAlbums", "compilationAlbums", "liveAlbums"] {
                    if self.album_list(kind).is_empty() {
                        issues.push(format!("No {kind} found in discography"));
                    }
                }
            }
        }
        issues
    }
}

fn list_of_objects<'a>(root: Option<&'a Value>, key: &str) -> Vec<&'a Map<String, Value>> {
    root.and_then(|v| v.get(key))
        .and_then(Value::as_array)
        .map(|items| items.iter().filter_map(Value::as_object).collect())
        .unwrap_or_default()
}

/// One intent in a training corpus.
#[derive(Debug, Clone, Deserialize)]
pub struct IntentData {
    pub intent: String,
    #[serde(default)]
    pub utterances: Vec<String>,
    #[serde(default)]
    pub answers: Vec<String>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Corpus {
    #[serde(default)]
    pub data: Vec<IntentData>,
}

/// `{"base": ..., "rhcp": ...}` — the two corpora, in the order the Python looked them up.
#[derive(Debug, Clone, Default)]
pub struct TrainingData {
    pub corpora: Vec<(String, Corpus)>,
}

impl TrainingData {
    pub fn load(dir: &Path) -> Self {
        let mut corpora = Vec::new();
        for (file, key) in [("base-corpus.json", "base"), ("rhcp-corpus-v2.json", "rhcp")] {
            let path = dir.join(file);
            match fs::read_to_string(&path)
                .map_err(anyhow::Error::from)
                .and_then(|t| serde_json::from_str::<Corpus>(&t).with_context(|| format!("parsing {}", path.display())))
            {
                Ok(corpus) => corpora.push((key.to_string(), corpus)),
                Err(_) => println!("Warning: Training file {} not found", path.display()),
            }
        }
        Self { corpora }
    }

    /// First corpus (base, then rhcp) whose entry for `intent` has answers.
    pub fn answers_for(&self, intent: &str) -> Option<&[String]> {
        for key in ["base", "rhcp"] {
            if let Some((_, corpus)) = self.corpora.iter().find(|(k, _)| k == key) {
                if let Some(item) = corpus.data.iter().find(|i| i.intent == intent) {
                    if !item.answers.is_empty() {
                        return Some(&item.answers);
                    }
                }
            }
        }
        None
    }

    /// Every (utterance, intent) pair except the `"None"` intent, in corpus order.
    pub fn samples(&self) -> (Vec<&str>, Vec<&str>) {
        let (mut texts, mut intents) = (Vec::new(), Vec::new());
        for (_, corpus) in &self.corpora {
            for item in &corpus.data {
                if item.intent != "None" {
                    for u in &item.utterances {
                        texts.push(u.as_str());
                        intents.push(item.intent.as_str());
                    }
                }
            }
        }
        (texts, intents)
    }
}
