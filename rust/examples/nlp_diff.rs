//! Helper for the Python-vs-Rust comparison: reads a JSON array of strings from
//! the file given as the first argument and prints, for each, the sentences,
//! word tokens, and stemmed tokens as JSON.
use rhcp_chatbot::nlp::tokenizer::TextAnalyzer;
use serde_json::{Value, json};

fn main() {
    let analyzer = TextAnalyzer::from_nltk_data().expect("NLTK punkt data");
    let text = std::fs::read_to_string(std::env::args().nth(1).expect("input json path")).unwrap();
    let inputs: Vec<String> = serde_json::from_str(&text).unwrap();
    let out: Vec<Value> = inputs
        .iter()
        .map(|s| json!({ "words": analyzer.word_tokenize(s), "stems": analyzer.tokenize_and_stem(s) }))
        .collect();
    println!("{}", Value::Array(out));
}
