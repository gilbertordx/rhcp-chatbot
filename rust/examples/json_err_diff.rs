//! Helper: reads a JSON array of strings, prints [offset, message] (or null if CPython would accept it) for each.
use rhcp_chatbot::pyjson::python_json_error;
use serde_json::{Value, json};
fn main() {
    let inputs: Vec<String> =
        serde_json::from_str(&std::fs::read_to_string(std::env::args().nth(1).unwrap()).unwrap()).unwrap();
    let out: Vec<Value> = inputs
        .iter()
        .map(|s| match python_json_error(s) {
            Some((p, m)) => json!([p, m]),
            None => Value::Null,
        })
        .collect();
    println!("{}", Value::Array(out));
}
