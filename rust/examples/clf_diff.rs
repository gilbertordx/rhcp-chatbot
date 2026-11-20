//! Helper for the scikit-learn comparison: args = model.json inputs.json.
//! Prints one probability vector (classes in model order) per input.
use rhcp_chatbot::nlp::{classifier::Classifier, tokenizer::TextAnalyzer};
fn main() {
    let args: Vec<String> = std::env::args().collect();
    let analyzer = TextAnalyzer::from_nltk_data().expect("NLTK punkt data");
    let clf = Classifier::load(std::path::Path::new(&args[1])).expect("model");
    let inputs: Vec<String> = serde_json::from_str(&std::fs::read_to_string(&args[2]).unwrap()).unwrap();
    let out: Vec<Vec<f64>> = inputs.iter().map(|t| clf.predict_proba(&analyzer, t)).collect();
    println!("{}", serde_json::to_string(&out).unwrap());
}
