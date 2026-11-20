//! Command-line entry point: `rhcp-chatbot <command>`.
//!
//! The Python project had several entry points (`uvicorn app.main:app`, `cli.py`,
//! `scripts/build_fts.py`, `app/scripts/setup_nltk.py`, `scripts/training/...`);
//! here they are subcommands of one program.

use std::path::PathBuf;
use std::sync::Arc;

use anyhow::{Context, Result};
use clap::{Parser, Subcommand};

use rhcp_chatbot::api::{self, AppState};
use rhcp_chatbot::app::{self, CLI_MEMORY};
use rhcp_chatbot::auth::AuthService;
use rhcp_chatbot::cli::ChatCli;
use rhcp_chatbot::config::{DEFAULT_SECRET, Settings};
use rhcp_chatbot::{fts_builder, nltk_setup};

#[derive(Parser)]
#[command(name = "rhcp-chatbot", version, about = "Red Hot Chili Peppers trivia chatbot")]
struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Subcommand)]
enum Command {
    /// Start the HTTP API (Python: `uvicorn app.main:app`).
    Serve {
        /// Overrides RHCP_HOST.
        #[arg(long)]
        host: Option<String>,
        /// Overrides RHCP_PORT.
        #[arg(long)]
        port: Option<u16>,
    },
    /// Chat in the terminal (Python: `python cli.py`).
    Chat {
        /// Send one message and exit.
        #[arg(short, long)]
        message: Option<String>,
        /// Show the top intents and entities.
        #[arg(long)]
        debug: bool,
        /// Print responses as JSON.
        #[arg(long)]
        json: bool,
        /// Accepted for compatibility; remote API mode was never implemented.
        #[arg(long)]
        api_url: Option<String>,
        /// Accepted for compatibility; remote API mode was never implemented.
        #[arg(long)]
        use_api: bool,
    },
    /// Rebuild the SQLite fact database from the YAML files (Python: `scripts/build_fts.py`).
    BuildFts {
        #[arg(long, default_value = "data/rhcp_fts.sqlite")]
        db_path: PathBuf,
        #[arg(long, default_value = "data/knowledge")]
        knowledge_dir: PathBuf,
    },
    /// Download the NLTK sentence-splitter data (Python: `app/scripts/setup_nltk.py`).
    SetupNltk,
    /// Train the intent classifier from the corpora (Python: `train_new_model`).
    Train {
        /// Where to write the model (default: RHCP_MODEL_PATH).
        #[arg(long)]
        out: Option<PathBuf>,
        /// Gradient tolerance; scikit-learn's default is 1e-4. Smaller = closer to the exact optimum.
        #[arg(long, default_value_t = 1e-4)]
        tol: f64,
        #[arg(long, default_value_t = 1000)]
        max_iter: usize,
    },
}

fn init_logging(settings: &Settings, debug: bool) {
    let level = if debug {
        "debug".to_string()
    } else {
        settings.log_level.to_lowercase()
    };
    let filter =
        tracing_subscriber::EnvFilter::try_new(format!("rhcp_chatbot={level},warn")).unwrap_or_else(|_| "info".into());
    let builder = tracing_subscriber::fmt()
        .with_env_filter(filter)
        .with_writer(std::io::stderr);
    if settings.log_format == "json" {
        builder.json().init()
    } else {
        builder.init()
    }
}

fn main() -> Result<()> {
    let _ = dotenvy::dotenv(); // like python-dotenv: load a .env file if there is one
    let cli = Cli::parse();
    match cli.command {
        Command::Serve { host, port } => {
            let mut settings = Settings::from_env()?;
            if let Some(h) = host {
                settings.host = h;
            }
            if let Some(p) = port {
                settings.port = p;
            }
            init_logging(&settings, settings.debug);
            if settings.secret_key == DEFAULT_SECRET {
                tracing::warn!("SECRET_KEY is the built-in default; set SECRET_KEY before exposing this server");
            }
            tracing::info!("Starting RHCP Chatbot application");
            let inference = Arc::new(app::initialize(&settings)?);
            let auth = Arc::new(AuthService::open(
                &settings.auth_database_path,
                &settings.secret_key,
                settings.access_token_expire_minutes,
            )?);
            let router = api::router(AppState {
                inference: inference.clone(),
                auth,
            });
            let addr = format!("{}:{}", settings.host, settings.port);

            tokio::runtime::Runtime::new()?.block_on(async move {
                let listener = tokio::net::TcpListener::bind(&addr)
                    .await
                    .with_context(|| format!("binding {addr}"))?;
                tracing::info!("Application startup completed successfully; listening on http://{addr}");
                axum::serve(listener, router)
                    .with_graceful_shutdown(async {
                        let _ = tokio::signal::ctrl_c().await;
                    })
                    .await?;
                tracing::info!("Shutting down RHCP Chatbot application");
                inference.with_memory(|m| m.cleanup_old_sessions());
                Ok::<(), anyhow::Error>(())
            })
        }

        Command::Chat {
            message,
            debug,
            json,
            api_url: _,
            use_api,
        } => {
            let settings = Settings::from_env()?;
            init_logging(&settings, debug);
            if use_api {
                println!("API mode not yet implemented");
                return Ok(());
            }
            let inference = match app::initialize_with(&settings, CLI_MEMORY) {
                Ok(i) => i,
                Err(e) => {
                    println!("Failed to initialize chatbot: {e:#}");
                    std::process::exit(1);
                }
            };
            let cli = ChatCli::new(&inference, debug, json);
            match message {
                Some(m) => match cli.send_message(&m) {
                    Ok(response) => cli.print_response(&response),
                    Err(e) => {
                        println!("Error: {}", e.message);
                        std::process::exit(1);
                    }
                },
                None => cli.run_interactive(),
            }
            Ok(())
        }

        Command::BuildFts { db_path, knowledge_dir } => fts_builder::build_database(&db_path, &knowledge_dir)
            .map(|_| {
                println!(
                    "FTS database built successfully!\nDatabase location: {}",
                    db_path.display()
                )
            })
            .inspect_err(|e| eprintln!("Failed to build FTS database: {e:#}")),

        Command::SetupNltk => nltk_setup::run(),

        Command::Train { out, tol, max_iter } => {
            use rhcp_chatbot::data::TrainingData;
            use rhcp_chatbot::nlp::{classifier, tokenizer::TextAnalyzer, trainer};
            let settings = Settings::from_env()?;
            let training = TrainingData::load(std::path::Path::new(&settings.training_dir));
            let (texts, intents) = training.samples();
            anyhow::ensure!(!texts.is_empty(), "no training data found in {}", settings.training_dir);
            let analyzer = TextAnalyzer::from_nltk_data()?;
            println!("Training on {} samples...", texts.len());
            let started = std::time::Instant::now();
            let cfg = trainer::TrainConfig {
                tol,
                max_iter,
                ..Default::default()
            };
            let (model, report) = trainer::train(&analyzer, &texts, &intents, &cfg);
            let out = out.unwrap_or_else(|| PathBuf::from(&settings.model_path));
            classifier::save_model(&model, &out)?;
            println!(
                "{} classes, {} terms, {} optimiser iterations, training accuracy {:.1}% ({:.1}s)\nModel saved to {}",
                report.classes,
                report.terms,
                report.iterations,
                report.train_accuracy * 100.0,
                started.elapsed().as_secs_f64(),
                out.display()
            );
            Ok(())
        }
    }
}
