//! Error types. Python equivalent: `app/errors.py`.
//!
//! Python used a family of exception classes that all extended `RHCPError`.
//! Rust has no exceptions or inheritance, so this is one struct plus an enum
//! saying which kind it is. Functions that can fail return `Result<T, RhcpError>`
//! and callers use `?` to pass the error up.

use serde_json::{Map, Value};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ErrorKind {
    Config,
    InvalidInput,
    Processing,
    Authentication,
    Database,
    Model,
}

#[derive(Debug, Clone, thiserror::Error)]
#[error("{message}")]
pub struct RhcpError {
    pub kind: ErrorKind,
    pub message: String,
    pub details: Map<String, Value>,
}

impl RhcpError {
    pub fn new(kind: ErrorKind, message: impl Into<String>) -> Self {
        Self {
            kind,
            message: message.into(),
            details: Map::new(),
        }
    }

    pub fn invalid_input(message: impl Into<String>) -> Self {
        Self::new(ErrorKind::InvalidInput, message)
    }

    pub fn processing(message: impl Into<String>) -> Self {
        Self::new(ErrorKind::Processing, message)
    }

    pub fn config(message: impl Into<String>) -> Self {
        Self::new(ErrorKind::Config, message)
    }

    pub fn model(message: impl Into<String>) -> Self {
        Self::new(ErrorKind::Model, message)
    }

    /// The `remedy` hint shown to API clients (Python: `details.get("remedy", "Please try again")`).
    pub fn remedy(&self) -> String {
        self.details
            .get("remedy")
            .and_then(Value::as_str)
            .unwrap_or("Please try again")
            .to_string()
    }
}
