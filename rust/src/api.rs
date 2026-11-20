//! The HTTP API. Python equivalents: `app/main.py`, `app/api/routes/chat.py`,
//! `app/api/routes/auth.py`, `app/core/auth.py` and `app/core/session.py`.
//!
//! FastAPI validated every request body with pydantic and produced a detailed
//! `422` error list. axum does not, so the request checks here are written by
//! hand to reproduce the same status codes and the same JSON error shapes
//! (`type`, `loc`, `msg`, `input`), so existing clients keep working.
//!
//! Known difference: for a body that is not valid JSON, the `ctx.error` text is
//! serde's wording mapped to Python's closest message, not always identical.

use std::collections::HashMap;
use std::sync::Arc;
use std::time::Instant;

use axum::body::Bytes;
use axum::extract::{Path, Query, Request, State};
use axum::http::{HeaderMap, HeaderValue, StatusCode, header};
use axum::middleware::{self, Next};
use axum::response::{IntoResponse, Response};
use axum::routing::{get, post, put};
use axum::{Json, Router};
use serde_json::{Map, Value, json};
use tower_http::catch_panic::CatchPanicLayer;
use tower_http::cors::{AllowHeaders, AllowMethods, AllowOrigin, CorsLayer};

use crate::auth::{AuthError, AuthService, User};
use crate::config::Settings;
use crate::inference::Inference;
use crate::schemas::{ChatRequest, ChatResponse, MessageProblem};
use crate::search::FactSearchEngine;

#[derive(Clone)]
pub struct AppState {
    pub inference: Arc<Inference>,
    pub auth: Arc<AuthService>,
}

// ------------------------------------------------------------------ responses

fn internal_error() -> Response {
    (
        StatusCode::INTERNAL_SERVER_ERROR,
        Json(json!({"error": "Internal server error", "remedy": "Please try again later"})),
    )
        .into_response()
}

fn detail(status: StatusCode, message: &str) -> Response {
    (status, Json(json!({ "detail": message }))).into_response()
}

fn unauthorized(message: &str) -> Response {
    let mut r = detail(StatusCode::UNAUTHORIZED, message);
    r.headers_mut()
        .insert(header::WWW_AUTHENTICATE, HeaderValue::from_static("Bearer"));
    r
}

fn validation_error(errors: Vec<Value>) -> Response {
    (StatusCode::UNPROCESSABLE_ENTITY, Json(json!({ "detail": errors }))).into_response()
}

fn auth_error(e: AuthError) -> Response {
    match e {
        AuthError::Invalid(m) => detail(StatusCode::BAD_REQUEST, &m),
        AuthError::Internal(_) => internal_error(),
    }
}

// ------------------------------------------------------------------ request body parsing

/// What FastAPI did with the body: valid JSON, or one of the 422 errors.
fn parse_json_body(headers: &HeaderMap, body: &Bytes) -> Result<Value, Response> {
    let content_type = headers
        .get(header::CONTENT_TYPE)
        .and_then(|v| v.to_str().ok())
        .unwrap_or("")
        .to_lowercase();
    let is_json = content_type.starts_with("application/json")
        || (content_type.starts_with("application/") && content_type.contains("+json"));
    if body.is_empty() {
        return Err(validation_error(vec![
            json!({"type": "missing", "loc": ["body"], "msg": "Field required", "input": null}),
        ]));
    }
    if !is_json {
        // FastAPI treats a non-JSON body as raw text, which is not an object.
        return Err(validation_error(vec![json!({
            "type": "model_attributes_type", "loc": ["body"],
            "msg": "Input should be a valid dictionary or object to extract fields from",
            "input": String::from_utf8_lossy(body)
        })]));
    }
    serde_json::from_slice(body).map_err(|e| {
        let text = String::from_utf8_lossy(body);
        // Python's own wording and character offset when its decoder also rejects the text;
        // otherwise (a few inputs only one of the two parsers accepts) serde's description.
        let (offset, message) = crate::pyjson::python_json_error(&text).unwrap_or_else(|| {
            (
                e.column().saturating_sub(1),
                e.to_string()
                    .split(" at line")
                    .next()
                    .unwrap_or("JSON decode error")
                    .to_string(),
            )
        });
        validation_error(vec![json!({
            "type": "json_invalid", "loc": ["body", offset], "msg": "JSON decode error",
            "input": {}, "ctx": {"error": message}
        })])
    })
}

fn not_an_object(value: &Value) -> Response {
    validation_error(vec![json!({
        "type": "model_attributes_type", "loc": ["body"],
        "msg": "Input should be a valid dictionary or object to extract fields from", "input": value
    })])
}

/// Read a field that must be a string (and, if `required`, present).
fn string_field(body: &Map<String, Value>, name: &str, required: bool, errors: &mut Vec<Value>) -> Option<String> {
    match body.get(name) {
        None if required => {
            errors.push(json!({"type": "missing", "loc": ["body", name], "msg": "Field required", "input": body}));
            None
        }
        None | Some(Value::Null) if !required => None,
        Some(Value::String(s)) => Some(s.clone()),
        Some(other) => {
            errors.push(json!({"type": "string_type", "loc": ["body", name], "msg": "Input should be a valid string", "input": other}));
            None
        }
        _ => None,
    }
}

// ------------------------------------------------------------------ middleware

async fn log_requests(request: Request, next: Next) -> Response {
    let request_id = uuid::Uuid::new_v4().to_string();
    let (method, path) = (request.method().clone(), request.uri().path().to_string());
    tracing::info!(request_id = %request_id, "Request started: {method} {path}");
    let started = Instant::now();
    let response = next.run(request).await;
    tracing::info!(
        request_id = %request_id,
        latency_ms = started.elapsed().as_secs_f64() * 1000.0,
        "Request completed: {method} {path} - {}",
        response.status().as_u16()
    );
    response
}

// ------------------------------------------------------------------ health

async fn healthz() -> Json<Value> {
    Json(json!({"status": "ok", "version": "1.0.0"}))
}

async fn readyz(State(state): State<AppState>) -> Response {
    let _ = &state;
    // Fresh settings on every call, so environment changes are picked up (as the original did).
    let Ok(settings) = Settings::from_env() else {
        return internal_error();
    };
    let mut ready = true;
    let mut details = Map::new();
    details.insert("chatbot_processor".into(), json!("ready"));
    details.insert("memory_manager".into(), json!("ready"));

    let model = std::path::Path::new(&settings.model_path);
    let model_detail = match std::fs::metadata(model) {
        Err(_) if !model.exists() => {
            ready = false;
            format!("not found: {}", settings.model_path)
        }
        Err(e) => {
            ready = false;
            format!("error checking file: {} - {e}", settings.model_path)
        }
        Ok(meta) if std::fs::File::open(model).is_err() => {
            let _ = meta;
            ready = false;
            format!("not readable: {}", settings.model_path)
        }
        Ok(meta) if meta.len() == 0 => {
            ready = false;
            format!("empty file: {} (size: {})", settings.model_path, meta.len())
        }
        Ok(meta) => format!("ready: {} (size: {} bytes)", settings.model_path, meta.len()),
    };
    details.insert("model_file".into(), json!(model_detail));

    for (key, path) in [
        ("band_info", &settings.band_info_path),
        ("discography", &settings.discography_path),
    ] {
        if std::path::Path::new(path).exists() {
            details.insert(key.into(), json!("exists"));
        } else {
            ready = false;
            details.insert(key.into(), json!(format!("not found: {path}")));
        }
    }

    let fts = std::path::Path::new(&settings.fts_db_path);
    let fts_detail = if !fts.exists() {
        ready = false;
        format!("not found: {}", settings.fts_db_path)
    } else if std::fs::File::open(fts).is_err() {
        ready = false;
        format!("not readable: {}", settings.fts_db_path)
    } else {
        match FactSearchEngine::fact_count(fts) {
            Ok(n) => format!("ready: {} ({n} facts)", settings.fts_db_path),
            Err(e) => {
                ready = false;
                format!("error validating: {} - {e}", settings.fts_db_path)
            }
        }
    };
    details.insert("fts_database".into(), json!(fts_detail));

    if ready {
        Json(json!({"ready": true, "details": details})).into_response()
    } else {
        (
            StatusCode::SERVICE_UNAVAILABLE,
            Json(json!({"ready": false, "details": details})),
        )
            .into_response()
    }
}

// ------------------------------------------------------------------ chat

async fn chat(State(state): State<AppState>, headers: HeaderMap, body: Bytes) -> Response {
    let value = match parse_json_body(&headers, &body) {
        Ok(v) => v,
        Err(r) => return r,
    };
    let Value::Object(object) = &value else {
        return not_an_object(&value);
    };

    // pydantic checks, in order: type, length limits, then the custom whitespace rule
    let message = match object.get("message") {
        None => {
            return validation_error(vec![
                json!({"type": "missing", "loc": ["body", "message"], "msg": "Field required", "input": object}),
            ]);
        }
        Some(Value::String(s)) => match ChatRequest::validate(s) {
            Ok(cleaned) => cleaned,
            Err(MessageProblem::TooShort) => {
                return validation_error(vec![json!({
                    "type": "string_too_short", "loc": ["body", "message"],
                    "msg": "String should have at least 1 character", "input": s, "ctx": {"min_length": 1}
                })]);
            }
            Err(MessageProblem::TooLong) => {
                return validation_error(vec![json!({
                    "type": "string_too_long", "loc": ["body", "message"],
                    "msg": "String should have at most 2000 characters", "input": s, "ctx": {"max_length": 2000}
                })]);
            }
            Err(MessageProblem::Blank) => {
                return validation_error(vec![json!({
                    "type": "value_error", "loc": ["body", "message"],
                    "msg": "Value error, message cannot be empty or whitespace", "input": s, "ctx": {"error": {}}
                })]);
            }
        },
        Some(other) => {
            return validation_error(vec![
                json!({"type": "string_type", "loc": ["body", "message"], "msg": "Input should be a valid string", "input": other}),
            ]);
        }
    };

    // Session: the X-Session-ID header, or a fresh id.
    let session_id = headers
        .get("x-session-id")
        .and_then(|v| v.to_str().ok())
        .filter(|s| !s.is_empty())
        .map(str::to_string)
        .unwrap_or_else(|| uuid::Uuid::new_v4().to_string());

    let inference = state.inference.clone();
    let sid = session_id.clone();
    let result = tokio::task::spawn_blocking(move || inference.run_inference(&message, Some(&sid))).await;
    match result {
        Ok(Ok(response)) => Json(ChatResponse {
            response,
            session_id: Some(session_id),
        })
        .into_response(),
        Ok(Err(e)) => {
            tracing::error!("Processing error: {}", e.message);
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(json!({"detail": {"error": e.message, "remedy": "Please try again later"}})),
            )
                .into_response()
        }
        Err(_) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!({"detail": {"error": "Internal server error", "remedy": "Please try again later"}})),
        )
            .into_response(),
    }
}

// ------------------------------------------------------------------ auth routes

/// FastAPI `HTTPBearer` + `get_current_user`.
fn current_user(state: &AppState, headers: &HeaderMap) -> Result<User, Response> {
    let header_value = headers
        .get(header::AUTHORIZATION)
        .and_then(|v| v.to_str().ok())
        .unwrap_or("");
    let (scheme, _, credentials) = header_value.partition_space();
    if header_value.is_empty() || scheme.is_empty() || credentials.is_empty() || !scheme.eq_ignore_ascii_case("bearer")
    {
        return Err(unauthorized("Not authenticated"));
    }
    match state.auth.user_by_token(credentials) {
        Ok(Some(user)) => Ok(user),
        Ok(None) => Err(unauthorized("Invalid authentication credentials")),
        Err(e) => Err(auth_error(e)),
    }
}

trait PartitionSpace {
    fn partition_space(&self) -> (&str, &str, &str);
}
impl PartitionSpace for str {
    /// Python `str.partition(" ")`.
    fn partition_space(&self) -> (&str, &str, &str) {
        match self.split_once(' ') {
            Some((a, b)) => (a, " ", b),
            None => (self, "", ""),
        }
    }
}

fn admin_user(state: &AppState, headers: &HeaderMap) -> Result<User, Response> {
    let user = current_user(state, headers)?;
    if !user.is_admin {
        return Err(detail(StatusCode::FORBIDDEN, "Admin privileges required"));
    }
    Ok(user)
}

fn user_json(user: &User) -> Value {
    Value::Object(user.to_dict())
}

async fn register(State(state): State<AppState>, headers: HeaderMap, body: Bytes) -> Response {
    let value = match parse_json_body(&headers, &body) {
        Ok(v) => v,
        Err(r) => return r,
    };
    let Value::Object(o) = &value else {
        return not_an_object(&value);
    };
    let mut errors = Vec::new();
    let username = string_field(o, "username", true, &mut errors);
    let email = string_field(o, "email", true, &mut errors);
    let password = string_field(o, "password", true, &mut errors);
    let first = string_field(o, "first_name", false, &mut errors);
    let last = string_field(o, "last_name", false, &mut errors);
    if !errors.is_empty() {
        return validation_error(errors);
    }
    let auth = state.auth.clone();
    let result = tokio::task::spawn_blocking(move || {
        auth.create_user(
            &username.unwrap(),
            &email.unwrap(),
            &password.unwrap(),
            first.as_deref(),
            last.as_deref(),
        )
    })
    .await;
    match result {
        Ok(Ok(user)) => {
            Json(json!({"success": true, "message": "User registered successfully", "user": user_json(&user)}))
                .into_response()
        }
        Ok(Err(e)) => auth_error(e),
        Err(_) => internal_error(),
    }
}

async fn login(State(state): State<AppState>, headers: HeaderMap, body: Bytes) -> Response {
    let value = match parse_json_body(&headers, &body) {
        Ok(v) => v,
        Err(r) => return r,
    };
    let Value::Object(o) = &value else {
        return not_an_object(&value);
    };
    let mut errors = Vec::new();
    let username = string_field(o, "username", true, &mut errors);
    let password = string_field(o, "password", true, &mut errors);
    if !errors.is_empty() {
        return validation_error(errors);
    }
    let auth = state.auth.clone();
    let result = tokio::task::spawn_blocking(move || -> Result<Option<(String, String, User)>, AuthError> {
        let (username, password) = (username.unwrap(), password.unwrap());
        let Some(user) = auth.authenticate_user(&username, &password)? else {
            return Ok(None);
        };
        auth.update_last_login(user.id)?;
        let user = auth.user_by_id(user.id)?.unwrap_or(user);
        let token = auth.create_access_token(&user)?;
        let session = auth.create_user_session(user.id)?;
        Ok(Some((token, session, user)))
    })
    .await;
    match result {
        Ok(Ok(Some((token, session, user)))) => Json(
            json!({"access_token": token, "token_type": "bearer", "session_id": session, "user": user_json(&user)}),
        )
        .into_response(),
        Ok(Ok(None)) => unauthorized("Incorrect username or password"),
        Ok(Err(e)) => auth_error(e),
        Err(_) => internal_error(),
    }
}

async fn logout(
    State(state): State<AppState>,
    headers: HeaderMap,
    Query(query): Query<HashMap<String, String>>,
) -> Response {
    if let Err(r) = current_user(&state, &headers) {
        return r;
    }
    let session_id = headers
        .get("x-session-id")
        .and_then(|v| v.to_str().ok())
        .map(str::to_string)
        .filter(|s| !s.is_empty())
        .or_else(|| query.get("session_id").cloned());
    if let Some(id) = session_id {
        if let Err(e) = state.auth.deactivate_session(&id) {
            return auth_error(e);
        }
    }
    Json(json!({"message": "Successfully logged out"})).into_response()
}

async fn me(State(state): State<AppState>, headers: HeaderMap) -> Response {
    match current_user(&state, &headers) {
        Ok(user) => Json(user_json(&user)).into_response(),
        Err(r) => r,
    }
}

async fn update_me(
    State(state): State<AppState>,
    headers: HeaderMap,
    Query(query): Query<HashMap<String, String>>,
) -> Response {
    let user = match current_user(&state, &headers) {
        Ok(u) => u,
        Err(r) => return r,
    };
    if let Err(e) = state.auth.update_profile(
        user.id,
        query.get("first_name").map(String::as_str),
        query.get("last_name").map(String::as_str),
    ) {
        return auth_error(e);
    }
    match state.auth.user_by_id(user.id) {
        Ok(Some(u)) => Json(user_json(&u)).into_response(),
        Ok(None) => internal_error(),
        Err(e) => auth_error(e),
    }
}

async fn list_users(State(state): State<AppState>, headers: HeaderMap) -> Response {
    if let Err(r) = admin_user(&state, &headers) {
        return r;
    }
    match state.auth.all_users() {
        Ok(users) => Json(users.iter().map(user_json).collect::<Vec<_>>()).into_response(),
        Err(e) => auth_error(e),
    }
}

/// The `{user_id}` path parameter, or FastAPI's 422 for a non-integer.
fn path_user_id(raw: &str) -> Result<i64, Response> {
    raw.trim().parse::<i64>().map_err(|_| {
        validation_error(vec![json!({
            "type": "int_parsing", "loc": ["path", "user_id"],
            "msg": "Input should be a valid integer, unable to parse string as an integer", "input": raw
        })])
    })
}

async fn user_by_id(State(state): State<AppState>, headers: HeaderMap, Path(raw): Path<String>) -> Response {
    if let Err(r) = admin_user(&state, &headers) {
        return r;
    }
    let id = match path_user_id(&raw) {
        Ok(id) => id,
        Err(r) => return r,
    };
    match state.auth.user_by_id(id) {
        Ok(Some(u)) => Json(user_json(&u)).into_response(),
        Ok(None) => detail(StatusCode::NOT_FOUND, "User not found"),
        Err(e) => auth_error(e),
    }
}

async fn set_active(state: AppState, headers: HeaderMap, raw: String, active: bool) -> Response {
    if let Err(r) = admin_user(&state, &headers) {
        return r;
    }
    let id = match path_user_id(&raw) {
        Ok(id) => id,
        Err(r) => return r,
    };
    match state.auth.user_by_id(id) {
        Ok(Some(_)) => {}
        Ok(None) => return detail(StatusCode::NOT_FOUND, "User not found"),
        Err(e) => return auth_error(e),
    }
    if let Err(e) = state.auth.set_user_active(id, active) {
        return auth_error(e);
    }
    let word = if active { "activated" } else { "deactivated" };
    Json(json!({"message": format!("User {word} successfully")})).into_response()
}

async fn activate(State(s): State<AppState>, h: HeaderMap, Path(raw): Path<String>) -> Response {
    set_active(s, h, raw, true).await
}

async fn deactivate(State(s): State<AppState>, h: HeaderMap, Path(raw): Path<String>) -> Response {
    set_active(s, h, raw, false).await
}

async fn cleanup_sessions(State(state): State<AppState>, headers: HeaderMap) -> Response {
    if let Err(r) = admin_user(&state, &headers) {
        return r;
    }
    match state.auth.cleanup_expired_sessions() {
        Ok(n) => Json(json!({"message": format!("Cleaned up {n} expired sessions")})).into_response(),
        Err(e) => auth_error(e),
    }
}

// ------------------------------------------------------------------ router

async fn not_found() -> Response {
    detail(StatusCode::NOT_FOUND, "Not Found")
}

async fn method_not_allowed() -> Response {
    detail(StatusCode::METHOD_NOT_ALLOWED, "Method Not Allowed")
}

pub fn router(state: AppState) -> Router {
    let cors = CorsLayer::new()
        .allow_origin(AllowOrigin::mirror_request())
        .allow_methods(AllowMethods::mirror_request())
        .allow_headers(AllowHeaders::mirror_request())
        .allow_credentials(true);

    Router::new()
        .route("/healthz", get(healthz))
        .route("/readyz", get(readyz))
        .route("/api/chat", post(chat))
        .route("/api/auth/register", post(register))
        .route("/api/auth/login", post(login))
        .route("/api/auth/logout", post(logout))
        .route("/api/auth/me", get(me).put(update_me))
        .route("/api/auth/users", get(list_users))
        .route("/api/auth/users/{user_id}", get(user_by_id))
        .route("/api/auth/users/{user_id}/activate", put(activate))
        .route("/api/auth/users/{user_id}/deactivate", put(deactivate))
        .route("/api/auth/cleanup-sessions", post(cleanup_sessions))
        .fallback(not_found)
        .method_not_allowed_fallback(method_not_allowed)
        .layer(middleware::from_fn(log_requests))
        .layer(CatchPanicLayer::custom(|_| internal_error()))
        .layer(cors)
        .with_state(state)
}
