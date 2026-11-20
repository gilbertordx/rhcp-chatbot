//! Fact lookup in the SQLite full-text-search database.
//! Python equivalent: `app/knowledge/search.py` (`FactSearchEngine`).
//!
//! The database (`data/rhcp_fts.sqlite`) holds one row per fact in table `facts`
//! plus an FTS5 index `facts_fts`. `rusqlite` with its `bundled` feature compiles
//! SQLite into the program, so no system SQLite is needed.

use std::path::{Path, PathBuf};

use anyhow::{Result, bail};
use rusqlite::{Connection, params};
use serde_json::{Value, json};

#[derive(Debug, Clone, PartialEq)]
pub struct Fact {
    pub id: i64,
    pub kind: String,
    pub canonical: String,
    pub field: String,
    pub value: String,
    pub year: Option<i64>,
    pub source: String,
}

pub struct FactSearchEngine {
    db_path: PathBuf,
}

fn row_to_fact(row: &rusqlite::Row<'_>) -> rusqlite::Result<Fact> {
    Ok(Fact {
        id: row.get(0)?,
        kind: row.get(1)?,
        canonical: row.get(2)?,
        field: row.get(3)?,
        value: row.get(4)?,
        year: row.get(5)?,
        source: row.get(6)?,
    })
}

impl FactSearchEngine {
    /// Open and validate the database (it must have `facts`, `facts_fts` and rows).
    pub fn open(path: &Path) -> Result<Self> {
        if !path.exists() {
            bail!("FTS database not found: {}", path.display());
        }
        let engine = Self {
            db_path: path.to_path_buf(),
        };
        let conn = engine.connect()?;
        let has_table = |name: &str| -> rusqlite::Result<bool> {
            conn.query_row(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?1",
                [name],
                |_| Ok(()),
            )
            .map(|_| true)
            .or_else(|e| match e {
                rusqlite::Error::QueryReturnedNoRows => Ok(false),
                other => Err(other),
            })
        };
        if !has_table("facts")? {
            bail!("Database missing 'facts' table");
        }
        if !has_table("facts_fts")? {
            bail!("Database missing 'facts_fts' table");
        }
        let count: i64 = conn.query_row("SELECT COUNT(*) FROM facts", [], |r| r.get(0))?;
        if count == 0 {
            bail!("Database has no facts");
        }
        Ok(engine)
    }

    fn connect(&self) -> Result<Connection> {
        Ok(Connection::open(&self.db_path)?)
    }

    /// Full-text search. Errors (e.g. bad FTS syntax) give an empty list, like the Python.
    pub fn search_facts(&self, query: &str, k: usize, fact_type: Option<&str>) -> Vec<Fact> {
        let query = query.trim();
        if query.is_empty() {
            return Vec::new();
        }
        let run = || -> Result<Vec<Fact>> {
            let conn = self.connect()?;
            let facts = match fact_type {
                Some(t) => {
                    let mut stmt = conn.prepare(
                        "SELECT f.id, f.type, f.canonical, f.field, f.value, f.year, f.source \
                         FROM facts_fts JOIN facts f ON f.id = facts_fts.rowid \
                         WHERE facts_fts.type = ?1 AND facts_fts MATCH ?2 LIMIT ?3",
                    )?;
                    stmt.query_map(params![t, query, k as i64], row_to_fact)?
                        .collect::<Result<Vec<_>, _>>()?
                }
                None => {
                    let mut stmt = conn.prepare(
                        "SELECT f.id, f.type, f.canonical, f.field, f.value, f.year, f.source \
                         FROM facts_fts JOIN facts f ON f.id = facts_fts.rowid \
                         WHERE facts_fts MATCH ?1 LIMIT ?2",
                    )?;
                    stmt.query_map(params![query, k as i64], row_to_fact)?
                        .collect::<Result<Vec<_>, _>>()?
                }
            };
            Ok(facts)
        };
        run().unwrap_or_default()
    }

    /// Every fact about one canonical name (`ORDER BY field, value`).
    pub fn get_facts_by_canonical(&self, canonical: &str, fact_type: Option<&str>) -> Result<Vec<Fact>> {
        let conn = self.connect()?;
        let facts = match fact_type {
            Some(t) => {
                let mut stmt = conn.prepare(
                    "SELECT id, type, canonical, field, value, year, source FROM facts \
                     WHERE canonical = ?1 AND type = ?2 ORDER BY field, value",
                )?;
                stmt.query_map(params![canonical, t], row_to_fact)?
                    .collect::<Result<Vec<_>, _>>()?
            }
            None => {
                let mut stmt = conn.prepare(
                    "SELECT id, type, canonical, field, value, year, source FROM facts \
                     WHERE canonical = ?1 ORDER BY field, value",
                )?;
                stmt.query_map(params![canonical], row_to_fact)?
                    .collect::<Result<Vec<_>, _>>()?
            }
        };
        Ok(facts)
    }

    pub fn get_facts_by_type(&self, fact_type: &str, limit: usize) -> Vec<Fact> {
        let run = || -> Result<Vec<Fact>> {
            let conn = self.connect()?;
            let mut stmt = conn.prepare(
                "SELECT id, type, canonical, field, value, year, source FROM facts \
                 WHERE type = ?1 ORDER BY canonical, field LIMIT ?2",
            )?;
            Ok(stmt
                .query_map(params![fact_type, limit as i64], row_to_fact)?
                .collect::<Result<Vec<_>, _>>()?)
        };
        run().unwrap_or_default()
    }

    pub fn database_stats(&self) -> Option<Value> {
        let run = || -> Result<Value> {
            let conn = self.connect()?;
            let total: i64 = conn.query_row("SELECT COUNT(*) FROM facts", [], |r| r.get(0))?;
            let group = |sql: &str| -> Result<serde_json::Map<String, Value>> {
                let mut stmt = conn.prepare(sql)?;
                let rows = stmt.query_map([], |r| Ok((r.get::<_, String>(0)?, r.get::<_, i64>(1)?)))?;
                Ok(rows
                    .collect::<Result<Vec<_>, _>>()?
                    .into_iter()
                    .map(|(k, v)| (k, json!(v)))
                    .collect())
            };
            Ok(json!({
                "total_facts": total,
                "type_counts": group("SELECT type, COUNT(*) FROM facts GROUP BY type")?,
                "source_counts": group("SELECT source, COUNT(*) FROM facts GROUP BY source")?,
                "database_size_bytes": std::fs::metadata(&self.db_path)?.len(),
                "database_path": self.db_path.display().to_string(),
            }))
        };
        run().ok()
    }

    /// Row count used by the readiness check (`SELECT COUNT(*) FROM facts`).
    pub fn fact_count(path: &Path) -> Result<i64> {
        let conn = Connection::open(path)?;
        Ok(conn.query_row("SELECT COUNT(*) FROM facts", [], |r| r.get(0))?)
    }
}
