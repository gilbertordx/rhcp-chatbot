//! The full "message in, structured answer out" pipeline.
//! Python equivalent: `app/core/inference.py`.
//!
//! Steps (same as the original): classify -> confidence gate -> canonicalize
//! entities -> build the reply -> remember the exchange.
//!
//! Quirks of the original that are kept on purpose (details in docs/RUST_LEARNING.md):
//! * the gate is 0.60 but the model's probabilities are rarely that high, so most
//!   questions end as `unknown`;
//! * the entity "span" given to the resolver is always empty, so resolution never
//!   succeeds and the raw entity is used as is;
//! * fact lookups use the entity's display name, which usually differs from the
//!   lower-case `canonical` key in the database.

use std::path::PathBuf;
use std::sync::{Arc, Mutex};

use serde_json::{Map, Value, json};

use crate::errors::RhcpError;
use crate::memory::{BotResponse, ConversationMemory};
use crate::processor::{ChatbotProcessor, RawEntity};
use crate::pyfmt::{py_repr, py_str};
use crate::resolver::KnowledgeResolver;
use crate::schemas::{Entity, EntityType, Intent, ResponseModel};
use crate::search::{Fact, FactSearchEngine};

const UNKNOWN_MESSAGE: &str =
    "I'm not sure what you mean. Let's talk about RHCP! What would you like to know about the Red Hot Chili Peppers?";

pub struct Inference {
    processor: Arc<ChatbotProcessor>,
    memory: Mutex<ConversationMemory>,
    resolver: KnowledgeResolver,
    fts_path: PathBuf,
    /// Opened on first use, like Python's `get_search_engine()`; retried if it failed.
    search: Mutex<Option<Arc<FactSearchEngine>>>,
    threshold: f64,
}

/// `(raw intent, raw confidence, raw entities)`
pub type Classification = (String, f64, Vec<RawEntity>);

impl Inference {
    pub fn new(
        processor: Arc<ChatbotProcessor>,
        memory: ConversationMemory,
        resolver: KnowledgeResolver,
        fts_path: PathBuf,
        threshold: f64,
    ) -> Self {
        Self {
            processor,
            memory: Mutex::new(memory),
            resolver,
            fts_path,
            search: Mutex::new(None),
            threshold,
        }
    }

    pub fn processor(&self) -> &ChatbotProcessor {
        &self.processor
    }

    /// Run `f` with this pipeline's own memory (the CLI creates its session here).
    pub fn with_memory<R>(&self, f: impl FnOnce(&mut ConversationMemory) -> R) -> R {
        f(&mut self.memory.lock().expect("memory lock"))
    }

    fn search_engine(&self) -> anyhow::Result<Arc<FactSearchEngine>> {
        let mut slot = self.search.lock().expect("search lock");
        if let Some(engine) = slot.as_ref() {
            return Ok(engine.clone());
        }
        let engine = Arc::new(FactSearchEngine::open(&self.fts_path)?);
        *slot = Some(engine.clone());
        Ok(engine)
    }

    /// Step 1: the classifier's best guess and the entities found in the text.
    pub fn classify(&self, message: &str) -> Classification {
        let lowered = message.to_lowercase();
        let classifications = self.processor.nlu().classifications(&lowered);
        let Some((label, value)) = classifications.first() else {
            return ("unknown".into(), 0.0, Vec::new());
        };
        (label.clone(), *value, self.processor.find_entities(&lowered))
    }

    /// Step 2: accept the raw intent only if it is confident AND one of the valid intents.
    pub fn apply_confidence_gating(&self, raw_intent: &str, raw_confidence: f64) -> (Intent, f64) {
        if raw_confidence >= self.threshold {
            (
                Intent::from_label(raw_intent).unwrap_or(Intent::Unknown),
                raw_confidence,
            )
        } else {
            (Intent::Unknown, raw_confidence)
        }
    }

    /// Step 3: replace each raw entity by its canonical record when the resolver finds one.
    pub fn canonicalize_entities(&self, raw: &[RawEntity]) -> Vec<Entity> {
        let mut out = Vec::new();
        for entity in raw {
            let kind = match entity.get("type").and_then(Value::as_str) {
                Some("member") => EntityType::Member,
                Some("album") => EntityType::Album,
                Some("song") => EntityType::Song,
                Some("band") => EntityType::Band,
                _ => continue, // invalid type: skipped (the Python logged a warning)
            };
            let raw_value = entity.get("value").cloned().unwrap_or_else(|| json!({}));
            // The original asked for `raw_value["text"]`, which the records never have,
            // so the span is always "" and resolution never matches.
            let span = match &raw_value {
                Value::Object(m) => m.get("text").map(py_str).unwrap_or_default(),
                other => py_str(other),
            };
            let canonical = match kind {
                EntityType::Member => self.resolver.resolve_member(&span),
                EntityType::Album => self.resolver.resolve_album(&span),
                EntityType::Song => self.resolver.resolve_song(&span),
                EntityType::Band => None,
            };
            let value = match (canonical, raw_value) {
                (Some(c), _) => c,
                (None, Value::Object(m)) => m,
                (None, _) => continue, // not a dict: pydantic rejected it, entity skipped
            };
            let confidence = entity.get("confidence").and_then(Value::as_f64).unwrap_or(0.5);
            out.push(Entity {
                kind,
                value,
                confidence,
            });
        }
        out
    }

    /// Step 4: the reply text for a final intent.
    pub fn build_response(
        &self,
        final_intent: Intent,
        final_confidence: f64,
        entities: Vec<Entity>,
        raw_intent: &str,
        raw_confidence: f64,
        session_id: Option<&str>,
    ) -> Result<ResponseModel, RhcpError> {
        let message = if final_intent == Intent::Unknown {
            UNKNOWN_MESSAGE.to_string()
        } else if !entities.is_empty()
            && matches!(
                final_intent,
                Intent::MemberBiography | Intent::AlbumInfo | Intent::SongInfo
            )
        {
            self.build_factual_response(final_intent, &entities)
        } else {
            let as_dicts: Vec<RawEntity> = entities.iter().map(entity_as_dict).collect();
            self.processor
                .generate_contextual_response("", final_intent.as_str(), &as_dicts, session_id)
        };
        ResponseModel::new(
            final_intent,
            final_confidence,
            entities,
            &message,
            Some(raw_intent.to_string()),
            Some(raw_confidence),
        )
    }

    fn build_factual_response(&self, intent: Intent, entities: &[Entity]) -> String {
        let attempt = || -> anyhow::Result<String> {
            let Some(entity) = entities.first() else {
                return Ok("I don't have enough information to answer that question.".into());
            };
            // Python: member -> value.get("canonical", value.get("name", "")),
            //         album/song -> value.get("canonical", value.get("title", "")).
            let fallback_key = if entity.kind == EntityType::Member {
                "name"
            } else {
                "title"
            };
            let canonical_value = entity
                .value
                .get("canonical")
                .or_else(|| entity.value.get(fallback_key))
                .cloned()
                .unwrap_or(json!(""));
            let canonical = py_str(&canonical_value);
            let falsy = matches!(&canonical_value, Value::Null | Value::Bool(false))
                || canonical_value.as_str().is_some_and(str::is_empty)
                || canonical_value.as_i64() == Some(0);
            if falsy {
                return Ok("I don't have enough information to answer that question.".into());
            }

            let engine = self.search_engine()?;
            let facts: Vec<Fact> = engine
                .get_facts_by_canonical(&canonical, Some(entity.kind.as_str()))
                .unwrap_or_default();
            if facts.is_empty() {
                return Ok(format!("I don't have specific information about {canonical}."));
            }
            Ok(match intent {
                Intent::MemberBiography => member_response(&facts, &canonical),
                Intent::AlbumInfo => album_response(&facts, &canonical),
                Intent::SongInfo => song_response(&facts, &canonical),
                _ => generic_response(&facts, &canonical),
            })
        };
        attempt().unwrap_or_else(|_| {
            let what = entities
                .first()
                .map(|e| py_repr(&Value::Object(e.value.clone())))
                .unwrap_or_else(|| "this topic".into());
            format!("I have information about {what}, but I'm having trouble retrieving the details right now.")
        })
    }

    /// The whole pipeline for one message.
    pub fn run_inference(&self, message: &str, session_id: Option<&str>) -> Result<ResponseModel, RhcpError> {
        let (raw_intent, raw_confidence, raw_entities) = self.classify(message);
        let (final_intent, final_confidence) = self.apply_confidence_gating(&raw_intent, raw_confidence);
        let entities = self.canonicalize_entities(&raw_entities);
        let response = self.build_response(
            final_intent,
            final_confidence,
            entities,
            &raw_intent,
            raw_confidence,
            session_id,
        )?;

        if let Some(session_id) = session_id {
            // Intentional fix: the Python looked for a `message` key that `model_dump()`
            // never had (it is `final_message`), so the stored bot message was always empty.
            self.with_memory(|m| {
                m.add_message(
                    session_id,
                    message,
                    &BotResponse {
                        message: response.final_message.clone(),
                        intent: Some(response.intent.as_str().to_string()),
                        confidence: Some(response.confidence),
                        entities: response.entities.iter().map(entity_as_dict).collect(),
                    },
                )
            });
        }
        Ok(response)
    }
}

/// `Entity.dict()`: the three keys the Python model had.
fn entity_as_dict(e: &Entity) -> Map<String, Value> {
    let mut m = Map::new();
    m.insert("type".into(), json!(e.kind.as_str()));
    m.insert("value".into(), Value::Object(e.value.clone()));
    m.insert("confidence".into(), json!(e.confidence));
    m
}

/// Join like Python's `" is ".join(parts) + "."` — the sentence structure is odd
/// ("Flea is plays bass is joined in 1983."), and kept as is.
fn finish(parts: Vec<String>, canonical: &str) -> String {
    if parts.is_empty() {
        format!("I have information about {canonical} but the details are incomplete.")
    } else {
        parts.join(" is ") + "."
    }
}

fn truthy(s: &Option<String>) -> Option<&str> {
    s.as_deref().filter(|v| !v.is_empty())
}

pub fn member_response(facts: &[Fact], canonical: &str) -> String {
    let (mut name, mut join_year, mut active, mut notes) = (None, None, None, None);
    let mut roles: Vec<&str> = Vec::new();
    for f in facts {
        match f.field.as_str() {
            "name" => name = Some(f.value.clone()),
            "role" => roles.push(&f.value),
            "join_year" => join_year = Some(f.value.clone()),
            "active" => active = Some(f.value.clone()),
            "notes" => notes = Some(f.value.clone()),
            _ => {}
        }
    }
    let mut parts = Vec::new();
    if let Some(n) = truthy(&name) {
        parts.push(n.to_string());
    }
    if !roles.is_empty() {
        parts.push(format!("plays {}", roles.join(", ")));
    }
    if let Some(y) = truthy(&join_year) {
        parts.push(format!("joined in {y}"));
    }
    if let Some(a) = &active {
        let status = if a.to_lowercase() == "true" {
            "currently active"
        } else {
            "not currently active"
        };
        parts.push(format!("is {status}"));
    }
    if let Some(n) = truthy(&notes) {
        parts.push(format!("Note: {n}"));
    }
    finish(parts, canonical)
}

pub fn album_response(facts: &[Fact], canonical: &str) -> String {
    let (mut title, mut year, mut label, mut tracks, mut notes) = (None, None, None, None, None);
    for f in facts {
        match f.field.as_str() {
            "title" => title = Some(f.value.clone()),
            "year" => year = Some(f.value.clone()),
            "label" => label = Some(f.value.clone()),
            "tracks" => tracks = Some(f.value.clone()),
            "notes" => notes = Some(f.value.clone()),
            _ => {}
        }
    }
    let mut parts = Vec::new();
    if let Some(v) = truthy(&title) {
        parts.push(v.to_string());
    }
    if let Some(v) = truthy(&year) {
        parts.push(format!("released in {v}"));
    }
    if let Some(v) = truthy(&label) {
        parts.push(format!("on {v}"));
    }
    if let Some(v) = truthy(&tracks) {
        parts.push(format!("has {v} tracks"));
    }
    if let Some(v) = truthy(&notes) {
        parts.push(format!("Note: {v}"));
    }
    finish(parts, canonical)
}

pub fn song_response(facts: &[Fact], canonical: &str) -> String {
    let (mut title, mut year, mut album, mut track_no, mut notes) = (None, None, None, None, None);
    for f in facts {
        match f.field.as_str() {
            "title" => title = Some(f.value.clone()),
            "year" => year = Some(f.value.clone()),
            "album" => album = Some(f.value.clone()),
            "track_no" => track_no = Some(f.value.clone()),
            "notes" => notes = Some(f.value.clone()),
            _ => {}
        }
    }
    let mut parts = Vec::new();
    if let Some(v) = truthy(&title) {
        parts.push(v.to_string());
    }
    if let Some(v) = truthy(&year) {
        parts.push(format!("released in {v}"));
    }
    if let Some(v) = truthy(&album) {
        parts.push(format!("from the album {v}"));
    }
    if let Some(v) = truthy(&track_no) {
        parts.push(format!("track {v}"));
    }
    if let Some(v) = truthy(&notes) {
        parts.push(format!("Note: {v}"));
    }
    finish(parts, canonical)
}

pub fn generic_response(facts: &[Fact], canonical: &str) -> String {
    // Group by field, in first-seen order; values de-duplicated through a Python `set`
    // (order unspecified there, so it is sorted here for stable output).
    let mut fields: Vec<(String, Vec<String>)> = Vec::new();
    for f in facts {
        match fields.iter_mut().find(|(k, _)| *k == f.field) {
            Some((_, v)) => v.push(f.value.clone()),
            None => fields.push((f.field.clone(), vec![f.value.clone()])),
        }
    }
    let mut parts = vec![format!("Here's what I know about {canonical}:")];
    for (field, values) in fields {
        if field == "name" || field == "title" {
            continue;
        }
        let mut unique: Vec<String> = values;
        unique.sort();
        unique.dedup();
        if unique.len() == 1 {
            parts.push(format!("{field}: {}", unique[0]));
        } else {
            parts.push(format!("{field}: {}", unique.join(", ")));
        }
    }
    if parts.len() > 1 {
        parts.join(" ")
    } else {
        format!("I have basic information about {canonical} but not many details.")
    }
}
