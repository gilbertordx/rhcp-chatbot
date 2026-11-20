//! Helper for the Python-vs-Rust comparison of the whole inference pipeline.
//! args: messages.json threshold   (run from the repository root)
//! Prints one `ResponseModel` JSON object per message.
use rhcp_chatbot::{app, config::Settings};
use serde_json::Value;

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let messages: Vec<String> = serde_json::from_str(&std::fs::read_to_string(&args[1]).unwrap()).unwrap();
    let mut settings = Settings::from_env().unwrap();
    settings.confidence_threshold = args[2].parse().unwrap();
    let inference = {
        // keep start-up chatter off stdout so only JSON is printed
        let _quiet = ();
        app::initialize(&settings).expect("initialize")
    };
    let out: Vec<Value> = messages
        .iter()
        .map(|m| serde_json::to_value(inference.run_inference(m, None).expect("inference")).unwrap())
        .collect();
    eprintln!("done");
    println!("@@JSON@@{}", Value::Array(out));
}
