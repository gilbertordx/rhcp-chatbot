//! RHCP chatbot, Rust remaster. See `docs/RUST_LEARNING.md`.

// axum helpers return a whole `Response` as their error value; it is large, but request
// handling is not a hot path, and boxing would add noise for a learner reading the code.
#![allow(clippy::result_large_err)]
// Some nested `if let` blocks are kept as written in the Python so the two can be read side by side.
#![allow(clippy::collapsible_if)]

pub mod api;
pub mod app;
pub mod auth;
pub mod cli;
pub mod config;
pub mod data;
pub mod errors;
pub mod fts_builder;
pub mod inference;
pub mod memory;
pub mod nlp;
pub mod nltk_setup;
pub mod processor;
pub mod pyfmt;
pub mod pyjson;
pub mod resolver;
pub mod schemas;
pub mod search;
