//! Configuration from environment variables.
//!
//! Python equivalents: `app/config.py` (the `RHCP_*` settings) and
//! `app/core/config.py` (`SECRET_KEY`, `DATABASE_URL`, ...). Variable names and
//! defaults are unchanged so an existing `.env` file keeps working.
//!
//! Intentional differences (see docs/RUST_LEARNING.md): the model file default
//! is the file the app actually loads, and a few paths that were hard-coded in
//! Python can be overridden.

use crate::errors::RhcpError;

#[derive(Debug, Clone, PartialEq)]
pub struct Settings {
    // --- app/config.py ---
    pub env: String,
    pub debug: bool,
    pub port: u16,
    pub host: String,
    pub database_url: String,
    pub log_level: String,
    pub log_format: String,
    pub secret_key: String,
    pub algorithm: String,
    pub access_token_expire_minutes: i64,
    pub bcrypt_rounds: u32,
    pub model_path: String,
    pub band_info_path: String,
    pub discography_path: String,
    // --- paths that were hard-coded in Python ---
    pub training_dir: String,
    pub knowledge_dir: String,
    pub fts_db_path: String,
    /// Python: the literal `0.60` inside `apply_confidence_gating`.
    pub confidence_threshold: f64,
    // --- app/core/config.py (a second, separate config in the Python code) ---
    pub auth_database_path: String,
}

pub const DEFAULT_SECRET: &str = "your-secret-key-change-in-production";

fn var(name: &str, default: &str) -> String {
    std::env::var(name).unwrap_or_else(|_| default.to_string())
}

fn parse<T: std::str::FromStr>(name: &str, default: &str) -> Result<T, RhcpError> {
    var(name, default)
        .parse()
        .map_err(|_| RhcpError::config(format!("invalid value for {name}: {:?}", var(name, default))))
}

/// `sqlite:///./rhcp_chatbot.db` -> `./rhcp_chatbot.db`. Only SQLite is supported.
pub fn sqlite_path(url: &str) -> Result<String, RhcpError> {
    url.strip_prefix("sqlite:///")
        .map(str::to_string)
        .ok_or_else(|| RhcpError::config(format!("only sqlite:/// database URLs are supported, got {url:?}")))
}

impl Settings {
    pub fn from_env() -> Result<Self, RhcpError> {
        let settings = Self {
            env: var("RHCP_ENV", "dev"),
            debug: var("RHCP_DEBUG", "false").to_lowercase() == "true",
            port: parse("RHCP_PORT", "3000")?,
            host: var("RHCP_HOST", "0.0.0.0"),
            database_url: var("RHCP_DB_URL", "sqlite:///./data/rhcp.sqlite3"),
            log_level: var("RHCP_LOG_LEVEL", "INFO"),
            log_format: var("RHCP_LOG_FORMAT", "json"),
            // Python had two secrets: RHCP_SECRET_KEY (config.py, never used) and
            // SECRET_KEY (core/config.py, used to sign tokens). Only the real one is kept.
            secret_key: var("SECRET_KEY", DEFAULT_SECRET),
            algorithm: var("RHCP_ALGORITHM", "HS256"),
            access_token_expire_minutes: parse("ACCESS_TOKEN_EXPIRE_MINUTES", "30")?,
            bcrypt_rounds: parse("BCRYPT_ROUNDS", "12")?,
            model_path: var("RHCP_MODEL_PATH", "data/models/classifier_weights.json"),
            band_info_path: var("RHCP_BAND_INFO_PATH", "app/chatbot/data/static/band-info.json"),
            discography_path: var("RHCP_DISCOGRAPHY_PATH", "app/chatbot/data/static/discography.json"),
            training_dir: var("RHCP_TRAINING_DIR", "app/chatbot/data/training"),
            knowledge_dir: var("RHCP_KNOWLEDGE_DIR", "data/knowledge"),
            fts_db_path: var("RHCP_FTS_DB_PATH", "data/rhcp_fts.sqlite"),
            confidence_threshold: parse("RHCP_CONFIDENCE_THRESHOLD", "0.60")?,
            auth_database_path: sqlite_path(&var("DATABASE_URL", "sqlite:///./rhcp_chatbot.db"))?,
        };
        settings.validate()?;
        Ok(settings)
    }

    pub fn is_production(&self) -> bool {
        self.env.to_lowercase() == "production"
    }

    pub fn validate(&self) -> Result<(), RhcpError> {
        if self.port < 1 {
            return Err(RhcpError::config(format!("Invalid port number: {}", self.port)));
        }
        if !["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"].contains(&self.log_level.as_str()) {
            return Err(RhcpError::config(format!("Invalid log level: {}", self.log_level)));
        }
        if !["json", "human"].contains(&self.log_format.as_str()) {
            return Err(RhcpError::config(format!("Invalid log format: {}", self.log_format)));
        }
        if self.access_token_expire_minutes < 1 {
            return Err(RhcpError::config(format!(
                "Invalid access token expire minutes: {}",
                self.access_token_expire_minutes
            )));
        }
        if !(4..=31).contains(&self.bcrypt_rounds) {
            return Err(RhcpError::config(format!(
                "Invalid bcrypt rounds: {}",
                self.bcrypt_rounds
            )));
        }
        if !(0.0..=1.0).contains(&self.confidence_threshold) {
            return Err(RhcpError::config(format!(
                "Invalid confidence threshold: {}",
                self.confidence_threshold
            )));
        }
        Ok(())
    }
}
