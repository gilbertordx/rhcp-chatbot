//! Request/response shapes. Python equivalent: `app/schemas.py` (pydantic models).
//!
//! Pydantic validated these at runtime. In Rust the *types* do most of that work
//! (an `Intent` can only be one of nine values), and the few rules that a type
//! cannot express are checked in `ResponseModel::new` and `ChatRequest::validate`.

use serde::{Deserialize, Serialize};
use serde_json::{Map, Value};

/// The only intents the API will ever return (JSON: `"greetings.hello"` etc.).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Intent {
    #[serde(rename = "greetings.hello")]
    GreetingsHello,
    #[serde(rename = "greetings.bye")]
    GreetingsBye,
    #[serde(rename = "member.biography")]
    MemberBiography,
    #[serde(rename = "band.members")]
    BandMembers,
    #[serde(rename = "album.info")]
    AlbumInfo,
    #[serde(rename = "song.info")]
    SongInfo,
    #[serde(rename = "band.history")]
    BandHistory,
    #[serde(rename = "intent.outofscope")]
    OutOfScope,
    #[serde(rename = "unknown")]
    Unknown,
}

impl Intent {
    /// Parse a label from the classifier. Labels that are not valid intents
    /// (`"album.specific"`, `"agent.age"`, ...) return `None`.
    pub fn from_label(label: &str) -> Option<Self> {
        Some(match label {
            "greetings.hello" => Self::GreetingsHello,
            "greetings.bye" => Self::GreetingsBye,
            "member.biography" => Self::MemberBiography,
            "band.members" => Self::BandMembers,
            "album.info" => Self::AlbumInfo,
            "song.info" => Self::SongInfo,
            "band.history" => Self::BandHistory,
            "intent.outofscope" => Self::OutOfScope,
            "unknown" => Self::Unknown,
            _ => return None,
        })
    }

    pub fn as_str(&self) -> &'static str {
        match self {
            Self::GreetingsHello => "greetings.hello",
            Self::GreetingsBye => "greetings.bye",
            Self::MemberBiography => "member.biography",
            Self::BandMembers => "band.members",
            Self::AlbumInfo => "album.info",
            Self::SongInfo => "song.info",
            Self::BandHistory => "band.history",
            Self::OutOfScope => "intent.outofscope",
            Self::Unknown => "unknown",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum EntityType {
    Member,
    Album,
    Song,
    Band,
}

impl EntityType {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Member => "member",
            Self::Album => "album",
            Self::Song => "song",
            Self::Band => "band",
        }
    }
}

/// A recognised thing in the user's message (a band member, album or song).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Entity {
    #[serde(rename = "type")]
    pub kind: EntityType,
    /// The details record from the knowledge files (name, dates, biography ...).
    pub value: Map<String, Value>,
    pub confidence: f64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ResponseModel {
    pub intent: Intent,
    pub confidence: f64,
    pub entities: Vec<Entity>,
    pub final_message: String,
    pub raw_intent: Option<String>,
    pub raw_confidence: Option<f64>,
}

impl ResponseModel {
    /// Build a response, applying the pydantic rules: the message is stripped and
    /// must not be empty; confidences must be in `[0, 1]`.
    pub fn new(
        intent: Intent,
        confidence: f64,
        entities: Vec<Entity>,
        final_message: &str,
        raw_intent: Option<String>,
        raw_confidence: Option<f64>,
    ) -> Result<Self, crate::errors::RhcpError> {
        let message = final_message.trim();
        if message.is_empty() {
            return Err(crate::errors::RhcpError::processing(
                "final_message cannot be empty or whitespace",
            ));
        }
        for c in [Some(confidence), raw_confidence].into_iter().flatten() {
            if !(0.0..=1.0).contains(&c) {
                return Err(crate::errors::RhcpError::processing(
                    "confidence must be between 0.0 and 1.0",
                ));
            }
        }
        Ok(Self {
            intent,
            confidence,
            entities,
            final_message: message.to_string(),
            raw_intent,
            raw_confidence,
        })
    }
}

#[derive(Debug, Clone, Deserialize)]
pub struct ChatRequest {
    pub message: String,
}

/// Why a chat message was rejected (pydantic's messages, which FastAPI returned as a 422).
#[derive(Debug, PartialEq, Eq)]
pub enum MessageProblem {
    TooShort,
    TooLong,
    Blank,
}

impl ChatRequest {
    pub const MAX_LEN: usize = 2000;

    /// Pydantic order: length limits are checked first, then the whitespace rule.
    /// On success the message is returned stripped.
    pub fn validate(message: &str) -> Result<String, MessageProblem> {
        let len = message.chars().count();
        if len < 1 {
            return Err(MessageProblem::TooShort);
        }
        if len > Self::MAX_LEN {
            return Err(MessageProblem::TooLong);
        }
        let stripped = message.trim();
        if stripped.is_empty() {
            return Err(MessageProblem::Blank);
        }
        Ok(stripped.to_string())
    }
}

#[derive(Debug, Clone, Serialize)]
pub struct ChatResponse {
    pub response: ResponseModel,
    pub session_id: Option<String>,
}
