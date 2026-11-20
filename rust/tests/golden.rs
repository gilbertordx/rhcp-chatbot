//! Golden tests: the Rust pipeline must reproduce values captured from the ORIGINAL
//! Python code (`tools/make_golden.py` writes `golden.json`). Run from the repo root
//! (`cargo test --manifest-path rust/Cargo.toml` does that automatically because
//! `CARGO_MANIFEST_DIR/..` is used below).
//!
//! These need the NLTK Punkt data (`rhcp-chatbot setup-nltk`); without it they skip
//! with a message instead of failing, so a plain `cargo test` works on a fresh machine.

use std::path::PathBuf;

use rhcp_chatbot::config::Settings;
use rhcp_chatbot::nlp::tokenizer::TextAnalyzer;
use rhcp_chatbot::resolver::KnowledgeResolver;
use rhcp_chatbot::{app, nlp::punkt};
use serde_json::Value;

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .to_path_buf()
}

fn golden() -> Value {
    serde_json::from_str(&std::fs::read_to_string(repo_root().join("rust/tests/golden.json")).expect("golden.json"))
        .unwrap()
}

/// Skip (return false) when the NLTK data is not installed.
fn have_nltk() -> bool {
    let ok = punkt::find_punkt_dir().is_some();
    if !ok {
        eprintln!("SKIPPED: NLTK punkt data not installed (run `rhcp-chatbot setup-nltk`)");
    }
    ok
}

fn strings(v: &Value) -> Vec<String> {
    v.as_array()
        .unwrap()
        .iter()
        .map(|s| s.as_str().unwrap().to_string())
        .collect()
}

#[test]
fn tokens_and_stems_match_nltk() {
    if !have_nltk() {
        return;
    }
    let analyzer = TextAnalyzer::from_nltk_data().unwrap();
    for case in golden()["tokens"].as_array().unwrap() {
        let text = case["text"].as_str().unwrap();
        assert_eq!(
            analyzer.word_tokenize(text),
            strings(&case["words"]),
            "word_tokenize({text:?})"
        );
        assert_eq!(
            analyzer.tokenize_and_stem(text),
            strings(&case["stems"]),
            "tokenize+stem({text:?})"
        );
    }
}

fn inference() -> rhcp_chatbot::inference::Inference {
    std::env::set_current_dir(repo_root()).unwrap(); // the app reads data/ relative to the repo root
    let mut settings = Settings::from_env().unwrap();
    settings.confidence_threshold = 0.60;
    app::initialize(&settings)
        .expect("initialize (needs data/models/classifier_weights.json; see tools/export_model.py)")
}

#[test]
fn classifier_probabilities_match_scikit_learn() {
    if !have_nltk() {
        return;
    }
    let inf = inference();
    for case in golden()["classify"].as_array().unwrap() {
        let text = case["text"].as_str().unwrap();
        let ranked = inf.processor().nlu().classifications(&text.to_lowercase());
        for (i, expected) in case["top"].as_array().unwrap().iter().enumerate() {
            assert_eq!(
                ranked[i].0,
                expected[0].as_str().unwrap(),
                "rank {i} label for {text:?}"
            );
            assert!(
                (ranked[i].1 - expected[1].as_f64().unwrap()).abs() < 1e-9,
                "rank {i} probability for {text:?}"
            );
        }
    }
}

#[test]
fn full_pipeline_matches_the_original() {
    if !have_nltk() {
        return;
    }
    let inf = inference();
    for case in golden()["pipeline"].as_array().unwrap() {
        let text = case["text"].as_str().unwrap();
        let r = inf.run_inference(text, None).unwrap();
        assert_eq!(
            r.intent.as_str(),
            case["intent"].as_str().unwrap(),
            "intent for {text:?}"
        );
        assert_eq!(
            r.raw_intent.as_deref(),
            case["raw_intent"].as_str(),
            "raw intent for {text:?}"
        );
        assert!(
            (r.confidence - case["confidence"].as_f64().unwrap()).abs() < 1e-9,
            "confidence for {text:?}"
        );
        let types: Vec<&str> = r.entities.iter().map(|e| e.kind.as_str()).collect();
        let expected_types: Vec<String> = strings(&case["entity_types"]);
        assert_eq!(
            types,
            expected_types.iter().map(String::as_str).collect::<Vec<_>>(),
            "entity types for {text:?}"
        );
        let names: Vec<Option<&str>> = r
            .entities
            .iter()
            .map(|e| e.value.get("name").and_then(Value::as_str))
            .collect();
        let expected_names: Vec<Option<&str>> = case["entity_names"]
            .as_array()
            .unwrap()
            .iter()
            .map(Value::as_str)
            .collect();
        assert_eq!(names, expected_names, "entity names for {text:?}");
        // Replies picked at random from a list (greetings) cannot be compared exactly.
        if case["intent"] == "unknown" {
            assert_eq!(
                r.final_message,
                case["final_message"].as_str().unwrap(),
                "reply for {text:?}"
            );
        }
    }
}

#[test]
fn resolver_matches_the_original() {
    let r = KnowledgeResolver::load(&repo_root().join("data/knowledge"));
    let canon = |v: Option<serde_json::Map<String, Value>>| {
        v.and_then(|m| m.get("canonical").and_then(Value::as_str).map(str::to_string))
    };
    for case in golden()["resolve"].as_array().unwrap() {
        let span = case["span"].as_str().unwrap();
        assert_eq!(
            r.normalize_span(span),
            case["norm"].as_str().unwrap(),
            "normalize {span:?}"
        );
        assert_eq!(
            canon(r.resolve_member(span)).as_deref(),
            case["member"].as_str(),
            "member {span:?}"
        );
        assert_eq!(
            canon(r.resolve_album(span)).as_deref(),
            case["album"].as_str(),
            "album {span:?}"
        );
        assert_eq!(
            canon(r.resolve_song(span)).as_deref(),
            case["song"].as_str(),
            "song {span:?}"
        );
    }
}

#[test]
fn fact_database_builder_reproduces_the_committed_database() {
    let root = repo_root();
    let tmp = std::env::temp_dir().join(format!("rhcp-fts-test-{}.sqlite", std::process::id()));
    let built = rhcp_chatbot::fts_builder::build_database(&tmp, &root.join("data/knowledge")).unwrap();
    let rows = |path: &std::path::Path| -> Vec<(String, String, String, String, Option<i64>, String)> {
        let c = rusqlite::Connection::open(path).unwrap();
        let mut s = c
            .prepare("SELECT type, canonical, field, value, year, source FROM facts ORDER BY id")
            .unwrap();
        s.query_map([], |r| {
            Ok((r.get(0)?, r.get(1)?, r.get(2)?, r.get(3)?, r.get(4)?, r.get(5)?))
        })
        .unwrap()
        .map(Result::unwrap)
        .collect()
    };
    assert_eq!(built, 513);
    assert_eq!(rows(&tmp), rows(&root.join("data/rhcp_fts.sqlite")));
    let _ = std::fs::remove_file(tmp);
}
