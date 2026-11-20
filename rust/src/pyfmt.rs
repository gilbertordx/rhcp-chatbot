//! Python-style text formatting for JSON values.
//!
//! A few answers in the original app embed a value with an f-string, e.g.
//! `f"joined {member_since}"` or `f"... {entities[0].value} ..."`. Python turns
//! numbers, booleans, `None` and dicts into text in its own way (`True`, `None`,
//! `{'name': 'Flea'}`), so to produce byte-identical answers this module
//! reproduces `str()` / `repr()` for the JSON types.

use serde_json::Value;

/// Python `repr()` of a string: single quotes unless the text has a `'` and no `"`.
fn repr_str(s: &str) -> String {
    let quote = if s.contains('\'') && !s.contains('"') {
        '"'
    } else {
        '\''
    };
    let mut out = String::new();
    out.push(quote);
    for c in s.chars() {
        match c {
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if c == quote => {
                out.push('\\');
                out.push(c);
            }
            c if (c as u32) < 0x20 || c as u32 == 0x7f => out.push_str(&format!("\\x{:02x}", c as u32)),
            c => out.push(c),
        }
    }
    out.push(quote);
    out
}

fn repr_float(f: f64) -> String {
    if f.is_nan() {
        "nan".into()
    } else if f.is_infinite() {
        if f > 0.0 { "inf".into() } else { "-inf".into() }
    } else if f == f.trunc() && f.abs() < 1e16 {
        format!("{f:.1}")
    } else {
        let s = format!("{f:?}");
        // Rust writes 1e16 where Python writes 1e+16
        match s.split_once('e') {
            Some((m, e)) if !e.starts_with('-') => format!("{m}e+{e}"),
            _ => s,
        }
    }
}

/// Python `repr(value)` for JSON data.
pub fn py_repr(v: &Value) -> String {
    match v {
        Value::Null => "None".into(),
        Value::Bool(true) => "True".into(),
        Value::Bool(false) => "False".into(),
        Value::Number(n) => match n.as_i64() {
            Some(i) => i.to_string(),
            None => match n.as_u64() {
                Some(u) => u.to_string(),
                None => repr_float(n.as_f64().unwrap_or(f64::NAN)),
            },
        },
        Value::String(s) => repr_str(s),
        Value::Array(items) => format!("[{}]", items.iter().map(py_repr).collect::<Vec<_>>().join(", ")),
        Value::Object(map) => {
            format!(
                "{{{}}}",
                map.iter()
                    .map(|(k, v)| format!("{}: {}", repr_str(k), py_repr(v)))
                    .collect::<Vec<_>>()
                    .join(", ")
            )
        }
    }
}

/// Python `str(value)`: like `repr` except a plain string is shown as is.
pub fn py_str(v: &Value) -> String {
    match v {
        Value::String(s) => s.clone(),
        other => py_repr(other),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn scalars() {
        assert_eq!(py_str(&json!(1983)), "1983");
        assert_eq!(py_str(&json!("x")), "x");
        assert_eq!(py_str(&json!(true)), "True");
        assert_eq!(py_str(&json!(null)), "None");
        assert_eq!(py_str(&json!(2.0)), "2.0");
        assert_eq!(py_str(&json!(2.5)), "2.5");
    }

    #[test]
    fn dict_and_list_repr() {
        let v = json!({"name": "Michael 'Flea' Balzary", "periods": ["1988-1992"], "n": 3, "ok": false});
        assert_eq!(
            py_repr(&v),
            r#"{'name': "Michael 'Flea' Balzary", 'periods': ['1988-1992'], 'n': 3, 'ok': False}"#
        );
    }
}
