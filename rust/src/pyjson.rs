//! JSON text formatted the way Python's `json.dumps(value, indent=2)` writes it:
//! two-space indent and `ensure_ascii=True`, which writes every non-ASCII
//! character as a `\uXXXX` escape (characters above U+FFFF as surrogate pairs).
//! Used for the CLI's `--json` output so it is byte-identical to the original.

use serde::Serialize;
use serde_json::Value;
use serde_json::ser::{Formatter, PrettyFormatter, Serializer};

struct AsciiPretty(PrettyFormatter<'static>);

impl Formatter for AsciiPretty {
    // Everything except string fragments is delegated to the standard pretty printer.
    fn begin_array<W: ?Sized + std::io::Write>(&mut self, w: &mut W) -> std::io::Result<()> {
        self.0.begin_array(w)
    }
    fn end_array<W: ?Sized + std::io::Write>(&mut self, w: &mut W) -> std::io::Result<()> {
        self.0.end_array(w)
    }
    fn begin_array_value<W: ?Sized + std::io::Write>(&mut self, w: &mut W, first: bool) -> std::io::Result<()> {
        self.0.begin_array_value(w, first)
    }
    fn end_array_value<W: ?Sized + std::io::Write>(&mut self, w: &mut W) -> std::io::Result<()> {
        self.0.end_array_value(w)
    }
    fn begin_object<W: ?Sized + std::io::Write>(&mut self, w: &mut W) -> std::io::Result<()> {
        self.0.begin_object(w)
    }
    fn end_object<W: ?Sized + std::io::Write>(&mut self, w: &mut W) -> std::io::Result<()> {
        self.0.end_object(w)
    }
    fn begin_object_key<W: ?Sized + std::io::Write>(&mut self, w: &mut W, first: bool) -> std::io::Result<()> {
        self.0.begin_object_key(w, first)
    }
    fn begin_object_value<W: ?Sized + std::io::Write>(&mut self, w: &mut W) -> std::io::Result<()> {
        self.0.begin_object_value(w)
    }
    fn end_object_value<W: ?Sized + std::io::Write>(&mut self, w: &mut W) -> std::io::Result<()> {
        self.0.end_object_value(w)
    }

    fn write_string_fragment<W: ?Sized + std::io::Write>(&mut self, w: &mut W, fragment: &str) -> std::io::Result<()> {
        let mut buf = [0u16; 2];
        for c in fragment.chars() {
            if c.is_ascii() {
                w.write_all(&[c as u8])?;
            } else {
                for unit in c.encode_utf16(&mut buf) {
                    write!(w, "\\u{:04x}", unit)?;
                }
            }
        }
        Ok(())
    }
}

pub fn dumps_pretty(value: &Value) -> String {
    let mut out = Vec::new();
    let mut ser = Serializer::with_formatter(&mut out, AsciiPretty(PrettyFormatter::with_indent(b"  ")));
    value
        .serialize(&mut ser)
        .expect("serializing JSON to memory cannot fail");
    String::from_utf8(out).expect("JSON output is valid UTF-8")
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn escapes_non_ascii_like_python() {
        let v = json!({"a": "caf\u{e9} \u{1F3B8}", "b": [1, 2.5, null, true]});
        assert_eq!(
            dumps_pretty(&v),
            "{\n  \"a\": \"caf\\u00e9 \\ud83c\\udfb8\",\n  \"b\": [\n    1,\n    2.5,\n    null,\n    true\n  ]\n}"
        );
    }
}

// ---------------------------------------------------------------------------
// Python-compatible JSON *error* reporting
// ---------------------------------------------------------------------------
//
// When a request body is not valid JSON, FastAPI reported the message and the
// character offset from Python's `json.JSONDecodeError` (for example
// `"Expecting ',' delimiter"` at offset 15). serde_json words and locates its
// errors differently, so this small scanner follows CPython's decoder to produce
// the same text and offset. It only *finds the first error*; actual parsing
// still uses serde_json.

/// `(offset in characters, message)` of the first error CPython's decoder would report.
pub fn python_json_error(text: &str) -> Option<(usize, String)> {
    let s: Vec<char> = text.chars().collect();
    let mut p = Scanner { s: &s };
    let start = p.skip_ws(0);
    match p.value(start) {
        Err(Fail::Stop(pos)) => Some((pos, "Expecting value".to_string())),
        Err(Fail::Error(pos, msg)) => Some((pos, msg)),
        Ok(end) => {
            let end = p.skip_ws(end);
            (end != s.len()).then(|| (end, "Extra data".to_string()))
        }
    }
}

enum Fail {
    /// CPython's `StopIteration(idx)`: no value starts here.
    Stop(usize),
    Error(usize, String),
}

struct Scanner<'a> {
    s: &'a [char],
}

fn err<T>(pos: usize, msg: &str) -> Result<T, Fail> {
    Err(Fail::Error(pos, msg.to_string()))
}

impl Scanner<'_> {
    fn at(&self, i: usize) -> Option<char> {
        self.s.get(i).copied()
    }

    fn skip_ws(&self, mut i: usize) -> usize {
        while matches!(self.at(i), Some(' ' | '\t' | '\n' | '\r')) {
            i += 1;
        }
        i
    }

    fn starts_with(&self, i: usize, word: &str) -> bool {
        word.chars().enumerate().all(|(k, c)| self.at(i + k) == Some(c))
    }

    /// Returns the index just after the value that starts at `idx`.
    fn value(&mut self, idx: usize) -> Result<usize, Fail> {
        let Some(c) = self.at(idx) else {
            return Err(Fail::Stop(idx));
        };
        match c {
            '"' => self.string(idx + 1),
            '{' => self.object(idx + 1),
            '[' => self.array(idx + 1),
            'n' if self.starts_with(idx, "null") => Ok(idx + 4),
            't' if self.starts_with(idx, "true") => Ok(idx + 4),
            'f' if self.starts_with(idx, "false") => Ok(idx + 5),
            'N' if self.starts_with(idx, "NaN") => Ok(idx + 3),
            'I' if self.starts_with(idx, "Infinity") => Ok(idx + 8),
            '-' if self.starts_with(idx, "-Infinity") => Ok(idx + 9),
            _ => self.number(idx).ok_or(Fail::Stop(idx)),
        }
    }

    /// `(-?(?:0|[1-9]\d*))(\.\d+)?([eE][-+]?\d+)?`
    fn number(&self, idx: usize) -> Option<usize> {
        let mut i = idx;
        if self.at(i) == Some('-') {
            i += 1;
        }
        match self.at(i) {
            Some('0') => i += 1,
            Some('1'..='9') => {
                while matches!(self.at(i), Some('0'..='9')) {
                    i += 1;
                }
            }
            _ => return None,
        }
        if self.at(i) == Some('.') && matches!(self.at(i + 1), Some('0'..='9')) {
            i += 1;
            while matches!(self.at(i), Some('0'..='9')) {
                i += 1;
            }
        }
        if matches!(self.at(i), Some('e' | 'E')) {
            let mut j = i + 1;
            if matches!(self.at(j), Some('+' | '-')) {
                j += 1;
            }
            if matches!(self.at(j), Some('0'..='9')) {
                while matches!(self.at(j), Some('0'..='9')) {
                    j += 1;
                }
                i = j;
            }
        }
        Some(i)
    }

    /// `end` is the index just after the opening quote.
    fn string(&mut self, mut end: usize) -> Result<usize, Fail> {
        let begin = end - 1;
        loop {
            // find the next quote, backslash or control character
            let mut i = end;
            loop {
                match self.at(i) {
                    None => return err(begin, "Unterminated string starting at"),
                    Some('"') | Some('\\') => break,
                    Some(c) if (c as u32) < 0x20 => break,
                    _ => i += 1,
                }
            }
            let terminator = self.s[i];
            end = i + 1;
            if terminator == '"' {
                return Ok(end);
            }
            if terminator != '\\' {
                return err(i, "Invalid control character at");
            }
            let Some(esc) = self.at(end) else {
                return err(begin, "Unterminated string starting at");
            };
            if esc != 'u' {
                if !matches!(esc, '"' | '\\' | '/' | 'b' | 'f' | 'n' | 'r' | 't') {
                    return err(end - 1, "Invalid \\escape");
                }
                end += 1;
            } else {
                let hex_ok = |at: usize| (0..4).all(|k| self.at(at + k).is_some_and(|c| c.is_ascii_hexdigit()));
                if !hex_ok(end + 1) {
                    return err(end, "Invalid \\uXXXX escape");
                }
                let unit = u32::from_str_radix(&self.s[end + 1..end + 5].iter().collect::<String>(), 16).unwrap_or(0);
                end += 5;
                // a high surrogate may be followed by `\uXXXX` (a low surrogate); either way parsing goes on
                if (0xd800..=0xdbff).contains(&unit) && self.at(end) == Some('\\') && self.at(end + 1) == Some('u') {
                    if !hex_ok(end + 2) {
                        return err(end + 1, "Invalid \\uXXXX escape");
                    }
                    end += 6;
                }
            }
        }
    }

    fn object(&mut self, mut end: usize) -> Result<usize, Fail> {
        let mut next = self.at(end);
        if next != Some('"') {
            end = self.skip_ws(end);
            next = self.at(end);
            if next == Some('}') {
                return Ok(end + 1);
            } else if next != Some('"') {
                return err(end, "Expecting property name enclosed in double quotes");
            }
        }
        end += 1;
        loop {
            end = self.string(end)?;
            if self.at(end) != Some(':') {
                end = self.skip_ws(end);
                if self.at(end) != Some(':') {
                    return err(end, "Expecting ':' delimiter");
                }
            }
            end += 1;
            end = self.skip_ws(end);
            end = match self.value(end) {
                Ok(e) => e,
                Err(Fail::Stop(pos)) => return err(pos, "Expecting value"),
                Err(other) => return Err(other),
            };
            end = self.skip_ws(end);
            let next = self.at(end);
            end += 1;
            match next {
                Some('}') => return Ok(end),
                Some(',') => {}
                _ => return err(end - 1, "Expecting ',' delimiter"),
            }
            let comma = end - 1;
            end = self.skip_ws(end);
            let next = self.at(end);
            end += 1;
            if next != Some('"') {
                return if next == Some('}') {
                    err(comma, "Illegal trailing comma before end of object")
                } else {
                    err(end - 1, "Expecting property name enclosed in double quotes")
                };
            }
        }
    }

    fn array(&mut self, mut end: usize) -> Result<usize, Fail> {
        end = self.skip_ws(end);
        if self.at(end) == Some(']') {
            return Ok(end + 1);
        }
        loop {
            end = match self.value(end) {
                Ok(e) => e,
                Err(Fail::Stop(pos)) => return err(pos, "Expecting value"),
                Err(other) => return Err(other),
            };
            end = self.skip_ws(end);
            let next = self.at(end);
            end += 1;
            match next {
                Some(']') => return Ok(end),
                Some(',') => {}
                _ => return err(end - 1, "Expecting ',' delimiter"),
            }
            let comma = end - 1;
            end = self.skip_ws(end);
            if self.at(end) == Some(']') {
                return err(comma, "Illegal trailing comma before end of array");
            }
        }
    }
}

#[cfg(test)]
mod error_tests {
    use super::*;

    #[test]
    fn matches_cpython_messages_and_offsets() {
        assert_eq!(
            python_json_error("{nope"),
            Some((1, "Expecting property name enclosed in double quotes".into()))
        );
        assert_eq!(
            python_json_error(r#"{"message": "x",}"#),
            Some((15, "Illegal trailing comma before end of object".into()))
        );
        assert_eq!(
            python_json_error(r#"{"message": "x""#),
            Some((15, "Expecting ',' delimiter".into()))
        );
        assert_eq!(
            python_json_error("not json at all"),
            Some((0, "Expecting value".into()))
        );
        assert_eq!(python_json_error(r#"{"a": 1} x"#), Some((9, "Extra data".into())));
        assert_eq!(
            python_json_error(r#"{"a": "oops"#),
            Some((6, "Unterminated string starting at".into()))
        );
        assert_eq!(python_json_error(r#"{"a": 1}"#), None);
    }
}
