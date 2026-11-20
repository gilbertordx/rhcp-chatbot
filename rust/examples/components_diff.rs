//! Helper for the component-level Python-vs-Rust comparisons (run from the repo root).
//!   components_diff forced <pairs.json>   [[message, intent], ...]  -> build_response with a FORCED intent
//!   components_diff facts                 -> every (type, canonical) in the facts DB: facts + all four formatters
//!   components_diff resolver <spans.json> -> resolve_member/album/song/entity for each span
//!   components_diff search <queries.json> -> search_facts for each query
use rhcp_chatbot::{
    app, config::Settings, inference, resolver::KnowledgeResolver, schemas::Intent, search::FactSearchEngine,
};
use serde_json::{Value, json};
use std::path::Path;

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let settings = Settings::from_env().unwrap();
    match args[1].as_str() {
        "forced" => {
            let pairs: Vec<(String, String)> =
                serde_json::from_str(&std::fs::read_to_string(&args[2]).unwrap()).unwrap();
            let inf = app::initialize(&settings).unwrap();
            let out: Vec<Value> = pairs
                .iter()
                .map(|(msg, intent)| {
                    let (raw_i, raw_c, raw_e) = inf.classify(msg);
                    let ents = inf.canonicalize_entities(&raw_e);
                    let r = inf.build_response(Intent::from_label(intent).unwrap(), 0.9, ents, &raw_i, raw_c, None);
                    serde_json::to_value(r.unwrap()).unwrap()
                })
                .collect();
            println!("@@JSON@@{}", Value::Array(out));
        }
        "facts" => {
            let engine = FactSearchEngine::open(Path::new(&settings.fts_db_path)).unwrap();
            let mut out = serde_json::Map::new();
            for kind in ["member", "album", "song"] {
                let mut canon: Vec<String> = engine
                    .get_facts_by_type(kind, 100000)
                    .into_iter()
                    .map(|f| f.canonical)
                    .collect();
                canon.sort();
                canon.dedup();
                for c in canon {
                    let facts = engine.get_facts_by_canonical(&c, Some(kind)).unwrap();
                    out.insert(
                        format!("{kind}|{c}"),
                        json!({
                            "facts": facts.iter().map(|f| json!([f.id, f.kind, f.canonical, f.field, f.value, f.year, f.source])).collect::<Vec<_>>(),
                            "member": inference::member_response(&facts, &c),
                            "album": inference::album_response(&facts, &c),
                            "song": inference::song_response(&facts, &c),
                            "generic": inference::generic_response(&facts, &c),
                        }),
                    );
                }
            }
            println!("@@JSON@@{}", Value::Object(out));
        }
        "resolver" => {
            let spans: Vec<String> = serde_json::from_str(&std::fs::read_to_string(&args[2]).unwrap()).unwrap();
            let r = KnowledgeResolver::load(Path::new(&settings.knowledge_dir));
            let name = |v: Option<serde_json::Map<String, Value>>| {
                v.map(|m| m.get("canonical").cloned().unwrap_or(Value::Null))
                    .unwrap_or(Value::Null)
            };
            let out: Vec<Value> = spans
                .iter()
                .map(|s| json!({
                    "member": name(r.resolve_member(s)), "album": name(r.resolve_album(s)), "song": name(r.resolve_song(s)),
                    "any": name(r.resolve_entity(s, None)), "norm": r.normalize_span(s),
                }))
                .collect();
            println!("@@JSON@@{}", Value::Array(out));
        }
        "search" => {
            let queries: Vec<String> = serde_json::from_str(&std::fs::read_to_string(&args[2]).unwrap()).unwrap();
            let engine = FactSearchEngine::open(Path::new(&settings.fts_db_path)).unwrap();
            let out: Vec<Value> = queries
                .iter()
                .flat_map(|q| {
                    [None, Some("member"), Some("song")]
                        .into_iter()
                        .map(move |t| (q.clone(), t))
                })
                .map(|(q, t)| {
                    let hits = engine.search_facts(&q, 5, t);
                    json!(hits.iter().map(|f| f.id).collect::<Vec<_>>())
                })
                .collect();
            println!("@@JSON@@{}", Value::Array(out));
        }
        other => panic!("unknown mode {other}"),
    }
}
