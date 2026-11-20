//! Application start-up. Python equivalent: `initialize_chatbot()` in
//! `app/chatbot/initializer.py` plus the wiring in `app/main.py`'s lifespan.

use std::path::Path;
use std::sync::Arc;

use anyhow::{Context, Result};

use crate::config::Settings;
use crate::data::{StaticData, TrainingData};
use crate::inference::Inference;
use crate::memory::ConversationMemory;
use crate::nlp::classifier::Classifier;
use crate::nlp::tokenizer::TextAnalyzer;
use crate::processor::{ChatbotProcessor, Nlu};
use crate::resolver::KnowledgeResolver;

/// Memory limits: the API used (100 sessions, 24 h); the CLI used (10 sessions, 1 h).
#[derive(Clone, Copy)]
pub struct MemoryLimits {
    pub max_sessions: usize,
    pub timeout_hours: i64,
}

pub const API_MEMORY: MemoryLimits = MemoryLimits {
    max_sessions: 100,
    timeout_hours: 24,
};
pub const CLI_MEMORY: MemoryLimits = MemoryLimits {
    max_sessions: 10,
    timeout_hours: 1,
};

/// Load everything and return the ready-to-use pipeline (API memory limits).
pub fn initialize(settings: &Settings) -> Result<Inference> {
    initialize_with(settings, API_MEMORY)
}

pub fn initialize_with(settings: &Settings, memory: MemoryLimits) -> Result<Inference> {
    println!("Initializing chatbot...");

    let training = TrainingData::load(Path::new(&settings.training_dir));
    let static_data = StaticData::load(
        Path::new(&settings.band_info_path),
        Path::new(&settings.discography_path),
    );
    let missing: Vec<&str> = [
        ("bandInfo", static_data.band_info.is_none()),
        ("discography", static_data.discography.is_none()),
    ]
    .into_iter()
    .filter(|(_, m)| *m)
    .map(|(n, _)| n)
    .collect();
    if !missing.is_empty() {
        println!("Missing static data files: {missing:?}");
        println!("Chatbot will operate with limited functionality");
    }

    let analyzer = TextAnalyzer::from_nltk_data().context("loading the NLTK sentence tokenizer data")?;

    let model_path = Path::new(&settings.model_path);
    let classifier = if model_path.exists() {
        println!("Loading NLU classifier from {}...", model_path.display());
        let c = Classifier::load(model_path).context("loading the classifier")?;
        println!("NLU classifier loaded successfully.");
        c
    } else {
        // Same fallback as the Python app: "No pre-trained model found. Training new model..."
        println!("No pre-trained model found. Training new model...");
        let (texts, intents) = training.samples();
        anyhow::ensure!(!texts.is_empty(), "no training data found in {}", settings.training_dir);
        println!("Training on {} samples...", texts.len());
        let (model, _report) = crate::nlp::trainer::train(&analyzer, &texts, &intents, &Default::default());
        crate::nlp::classifier::save_model(&model, model_path)?;
        println!("Model saved to {}", model_path.display());
        Classifier::from_file(model)?
    };

    let nlu = Arc::new(Nlu { analyzer, classifier });
    // The processor gets its own memory, as in Python; the inference pipeline has another.
    let processor = Arc::new(ChatbotProcessor::new(
        nlu,
        training,
        static_data,
        Some(ConversationMemory::new(100, 24)),
    ));

    let issues = processor.validate_static_data();
    if issues.is_empty() {
        println!("Static data validation passed");
    } else {
        println!("Static data validation issues:");
        for issue in &issues {
            println!("  - {issue}");
        }
        println!("Chatbot will operate with limited functionality");
    }
    println!("Chatbot initialized successfully.");

    Ok(Inference::new(
        processor,
        ConversationMemory::new(memory.max_sessions, memory.timeout_hours),
        KnowledgeResolver::load(Path::new(&settings.knowledge_dir)),
        settings.fts_db_path.clone().into(),
        settings.confidence_threshold,
    ))
}
