//! Builds the SQLite full-text fact database from the YAML knowledge files.
//! Python equivalent: `scripts/build_fts.py`.
//!
//! One "fact" is one row: (type, canonical name, field, value, year, source file),
//! e.g. `("member", "flea", "role", "bass", NULL, "members.yml")`.

use std::fs;
use std::path::Path;

use anyhow::{Context, Result};
use rusqlite::{Connection, params};
use serde_json::Value;

use crate::pyfmt::py_str;

const SCHEMA_SQL: &str = "
CREATE TABLE IF NOT EXISTS facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,           -- 'member', 'album', 'song'
    canonical TEXT NOT NULL,      -- Canonical name/title
    field TEXT NOT NULL,          -- Field name (e.g., 'name', 'title', 'year', 'role')
    value TEXT NOT NULL,          -- Field value
    year INTEGER,                 -- Year (if applicable)
    source TEXT NOT NULL,         -- Source file
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts USING fts5(
    type, canonical, field, value, year, source,
    content='facts', content_rowid='id'
);

CREATE INDEX IF NOT EXISTS idx_facts_type ON facts(type);
CREATE INDEX IF NOT EXISTS idx_facts_canonical ON facts(canonical);
CREATE INDEX IF NOT EXISTS idx_facts_field ON facts(field);
CREATE INDEX IF NOT EXISTS idx_facts_year ON facts(year);

CREATE TRIGGER IF NOT EXISTS facts_ai AFTER INSERT ON facts BEGIN
    INSERT INTO facts_fts(type, canonical, field, value, year, source)
    VALUES (new.type, new.canonical, new.field, new.value, new.year, new.source);
END;

CREATE TRIGGER IF NOT EXISTS facts_ad AFTER DELETE ON facts BEGIN
    INSERT INTO facts_fts(facts_fts, type, canonical, field, value, year, source)
    VALUES('delete', old.type, old.canonical, old.field, old.value, old.year, old.source);
END;

CREATE TRIGGER IF NOT EXISTS facts_au AFTER UPDATE ON facts BEGIN
    INSERT INTO facts_fts(facts_fts, type, canonical, field, value, year, source)
    VALUES('delete', old.type, old.canonical, old.field, old.value, old.year, old.source);
    INSERT INTO facts_fts(type, canonical, field, value, year, source)
    VALUES (new.type, new.canonical, new.field, new.value, new.year, new.source);
END;
";

struct NewFact {
    kind: &'static str,
    canonical: String,
    field: &'static str,
    value: String,
    year: Option<i64>,
    source: &'static str,
}

/// Python truthiness of a YAML value (`if x:`).
fn truthy(v: &Value) -> bool {
    match v {
        Value::Null => false,
        Value::Bool(b) => *b,
        Value::Number(n) => n.as_f64().is_some_and(|f| f != 0.0),
        Value::String(s) => !s.is_empty(),
        Value::Array(a) => !a.is_empty(),
        Value::Object(o) => !o.is_empty(),
    }
}

fn text(record: &Value, key: &str) -> String {
    record.get(key).map(py_str).filter(|s| s != "None").unwrap_or_default()
}

fn list<'a>(record: &'a Value, key: &str) -> &'a [Value] {
    record
        .get(key)
        .and_then(Value::as_array)
        .map(Vec::as_slice)
        .unwrap_or(&[])
}

/// A single-valued field, only when it has a truthy value; `year_too` also records the number.
fn push_scalar(
    facts: &mut Vec<NewFact>,
    rec: &Value,
    kind: &'static str,
    source: &'static str,
    key: &'static str,
    year_too: bool,
) {
    if let Some(v) = rec.get(key).filter(|v| truthy(v)) {
        facts.push(NewFact {
            kind,
            canonical: text(rec, "canonical"),
            field: key,
            value: py_str(v),
            year: if year_too { v.as_i64() } else { None },
            source,
        });
    }
}

fn push_each(
    facts: &mut Vec<NewFact>,
    rec: &Value,
    kind: &'static str,
    source: &'static str,
    key: &str,
    field: &'static str,
    year_too: bool,
) {
    for item in list(rec, key) {
        facts.push(NewFact {
            kind,
            canonical: text(rec, "canonical"),
            field,
            value: py_str(item),
            year: if year_too { item.as_i64() } else { None },
            source,
        });
    }
}

fn first_fact(
    facts: &mut Vec<NewFact>,
    rec: &Value,
    kind: &'static str,
    source: &'static str,
    name_key: &str,
    field: &'static str,
) {
    facts.push(NewFact {
        kind,
        canonical: text(rec, "canonical"),
        field,
        value: text(rec, name_key),
        year: None,
        source,
    });
}

fn member_facts(m: &Value) -> Vec<NewFact> {
    let (k, s) = ("member", "members.yml");
    let mut f = Vec::new();
    first_fact(&mut f, m, k, s, "name", "name");
    push_each(&mut f, m, k, s, "aliases", "alias", false);
    push_each(&mut f, m, k, s, "roles", "role", false);
    push_scalar(&mut f, m, k, s, "join_year", true);
    push_each(&mut f, m, k, s, "leave_years", "leave_year", true);
    push_scalar(&mut f, m, k, s, "notes", false);
    // `active` is recorded even when false: Python tested `is not None`.
    if let Some(v) = m.get("active").filter(|v| !v.is_null()) {
        f.push(NewFact {
            kind: k,
            canonical: text(m, "canonical"),
            field: "active",
            value: py_str(v),
            year: None,
            source: s,
        });
    }
    f
}

fn album_facts(a: &Value) -> Vec<NewFact> {
    let (k, s) = ("album", "albums.yml");
    let mut f = Vec::new();
    first_fact(&mut f, a, k, s, "title", "title");
    push_each(&mut f, a, k, s, "aliases", "alias", false);
    push_scalar(&mut f, a, k, s, "year", true);
    push_scalar(&mut f, a, k, s, "label", false);
    push_scalar(&mut f, a, k, s, "lineup_hint", false);
    push_scalar(&mut f, a, k, s, "notes", false);
    push_scalar(&mut f, a, k, s, "tracks", false);
    f
}

fn song_facts(song: &Value) -> Vec<NewFact> {
    let (k, s) = ("song", "songs.yml");
    let mut f = Vec::new();
    first_fact(&mut f, song, k, s, "title", "title");
    push_each(&mut f, song, k, s, "aliases", "alias", false);
    push_scalar(&mut f, song, k, s, "year", true);
    push_scalar(&mut f, song, k, s, "album", false);
    push_scalar(&mut f, song, k, s, "track_no", false);
    push_scalar(&mut f, song, k, s, "notes", false);
    push_each(&mut f, song, k, s, "writers", "writer", false);
    f
}

fn load_yaml(path: &Path) -> Value {
    fs::read_to_string(path)
        .ok()
        .and_then(|t| serde_yaml_ng::from_str(&t).ok())
        .unwrap_or(Value::Null)
}

/// Rebuild the database from scratch. Returns the number of facts inserted.
pub fn build_database(db_path: &Path, knowledge_dir: &Path) -> Result<usize> {
    if let Some(dir) = db_path.parent() {
        fs::create_dir_all(dir)?;
    }
    if db_path.exists() {
        fs::remove_file(db_path).with_context(|| format!("removing {}", db_path.display()))?;
        println!("Removed existing database");
    }
    let mut conn = Connection::open(db_path)?;
    conn.execute_batch(SCHEMA_SQL)?;
    println!("Created database schema");

    let mut all: Vec<NewFact> = Vec::new();
    for (file, key, extract) in [
        ("members.yml", "members", member_facts as fn(&Value) -> Vec<NewFact>),
        ("albums.yml", "albums", album_facts),
        ("songs.yml", "songs", song_facts),
    ] {
        let path = knowledge_dir.join(file);
        if path.exists() {
            let doc = load_yaml(&path);
            for record in list(&doc, key) {
                all.extend(extract(record));
            }
        }
    }

    let tx = conn.transaction()?;
    {
        let mut insert = tx.prepare(
            "INSERT INTO facts (type, canonical, field, value, year, source) VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
        )?;
        for f in &all {
            insert.execute(params![f.kind, f.canonical, f.field, f.value, f.year, f.source])?;
        }
    }
    tx.commit()?;
    conn.execute("INSERT INTO facts_fts(facts_fts) VALUES('optimize')", [])?;

    println!("Inserted {} facts into database", all.len());
    let total: i64 = conn.query_row("SELECT COUNT(*) FROM facts", [], |r| r.get(0))?;
    println!("Database statistics:\n  Total facts: {total}");
    let mut stmt = conn.prepare("SELECT type, COUNT(*) FROM facts GROUP BY type")?;
    for row in stmt.query_map([], |r| Ok((r.get::<_, String>(0)?, r.get::<_, i64>(1)?)))? {
        let (kind, count) = row?;
        println!("  {kind}: {count} facts");
    }
    Ok(all.len())
}
