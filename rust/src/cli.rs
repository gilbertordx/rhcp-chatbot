//! The interactive command-line chat. Python equivalent: `cli.py`.
//!
//! Intentional fixes (see docs/RUST_LEARNING.md): the original crashed on every
//! message that contained a band member, album or song name
//! (`'dict' object has no attribute 'dict'`), and its `history` command showed
//! an empty "Bot:" line. Both work here. Everything else (the commands, the
//! wording, the debug output) is kept.

use std::io::{self, BufRead, Write};

use serde_json::{Map, Value, json};

use crate::errors::RhcpError;
use crate::inference::Inference;

pub struct ChatCli<'a> {
    inference: &'a Inference,
    session_id: String,
    pub debug: bool,
    pub json_output: bool,
}

const HELP_TEXT: &str = "RHCP Chatbot Help
=================

This chatbot can answer questions about the Red Hot Chili Peppers, including:
- Band members and their biographies
- Albums and their details
- Songs and their information
- Band history and formation

Commands:
- help: Show this help message
- history: Show conversation history
- commands: List available commands
- quit/exit/bye: End the session

Examples:
- \"Who is in the band?\"
- \"Tell me about Californication\"
- \"What year was RHCP formed?\"
- \"Who wrote Under the Bridge?\"";

const COMMANDS_TEXT: &str = "Available Commands:
==================
- help: Show help information
- history: Show conversation history
- commands: List available commands
- quit/exit/bye: End the session

You can also ask questions about RHCP members, albums, songs, and history!";

fn command_response(message: &str, intent: &str) -> Map<String, Value> {
    json!({"message": message, "intent": intent, "confidence": 1.0, "entities": []})
        .as_object()
        .unwrap()
        .clone()
}

impl<'a> ChatCli<'a> {
    pub fn new(inference: &'a Inference, debug: bool, json_output: bool) -> Self {
        let session_id = inference.with_memory(|m| m.create_session());
        Self {
            inference,
            session_id,
            debug,
            json_output,
        }
    }

    pub fn send_message(&self, message: &str) -> Result<Map<String, Value>, RhcpError> {
        if message.trim().is_empty() {
            return Err(RhcpError::invalid_input("Message cannot be empty or whitespace"));
        }
        let message = message.trim();
        if message.chars().count() > 2000 {
            return Err(RhcpError::invalid_input("Message too long (max 2000 characters)"));
        }

        match message.to_lowercase().as_str() {
            "help" => return Ok(command_response(HELP_TEXT, "command.help")),
            "history" => return Ok(self.history()),
            "quit" | "exit" | "bye" => {
                return Ok(command_response(
                    "Goodbye! Thanks for chatting about RHCP. Come back anytime!",
                    "command.quit",
                ));
            }
            "commands" => return Ok(command_response(COMMANDS_TEXT, "command.list")),
            _ => {}
        }

        let response = self.inference.run_inference(message, Some(&self.session_id))?;
        let mut result = serde_json::to_value(&response)
            .map_err(|e| RhcpError::processing(e.to_string()))?
            .as_object()
            .cloned()
            .unwrap_or_default();
        result.insert("message".into(), json!(response.final_message));

        if self.debug {
            let top = self
                .inference
                .processor()
                .nlu()
                .classifications(&message.to_lowercase());
            eprintln!("┌─────────────────────────────────────────────────────────────┐");
            eprintln!("│                    Top 3 Intents                            │");
            eprintln!("├─────────────────────────────────────────────────────────────┤");
            for (i, (label, value)) in top.iter().take(3).enumerate() {
                eprintln!("│ {}. {:<30} {:.3} │", i + 1, label, value);
            }
            eprintln!("└─────────────────────────────────────────────────────────────┘");
        }
        Ok(result)
    }

    fn history(&self) -> Map<String, Value> {
        let history = self
            .inference
            .with_memory(|m| m.conversation_history(&self.session_id, 10));
        if history.is_empty() {
            return command_response("No conversation history yet.", "command.history");
        }
        let mut text = String::from("Conversation History:\n");
        for (i, entry) in history.iter().enumerate() {
            text.push_str(&format!("\nTurn {}:\n", i + 1));
            text.push_str(&format!("  You: {}\n", entry.user_message));
            text.push_str(&format!("  Bot: {}\n", entry.bot_message));
            text.push_str(&format!(
                "  Intent: {} ({:.3})\n",
                entry.intent.as_deref().unwrap_or("unknown"),
                entry.confidence.unwrap_or(0.0)
            ));
        }
        command_response(&text, "command.history")
    }

    pub fn print_response(&self, response: &Map<String, Value>) {
        if self.json_output {
            println!("{}", crate::pyjson::dumps_pretty(&Value::Object(response.clone())));
            return;
        }
        println!("\n{}", response.get("message").and_then(Value::as_str).unwrap_or(""));
        if self.debug {
            println!(
                "\n[DEBUG] Intent: {} (confidence: {:.3})",
                response.get("intent").and_then(Value::as_str).unwrap_or(""),
                response.get("confidence").and_then(Value::as_f64).unwrap_or(0.0)
            );
            if let Some(entities) = response
                .get("entities")
                .and_then(Value::as_array)
                .filter(|e| !e.is_empty())
            {
                println!("[DEBUG] Entities: {} found", entities.len());
                for e in entities {
                    println!(
                        "  - {}: {}",
                        e.get("type").and_then(Value::as_str).unwrap_or("unknown"),
                        e.get("value")
                            .and_then(|v| v.get("name"))
                            .and_then(Value::as_str)
                            .unwrap_or("unknown")
                    );
                }
            }
        }
    }

    /// Interactive loop (one line per message). Ends on a quit command or end of input.
    pub fn run_interactive(&self) {
        println!("RHCP Chatbot CLI");
        println!("Type 'help' for commands, 'quit' to exit");
        println!("{}", "=".repeat(50));
        let stdin = io::stdin();
        loop {
            print!("\nYou: ");
            let _ = io::stdout().flush();
            let mut line = String::new();
            match stdin.lock().read_line(&mut line) {
                Ok(0) => {
                    println!("\nGoodbye!");
                    break;
                }
                Ok(_) => {}
                Err(_) => break,
            }
            let input = line.trim();
            if input.is_empty() {
                continue;
            }
            match self.send_message(input) {
                Ok(response) => {
                    self.print_response(&response);
                    if response.get("intent").and_then(Value::as_str) == Some("command.quit") {
                        break;
                    }
                }
                Err(e) if e.kind == crate::errors::ErrorKind::InvalidInput => println!("Error: {}", e.message),
                Err(e) => println!("Unexpected error: {}", e.message),
            }
        }
    }
}
