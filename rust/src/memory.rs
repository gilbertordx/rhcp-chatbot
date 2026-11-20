//! Conversation memory. Python equivalent: `app/chatbot/memory.py`.
//!
//! The Python version kept everything in nested dicts (`context["patterns"]["..."]`).
//! Here the same information lives in typed structs, so a misspelled key is a
//! compile error instead of a silent `KeyError` or `None`.
//!
//! Note (same as the original): sessions only exist if `create_session` was
//! called. The HTTP API never calls it, so over HTTP nothing is remembered;
//! only the command-line chat keeps a session.

use std::collections::{BTreeSet, HashMap};

use chrono::{DateTime, Duration, Local};
use serde_json::{Map, Value};

/// What the bot said, in the shape memory stores it.
#[derive(Debug, Clone, Default)]
pub struct BotResponse {
    pub message: String,
    pub intent: Option<String>,
    pub confidence: Option<f64>,
    /// Entities as JSON objects (`type`, `value`, `matched_text`, ...).
    pub entities: Vec<Map<String, Value>>,
}

#[derive(Debug, Clone)]
pub struct MessageEntry {
    pub timestamp: String,
    pub user_message: String,
    pub bot_message: String,
    pub intent: Option<String>,
    pub confidence: Option<f64>,
    pub entities: Vec<Map<String, Value>>,
}

#[derive(Debug, Clone)]
pub struct FlowEntry {
    pub intent: String,
    pub timestamp: String,
    pub confidence: f64,
    pub entities_count: usize,
}

#[derive(Debug, Clone, Default)]
pub struct Patterns {
    pub member_questions: u32,
    pub album_questions: u32,
    pub song_questions: u32,
    pub follow_up_questions: u32,
    pub general_questions: u32,
}

#[derive(Debug, Clone, Default)]
pub struct Context {
    pub current_topic: Option<String>,
    pub last_album: Option<String>,
    pub last_song: Option<String>,
    pub last_member: Option<String>,
    pub last_topic: Option<String>,
    pub topic_confidence: f64,
    pub mentioned_members: BTreeSet<String>,
    pub mentioned_albums: BTreeSet<String>,
    pub mentioned_songs: BTreeSet<String>,
    pub member_types: HashMap<String, String>,
    pub album_types: HashMap<String, String>,
    pub song_albums: HashMap<String, String>,
    pub conversation_flow: Vec<FlowEntry>,
    pub patterns: Patterns,
}

#[derive(Debug, Clone)]
struct Session {
    last_activity: DateTime<Local>,
    messages: Vec<MessageEntry>,
    context: Context,
}

/// The four "what were we just talking about" slots used to resolve "that one".
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct FollowUpContext {
    pub last_album: Option<String>,
    pub last_song: Option<String>,
    pub last_member: Option<String>,
    pub last_topic: Option<String>,
}

pub struct ConversationMemory {
    sessions: HashMap<String, Session>,
    max_sessions: usize,
    session_timeout_hours: i64,
}

/// Phrases that make a message count as a follow-up question (Python: `follow_up_indicators`).
const FOLLOW_UP_WORDS: [&str; 14] = [
    "what about",
    "how about",
    "tell me more",
    "and",
    "also",
    "too",
    "what else",
    "anything else",
    "more",
    "other",
    "different",
    "in what year",
    "when was",
    "who wrote",
];

impl ConversationMemory {
    pub fn new(max_sessions: usize, session_timeout_hours: i64) -> Self {
        Self {
            sessions: HashMap::new(),
            max_sessions,
            session_timeout_hours,
        }
    }

    pub fn create_session(&mut self) -> String {
        let id = uuid::Uuid::new_v4().to_string();
        if self.sessions.len() >= self.max_sessions {
            self.cleanup_old_sessions();
        }
        self.sessions.insert(
            id.clone(),
            Session {
                last_activity: Local::now(),
                messages: Vec::new(),
                context: Context::default(),
            },
        );
        id
    }

    /// Record one exchange. Silently ignores unknown sessions (as the original did).
    pub fn add_message(&mut self, session_id: &str, user_message: &str, bot: &BotResponse) {
        let Some(session) = self.sessions.get_mut(session_id) else {
            return;
        };
        session.last_activity = Local::now();
        let entry = MessageEntry {
            timestamp: Local::now().format("%Y-%m-%dT%H:%M:%S%.6f").to_string(),
            user_message: user_message.to_string(),
            bot_message: bot.message.clone(),
            intent: bot.intent.clone(),
            confidence: bot.confidence,
            entities: bot.entities.clone(),
        };
        session.messages.push(entry.clone());
        update_context(&mut session.context, &entry);
        if session.messages.len() > 10 {
            let drop = session.messages.len() - 10;
            session.messages.drain(..drop);
        }
    }

    /// The last `max_messages` exchanges, oldest first.
    pub fn conversation_history(&self, session_id: &str, max_messages: usize) -> Vec<MessageEntry> {
        let Some(session) = self.sessions.get(session_id) else {
            return Vec::new();
        };
        let start = session.messages.len().saturating_sub(max_messages);
        session.messages[start..].to_vec()
    }

    pub fn context(&self, session_id: &str) -> Option<&Context> {
        self.sessions.get(session_id).map(|s| &s.context)
    }

    pub fn follow_up_context(&self, session_id: &str) -> FollowUpContext {
        match self.sessions.get(session_id) {
            None => FollowUpContext::default(),
            Some(s) => FollowUpContext {
                last_album: s.context.last_album.clone(),
                last_song: s.context.last_song.clone(),
                last_member: s.context.last_member.clone(),
                last_topic: s.context.last_topic.clone(),
            },
        }
    }

    /// Remove sessions idle longer than the timeout.
    pub fn cleanup_old_sessions(&mut self) {
        let threshold = Local::now() - Duration::hours(self.session_timeout_hours);
        self.sessions.retain(|_, s| s.last_activity >= threshold);
    }

    pub fn is_session_valid(&self, session_id: &str) -> bool {
        self.sessions
            .get(session_id)
            .is_some_and(|s| s.last_activity > Local::now() - Duration::hours(self.session_timeout_hours))
    }

    pub fn session_count(&self) -> usize {
        self.sessions.len()
    }
}

fn entity_name(entity: &Map<String, Value>) -> Option<String> {
    entity.get("value")?.get("name")?.as_str().map(str::to_string)
}

fn update_context(context: &mut Context, entry: &MessageEntry) {
    for entity in &entry.entities {
        let kind = entity.get("type").and_then(Value::as_str).unwrap_or("");
        let Some(name) = entity_name(entity) else { continue };
        match kind {
            "member" => {
                context.mentioned_members.insert(name.clone());
                context.last_member = Some(name.clone());
                if let Some(t) = entity.get("member_type").and_then(Value::as_str) {
                    context.member_types.insert(name, t.to_string());
                }
            }
            "album" => {
                context.mentioned_albums.insert(name.clone());
                context.last_album = Some(name.clone());
                if let Some(t) = entity.get("album_type").and_then(Value::as_str) {
                    context.album_types.insert(name, t.to_string());
                }
            }
            "song" => {
                context.mentioned_songs.insert(name.clone());
                context.last_song = Some(name.clone());
                if let Some(album) = entity.get("value").and_then(|v| v.get("album")).and_then(Value::as_str) {
                    context.song_albums.insert(name, album.to_string());
                }
            }
            _ => {}
        }
    }

    let intent = entry.intent.as_deref();
    let has = |kind: &str| {
        entry
            .entities
            .iter()
            .any(|e| e.get("type").and_then(Value::as_str) == Some(kind))
    };

    if let Some(i) = intent.filter(|i| *i != "unknown" && *i != "None") {
        context.conversation_flow.push(FlowEntry {
            intent: i.to_string(),
            timestamp: entry.timestamp.clone(),
            confidence: entry.confidence.unwrap_or(0.0),
            entities_count: entry.entities.len(),
        });
        if context.conversation_flow.len() > 10 {
            let drop = context.conversation_flow.len() - 10;
            context.conversation_flow.drain(..drop);
        }
    }

    let set_topic = |topic: &str, conf: f64, c: &mut Context| {
        c.current_topic = Some(topic.to_string());
        c.last_topic = Some(topic.to_string());
        c.topic_confidence = conf;
    };
    if matches!(intent, Some("member.biography" | "band.members")) || has("member") {
        set_topic("band_members", 0.9, context);
    } else if intent == Some("album.info") || has("album") {
        set_topic("albums", 0.9, context);
    } else if intent == Some("song.info") || has("song") {
        set_topic("songs", 0.9, context);
    } else if intent == Some("band.history") {
        set_topic("band_history", 0.8, context);
    } else if matches!(intent, Some("greetings.hello" | "greetings.bye")) {
        set_topic("greetings", 0.7, context);
    } else {
        context.topic_confidence *= 0.8;
    }

    match intent {
        Some("member.biography" | "band.members") => context.patterns.member_questions += 1,
        Some("album.info") => context.patterns.album_questions += 1,
        Some("song.info") => context.patterns.song_questions += 1,
        Some("band.history") => context.patterns.general_questions += 1,
        _ => {}
    }

    let lowered = entry.user_message.to_lowercase();
    if FOLLOW_UP_WORDS.iter().any(|w| lowered.contains(w)) {
        context.patterns.follow_up_questions += 1;
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn member_entity(name: &str) -> Map<String, Value> {
        json!({"type": "member", "value": {"name": name}, "member_type": "current"})
            .as_object()
            .unwrap()
            .clone()
    }

    #[test]
    fn unknown_sessions_are_ignored() {
        let mut m = ConversationMemory::new(10, 24);
        m.add_message("nope", "hi", &BotResponse::default());
        assert_eq!(m.session_count(), 0);
        assert!(m.conversation_history("nope", 5).is_empty());
    }

    #[test]
    fn remembers_last_member_and_keeps_ten_messages() {
        let mut m = ConversationMemory::new(10, 24);
        let id = m.create_session();
        for i in 0..12 {
            let bot = BotResponse {
                message: format!("answer {i}"),
                intent: Some("member.biography".into()),
                confidence: Some(0.5),
                entities: vec![member_entity("Chad Smith")],
            };
            m.add_message(&id, &format!("question {i}"), &bot);
        }
        assert_eq!(m.conversation_history(&id, 100).len(), 10);
        assert_eq!(m.conversation_history(&id, 3)[2].user_message, "question 11");
        assert_eq!(m.follow_up_context(&id).last_member.as_deref(), Some("Chad Smith"));
        assert_eq!(m.follow_up_context(&id).last_topic.as_deref(), Some("band_members"));
        assert_eq!(m.context(&id).unwrap().patterns.member_questions, 12);
    }

    #[test]
    fn detects_follow_up_phrases() {
        let mut m = ConversationMemory::new(10, 24);
        let id = m.create_session();
        m.add_message(&id, "and what about flea", &BotResponse::default());
        assert_eq!(m.context(&id).unwrap().patterns.follow_up_questions, 1);
    }
}
