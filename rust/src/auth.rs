//! Users, login sessions, password hashing and JWT tokens.
//! Python equivalents: `app/models/user.py`, `app/core/database.py` and
//! `app/services/auth.py`.
//!
//! The SQLite file layout and the stored date formats are identical to what
//! SQLAlchemy wrote, so an existing `rhcp_chatbot.db` works unchanged, and
//! tokens/hashes made by the Python app are accepted here (and vice versa):
//! passwords are bcrypt `$2b$` hashes, tokens are HS256 JWTs with the same claims.

use std::path::Path;
use std::sync::Mutex;

use anyhow::Result;
use chrono::{Duration, NaiveDateTime, Utc};
use jsonwebtoken::{Algorithm, DecodingKey, EncodingKey, Header, Validation};
use regex::Regex;
use rusqlite::{Connection, OptionalExtension, Row, params};
use serde::{Deserialize, Serialize};
use serde_json::{Map, Value, json};

/// SQLAlchemy `create_all` output, made idempotent with `IF NOT EXISTS`.
const SCHEMA: &str = "
CREATE TABLE IF NOT EXISTS users (
    id INTEGER NOT NULL,
    username VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    is_active BOOLEAN,
    is_admin BOOLEAN,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME,
    last_login DATETIME,
    PRIMARY KEY (id)
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username);
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email);
CREATE INDEX IF NOT EXISTS ix_users_id ON users (id);
CREATE TABLE IF NOT EXISTS user_sessions (
    id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    session_id VARCHAR(255) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL,
    is_active BOOLEAN,
    PRIMARY KEY (id)
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_user_sessions_session_id ON user_sessions (session_id);
CREATE INDEX IF NOT EXISTS ix_user_sessions_id ON user_sessions (id);
";

/// Error text bcrypt 5.x raises for long passwords (the original surfaced it as a 400 on register).
pub const PASSWORD_TOO_LONG: &str =
    "password cannot be longer than 72 bytes, truncate manually if necessary (e.g. my_password[:72])";

#[derive(Debug, thiserror::Error)]
pub enum AuthError {
    /// A rule the user broke; shown to them as a 400.
    #[error("{0}")]
    Invalid(String),
    /// Something unexpected (database, hashing); shown as a 500.
    #[error("{0}")]
    Internal(String),
}

impl From<rusqlite::Error> for AuthError {
    fn from(e: rusqlite::Error) -> Self {
        AuthError::Internal(e.to_string())
    }
}

#[derive(Debug, Clone)]
pub struct User {
    pub id: i64,
    pub username: String,
    pub email: String,
    pub password_hash: String,
    pub first_name: Option<String>,
    pub last_name: Option<String>,
    pub is_active: bool,
    pub is_admin: bool,
    pub created_at: Option<String>,
    pub last_login: Option<String>,
}

/// `datetime.isoformat()` of a stored `YYYY-MM-DD HH:MM:SS[.ffffff]` text:
/// microseconds are shown only when they are not zero.
pub fn iso_from_stored(text: &str) -> String {
    match NaiveDateTime::parse_from_str(text, "%Y-%m-%d %H:%M:%S%.f") {
        Ok(dt) if dt.and_utc().timestamp_subsec_micros() == 0 => dt.format("%Y-%m-%dT%H:%M:%S").to_string(),
        Ok(dt) => dt.format("%Y-%m-%dT%H:%M:%S%.6f").to_string(),
        Err(_) => text.to_string(),
    }
}

impl User {
    /// Public fields only (Python `to_dict`): never the password hash.
    pub fn to_dict(&self) -> Map<String, Value> {
        let mut m = Map::new();
        m.insert("id".into(), json!(self.id));
        m.insert("username".into(), json!(self.username));
        m.insert("email".into(), json!(self.email));
        m.insert("first_name".into(), json!(self.first_name));
        m.insert("last_name".into(), json!(self.last_name));
        m.insert("is_active".into(), json!(self.is_active));
        m.insert("is_admin".into(), json!(self.is_admin));
        m.insert(
            "created_at".into(),
            json!(self.created_at.as_deref().map(iso_from_stored)),
        );
        m.insert(
            "last_login".into(),
            json!(self.last_login.as_deref().map(iso_from_stored)),
        );
        m
    }
}

/// Stored form of "now" (UTC, microseconds), as SQLAlchemy wrote datetimes.
fn now_stored() -> String {
    Utc::now().format("%Y-%m-%d %H:%M:%S%.6f").to_string()
}

fn row_to_user(row: &Row<'_>) -> rusqlite::Result<User> {
    Ok(User {
        id: row.get("id")?,
        username: row.get("username")?,
        email: row.get("email")?,
        password_hash: row.get("password_hash")?,
        first_name: row.get("first_name")?,
        last_name: row.get("last_name")?,
        is_active: row.get::<_, Option<bool>>("is_active")?.unwrap_or(false),
        is_admin: row.get::<_, Option<bool>>("is_admin")?.unwrap_or(false),
        created_at: row.get("created_at")?,
        last_login: row.get("last_login")?,
    })
}

#[derive(Debug, Serialize, Deserialize)]
struct Claims {
    sub: String,
    #[serde(default)]
    username: String,
    #[serde(default)]
    is_admin: bool,
    /// Optional on decode: PyJWT accepts a token with no `exp` claim.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    exp: Option<i64>,
}

pub struct AuthService {
    conn: Mutex<Connection>,
    secret: String,
    token_minutes: i64,
    username_re: Regex,
    email_re: Regex,
}

impl AuthService {
    pub fn open(path: &str, secret: &str, token_minutes: i64) -> Result<Self> {
        let conn = Connection::open(Path::new(path))?;
        conn.execute_batch(SCHEMA)?;
        Ok(Self {
            conn: Mutex::new(conn),
            secret: secret.to_string(),
            token_minutes,
            username_re: Regex::new(r"^[a-zA-Z0-9_]+$")?,
            email_re: Regex::new(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")?,
        })
    }

    fn db(&self) -> std::sync::MutexGuard<'_, Connection> {
        self.conn.lock().expect("database lock")
    }

    // ------------------------------------------------------------ passwords

    /// bcrypt hash at cost 12 (what `bcrypt.gensalt()` defaults to; the original
    /// ignored its `BCRYPT_ROUNDS` setting).
    fn hash_password(password: &str) -> Result<String, AuthError> {
        if password.len() > 72 {
            return Err(AuthError::Invalid(PASSWORD_TOO_LONG.into()));
        }
        bcrypt::hash(password, 12).map_err(|e| AuthError::Internal(e.to_string()))
    }

    fn check_password(password: &str, hash: &str) -> Result<bool, AuthError> {
        if password.len() > 72 {
            // bcrypt 5.x raises here, which the original left unhandled (a 500).
            return Err(AuthError::Internal(PASSWORD_TOO_LONG.into()));
        }
        bcrypt::verify(password, hash).map_err(|e| AuthError::Internal(e.to_string()))
    }

    // ------------------------------------------------------------ users

    pub fn create_user(
        &self,
        username: &str,
        email: &str,
        password: &str,
        first_name: Option<&str>,
        last_name: Option<&str>,
    ) -> Result<User, AuthError> {
        if username.chars().count() < 3 || username.chars().count() > 20 || !self.username_re.is_match(username) {
            return Err(AuthError::Invalid(
                "Username must be 3-20 characters and contain only letters, numbers, and underscores".into(),
            ));
        }
        if !self.email_re.is_match(email) {
            return Err(AuthError::Invalid("Invalid email format".into()));
        }
        if password.chars().count() < 8 {
            return Err(AuthError::Invalid("Password must be at least 8 characters long".into()));
        }
        {
            let db = self.db();
            let exists = |sql: &str, v: &str| -> rusqlite::Result<bool> {
                db.query_row(sql, [v], |_| Ok(())).optional().map(|o| o.is_some())
            };
            if exists("SELECT 1 FROM users WHERE username = ?1", username)? {
                return Err(AuthError::Invalid("Username already exists".into()));
            }
            if exists("SELECT 1 FROM users WHERE email = ?1", email)? {
                return Err(AuthError::Invalid("Email already exists".into()));
            }
        }
        let hash = Self::hash_password(password)?;
        let db = self.db();
        let inserted = db.execute(
            "INSERT INTO users (username, email, password_hash, first_name, last_name, is_active, is_admin) \
             VALUES (?1, ?2, ?3, ?4, ?5, 1, 0)",
            params![username, email, hash, first_name, last_name],
        );
        match inserted {
            Ok(_) => {}
            Err(rusqlite::Error::SqliteFailure(e, _)) if e.code == rusqlite::ErrorCode::ConstraintViolation => {
                return Err(AuthError::Invalid("User creation failed".into()));
            }
            Err(e) => return Err(e.into()),
        }
        let id = db.last_insert_rowid();
        Ok(db.query_row("SELECT * FROM users WHERE id = ?1", [id], row_to_user)?)
    }

    pub fn authenticate_user(&self, username: &str, password: &str) -> Result<Option<User>, AuthError> {
        let user = self.user_by_username(username)?;
        let Some(user) = user else { return Ok(None) };
        if !Self::check_password(password, &user.password_hash)? || !user.is_active {
            return Ok(None);
        }
        Ok(Some(user))
    }

    pub fn user_by_username(&self, username: &str) -> Result<Option<User>, AuthError> {
        Ok(self
            .db()
            .query_row("SELECT * FROM users WHERE username = ?1", [username], row_to_user)
            .optional()?)
    }

    pub fn user_by_id(&self, id: i64) -> Result<Option<User>, AuthError> {
        Ok(self
            .db()
            .query_row("SELECT * FROM users WHERE id = ?1", [id], row_to_user)
            .optional()?)
    }

    pub fn all_users(&self) -> Result<Vec<User>, AuthError> {
        let db = self.db();
        let mut stmt = db.prepare("SELECT * FROM users")?;
        Ok(stmt.query_map([], row_to_user)?.collect::<Result<Vec<_>, _>>()?)
    }

    pub fn update_last_login(&self, user_id: i64) -> Result<(), AuthError> {
        self.db().execute(
            "UPDATE users SET last_login = ?1, updated_at = CURRENT_TIMESTAMP WHERE id = ?2",
            params![now_stored(), user_id],
        )?;
        Ok(())
    }

    /// Change the profile names; only the given fields change.
    pub fn update_profile(&self, user_id: i64, first: Option<&str>, last: Option<&str>) -> Result<(), AuthError> {
        let db = self.db();
        if let Some(f) = first {
            db.execute(
                "UPDATE users SET first_name = ?1, updated_at = CURRENT_TIMESTAMP WHERE id = ?2",
                params![f, user_id],
            )?;
        }
        if let Some(l) = last {
            db.execute(
                "UPDATE users SET last_name = ?1, updated_at = CURRENT_TIMESTAMP WHERE id = ?2",
                params![l, user_id],
            )?;
        }
        Ok(())
    }

    pub fn set_user_active(&self, user_id: i64, active: bool) -> Result<(), AuthError> {
        self.db().execute(
            "UPDATE users SET is_active = ?1, updated_at = CURRENT_TIMESTAMP WHERE id = ?2",
            params![active, user_id],
        )?;
        Ok(())
    }

    // ------------------------------------------------------------ tokens

    pub fn create_access_token(&self, user: &User) -> Result<String, AuthError> {
        let claims = Claims {
            sub: user.id.to_string(),
            username: user.username.clone(),
            is_admin: user.is_admin,
            exp: Some((Utc::now() + Duration::minutes(self.token_minutes)).timestamp()),
        };
        let key = EncodingKey::from_secret(self.secret.as_bytes()).map_err(|e| AuthError::Internal(e.to_string()))?;
        jsonwebtoken::encode(&Header::new(Algorithm::HS256), &claims, &key)
            .map_err(|e| AuthError::Internal(e.to_string()))
    }

    /// The active user a valid token belongs to (any problem -> `None`).
    pub fn user_by_token(&self, token: &str) -> Result<Option<User>, AuthError> {
        let mut validation = Validation::new(Algorithm::HS256);
        validation.leeway = 0; // PyJWT's default
        validation.required_spec_claims.clear(); // PyJWT does not require `exp`
        let Ok(key) = DecodingKey::from_secret(self.secret.as_bytes()) else {
            return Ok(None);
        };
        let Ok(data) = jsonwebtoken::decode::<Claims>(token, &key, &validation) else {
            return Ok(None);
        };
        let Ok(id) = data.claims.sub.parse::<i64>() else {
            return Ok(None);
        };
        Ok(self.user_by_id(id)?.filter(|u| u.is_active))
    }

    // ------------------------------------------------------------ login sessions

    pub fn create_user_session(&self, user_id: i64) -> Result<String, AuthError> {
        let session_id = uuid::Uuid::new_v4().to_string();
        let expires = (Utc::now() + Duration::hours(24))
            .format("%Y-%m-%d %H:%M:%S%.6f")
            .to_string();
        self.db().execute(
            "INSERT INTO user_sessions (user_id, session_id, expires_at, is_active) VALUES (?1, ?2, ?3, 1)",
            params![user_id, session_id, expires],
        )?;
        Ok(session_id)
    }

    pub fn deactivate_session(&self, session_id: &str) -> Result<bool, AuthError> {
        let n = self.db().execute(
            "UPDATE user_sessions SET is_active = 0 WHERE session_id = ?1",
            [session_id],
        )?;
        Ok(n > 0)
    }

    /// Delete expired sessions; returns how many.
    pub fn cleanup_expired_sessions(&self) -> Result<usize, AuthError> {
        Ok(self
            .db()
            .execute("DELETE FROM user_sessions WHERE expires_at < ?1", [now_stored()])?)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn service() -> AuthService {
        AuthService::open(":memory:", "test-secret", 30).unwrap()
    }

    #[test]
    fn registers_logs_in_and_verifies_tokens() {
        let s = service();
        let u = s
            .create_user("alice_1", "alice@example.com", "password123", Some("Al"), None)
            .unwrap();
        assert_eq!(u.id, 1);
        assert!(u.is_active && !u.is_admin);
        assert!(s.authenticate_user("alice_1", "wrong-password").unwrap().is_none());
        let user = s.authenticate_user("alice_1", "password123").unwrap().unwrap();
        let token = s.create_access_token(&user).unwrap();
        assert_eq!(s.user_by_token(&token).unwrap().unwrap().username, "alice_1");
        assert!(s.user_by_token("garbage").unwrap().is_none());
    }

    #[test]
    fn validation_messages() {
        let s = service();
        let msg = |r: Result<User, AuthError>| r.unwrap_err().to_string();
        assert!(msg(s.create_user("a!", "a@b.co", "password123", None, None)).starts_with("Username must be 3-20"));
        assert_eq!(
            msg(s.create_user("bob", "nope", "password123", None, None)),
            "Invalid email format"
        );
        assert_eq!(
            msg(s.create_user("bob", "b@b.co", "short", None, None)),
            "Password must be at least 8 characters long"
        );
        s.create_user("bob", "b@b.co", "password123", None, None).unwrap();
        assert_eq!(
            msg(s.create_user("bob", "x@b.co", "password123", None, None)),
            "Username already exists"
        );
        assert_eq!(
            msg(s.create_user("bobby", "b@b.co", "password123", None, None)),
            "Email already exists"
        );
        assert_eq!(
            msg(s.create_user("long", "l@b.co", &"p".repeat(80), None, None)),
            PASSWORD_TOO_LONG
        );
    }

    #[test]
    fn dates_are_shown_like_python_isoformat() {
        assert_eq!(iso_from_stored("2026-11-20 20:43:18"), "2026-11-20T20:43:18");
        assert_eq!(
            iso_from_stored("2026-11-20 20:43:19.129749"),
            "2026-11-20T20:43:19.129749"
        );
        assert_eq!(iso_from_stored("2026-11-20 20:43:19.000000"), "2026-11-20T20:43:19");
    }

    #[test]
    fn deactivated_users_cannot_use_tokens() {
        let s = service();
        let u = s.create_user("carol", "c@b.co", "password123", None, None).unwrap();
        let token = s.create_access_token(&u).unwrap();
        s.set_user_active(u.id, false).unwrap();
        assert!(s.user_by_token(&token).unwrap().is_none());
    }
}
