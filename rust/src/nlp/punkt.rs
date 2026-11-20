//! Sentence splitting. Python equivalent: `nltk.tokenize.sent_tokenize`
//! (the Punkt algorithm), which `word_tokenize` calls before tokenizing words.
//!
//! Why this exists: the original app lower-cases a message and then calls
//! `word_tokenize`, and Punkt splits `"going. use your brain"` into two
//! sentences even in lower case, which changes the tokens (`going` + `.` instead
//! of `going.`). To produce the same tokens the saved model was trained on, the
//! algorithm has to be reproduced. It is driven by four small data files that
//! ship with NLTK's `punkt_tab` English model (abbreviations, collocations,
//! sentence starters, and per-word capitalisation statistics).
//!
//! This is a port of the parts of `nltk/tokenize/punkt.py` that tokenizing uses
//! (not the trainer). Offsets are byte offsets into the text, which is safe
//! because every slice below starts and ends on a character boundary.

use std::collections::{HashMap, HashSet};
use std::fs;
use std::path::{Path, PathBuf};

use anyhow::{Context, Result, bail};
use fancy_regex::Regex;

const ORTHO_BEG_UC: u32 = 1 << 1;
const ORTHO_MID_UC: u32 = 1 << 2;
const ORTHO_UNK_UC: u32 = 1 << 3;
const ORTHO_BEG_LC: u32 = 1 << 4;
const ORTHO_MID_LC: u32 = 1 << 5;
const ORTHO_UNK_LC: u32 = 1 << 6;
const ORTHO_UC: u32 = ORTHO_BEG_UC + ORTHO_MID_UC + ORTHO_UNK_UC;
const ORTHO_LC: u32 = ORTHO_BEG_LC + ORTHO_MID_LC + ORTHO_UNK_LC;

/// What Punkt learned about English (loaded from NLTK's data files).
#[derive(Default)]
pub struct PunktParams {
    abbrev_types: HashSet<String>,
    collocations: HashSet<(String, String)>,
    sent_starters: HashSet<String>,
    ortho_context: HashMap<String, u32>,
}

/// Where NLTK keeps its data, in the order NLTK looks: `NLTK_DATA` (a list separated by `:` on
/// Linux/macOS and `;` on Windows), then `~/nltk_data`, then the system folders.
/// On Windows there is usually no `HOME`, so `USERPROFILE` and `APPDATA` are tried too.
pub fn nltk_data_dirs() -> Vec<PathBuf> {
    let mut dirs: Vec<PathBuf> = Vec::new();
    if let Some(paths) = std::env::var_os("NLTK_DATA") {
        dirs.extend(std::env::split_paths(&paths).filter(|p| !p.as_os_str().is_empty()));
    }
    for var in ["HOME", "USERPROFILE", "APPDATA"] {
        if let Some(base) = std::env::var_os(var).filter(|v| !v.is_empty()) {
            let dir = Path::new(&base).join("nltk_data");
            if !dirs.contains(&dir) {
                dirs.push(dir);
            }
        }
    }
    dirs.push(PathBuf::from("/usr/share/nltk_data"));
    dirs.push(PathBuf::from("/usr/local/share/nltk_data"));
    dirs.push(PathBuf::from(r"C:\nltk_data"));
    dirs
}

/// Find `tokenizers/punkt_tab/english/` in any NLTK data folder.
pub fn find_punkt_dir() -> Option<PathBuf> {
    nltk_data_dirs()
        .into_iter()
        .map(|d| d.join("tokenizers").join("punkt_tab").join("english"))
        .find(|d| d.join("abbrev_types.txt").exists())
}

impl PunktParams {
    pub fn load(dir: &Path) -> Result<Self> {
        let read = |name: &str| -> Result<String> {
            fs::read_to_string(dir.join(name)).with_context(|| format!("reading {}", dir.join(name).display()))
        };
        // NLTK strips exactly one trailing newline from each line; `lines()` does that.
        let mut params = PunktParams::default();
        for line in read("collocations.tab")?.lines() {
            let mut parts = line.split('\t');
            if let (Some(a), Some(b)) = (parts.next(), parts.next()) {
                params.collocations.insert((a.to_string(), b.to_string()));
            }
        }
        params.sent_starters = read("sent_starters.txt")?.lines().map(str::to_string).collect();
        params.abbrev_types = read("abbrev_types.txt")?.lines().map(str::to_string).collect();
        for line in read("ortho_context.tab")?.lines() {
            let mut parts = line.split('\t');
            if let (Some(word), Some(flags)) = (parts.next(), parts.next()) {
                let flags: u32 = flags
                    .parse()
                    .with_context(|| format!("bad ortho flag in line {line:?}"))?;
                params.ortho_context.insert(word.to_string(), flags);
            }
        }
        if params.abbrev_types.is_empty() {
            bail!("punkt data in {} looks empty", dir.display());
        }
        Ok(params)
    }

    fn ortho(&self, typ: &str) -> u32 {
        self.ortho_context.get(typ).copied().unwrap_or(0)
    }
}

/// One word of text plus the decisions Punkt has made about it.
#[derive(Debug, Clone)]
struct Token {
    tok: String,
    typ: String,
    period_final: bool,
    sentbreak: bool,
    abbr: bool,
    ellipsis: bool,
}

fn is_letter_like(c: char) -> bool {
    // Python `[^\W\d]`: a word character that is not a digit.
    c.is_alphabetic() || c == '_'
}

impl Token {
    fn new(tok: &str, numeric: &Regex) -> Self {
        let lowered = tok.to_lowercase();
        let typ = if numeric.is_match(&lowered).unwrap_or(false) {
            "##number##".to_string()
        } else {
            lowered
        };
        Token {
            period_final: tok.ends_with('.'),
            tok: tok.to_string(),
            typ,
            sentbreak: false,
            abbr: false,
            ellipsis: false,
        }
    }

    fn type_no_period(&self) -> &str {
        if self.typ.chars().count() > 1 && self.typ.ends_with('.') {
            &self.typ[..self.typ.len() - 1]
        } else {
            &self.typ
        }
    }

    fn type_no_sentperiod(&self) -> &str {
        if self.sentbreak {
            self.type_no_period()
        } else {
            &self.typ
        }
    }

    fn first_upper(&self) -> bool {
        self.tok.chars().next().is_some_and(char::is_uppercase)
    }

    fn first_lower(&self) -> bool {
        self.tok.chars().next().is_some_and(char::is_lowercase)
    }

    fn is_ellipsis(&self) -> bool {
        self.tok.chars().count() >= 2 && self.tok.chars().all(|c| c == '.')
    }

    fn is_initial(&self) -> bool {
        let mut it = self.tok.chars();
        matches!((it.next(), it.next(), it.next()), (Some(a), Some('.'), None) if is_letter_like(a))
    }
}

pub struct SentenceTokenizer {
    params: PunktParams,
    word_re: Regex,
    numeric_re: Regex,
    period_chars: [char; 3],
    realign_re: Regex,
}

/// Characters that can start a sentence-final context (JS: `NonWord`).
const NON_WORD: &str = r#"(?:[)\";}\]\*:@\'\({\[‘’“”\xab\xbb?!])"#;

fn is_non_word(c: char) -> bool {
    matches!(
        c,
        ')' | '"'
            | ';'
            | '}'
            | ']'
            | '*'
            | ':'
            | '@'
            | '\''
            | '('
            | '{'
            | '['
            | '\u{2018}'
            | '\u{2019}'
            | '\u{201c}'
            | '\u{201d}'
            | '\u{ab}'
            | '\u{bb}'
            | '?'
            | '!'
    )
}

impl SentenceTokenizer {
    pub fn new(params: PunktParams) -> Result<Self> {
        let multi = r"(?:\-{2,}|\.{2,}|(?:\.\s){2,}\.)";
        let word_start = r#"[^\(\"\`{\[:;&\#\*@\)}\]\-,]"#;
        let pattern =
            format!(r"({multi}|(?={word_start})\S+?(?=\s|\z|{NON_WORD}|{multi}|,(?=\z|\s|{NON_WORD}|{multi}))|\S)");
        Ok(Self {
            params,
            word_re: Regex::new(&pattern)?,
            numeric_re: Regex::new(r"^-?[\.,]?\d[\d,\.-]*\.?$")?,
            period_chars: ['.', '?', '!'],
            realign_re: Regex::new(r#"\A["')\]}‘’“”\xab\xbb]+?(?:\s+|(?=--)|\z|(?=\n))"#)?,
        })
    }

    /// Load the English model from the NLTK data folders.
    pub fn from_nltk_data() -> Result<Self> {
        let dir = find_punkt_dir().context(
            "NLTK punkt data not found (looked for tokenizers/punkt_tab/english/ in NLTK_DATA, ~/nltk_data, /usr/share/nltk_data). \
             Run `rhcp-chatbot setup-nltk` to download it.",
        )?;
        Self::new(PunktParams::load(&dir)?)
    }

    /// Split a line into Punkt's word tokens (JS: `PunktLanguageVars.word_tokenize`).
    fn word_tokens<'a>(&self, line: &'a str) -> Vec<&'a str> {
        self.word_re
            .find_iter(line)
            .filter_map(|m| m.ok())
            .map(|m| m.as_str())
            .collect()
    }

    /// `_tokenize_words`: one pass per non-blank line.
    fn tokenize_words(&self, text: &str) -> Vec<Token> {
        let mut out = Vec::new();
        for line in text.split('\n') {
            if line.trim().is_empty() {
                continue;
            }
            for tok in self.word_tokens(line) {
                out.push(Token::new(tok, &self.numeric_re));
            }
        }
        out
    }

    /// Orthographic heuristic: `Some(true)` = starts a sentence, `Some(false)` = does not,
    /// `None` = unknown. (Python returns `True` / `False` / `"unknown"`.)
    fn ortho_heuristic(&self, next: &Token) -> Option<bool> {
        if matches!(next.tok.as_str(), ";" | ":" | "," | "." | "!" | "?") {
            return Some(false);
        }
        let ctx = self.params.ortho(next.type_no_sentperiod());
        if next.first_upper() && (ctx & ORTHO_LC) != 0 && (ctx & ORTHO_MID_UC) == 0 {
            return Some(true);
        }
        if next.first_lower() && ((ctx & ORTHO_UC) != 0 || (ctx & ORTHO_BEG_LC) == 0) {
            return Some(false);
        }
        None
    }

    fn first_pass(&self, tok: &mut Token) {
        if tok.tok.chars().count() == 1 && self.period_chars.contains(&tok.tok.chars().next().unwrap()) {
            tok.sentbreak = true;
        } else if tok.is_ellipsis() {
            tok.ellipsis = true;
        } else if tok.period_final && !tok.tok.ends_with("..") {
            let without_period = &tok.tok[..tok.tok.len() - 1];
            let lowered = without_period.to_lowercase();
            let last_hyphen_part = lowered.rsplit('-').next().unwrap_or("");
            if self.params.abbrev_types.contains(&lowered) || self.params.abbrev_types.contains(last_hyphen_part) {
                tok.abbr = true;
            } else {
                tok.sentbreak = true;
            }
        }
    }

    fn second_pass(&self, a: &mut Token, b: Option<&Token>) {
        let Some(b) = b else { return };
        if !a.period_final {
            return;
        }
        let typ = a.type_no_period().to_string();
        let next_typ = b.type_no_sentperiod().to_string();
        let a_is_initial = a.is_initial();

        if self.params.collocations.contains(&(typ.clone(), next_typ.clone())) {
            a.sentbreak = false;
            a.abbr = true;
            return;
        }

        if (a.abbr || a.ellipsis) && !a_is_initial {
            if self.ortho_heuristic(b) == Some(true) {
                a.sentbreak = true;
                return;
            }
            if b.first_upper() && self.params.sent_starters.contains(&next_typ) {
                a.sentbreak = true;
                return;
            }
        }

        if a_is_initial || typ == "##number##" {
            let heuristic = self.ortho_heuristic(b);
            if heuristic == Some(false) {
                a.sentbreak = false;
                a.abbr = true;
                return;
            }
            if heuristic.is_none() && a_is_initial && b.first_upper() && (self.params.ortho(&next_typ) & ORTHO_LC) == 0
            {
                a.sentbreak = false;
                a.abbr = true;
            }
        }
    }

    /// Annotate every token (both passes).
    fn annotate(&self, text: &str) -> Vec<Token> {
        let mut tokens = self.tokenize_words(text);
        for tok in tokens.iter_mut() {
            self.first_pass(tok);
        }
        for i in 0..tokens.len() {
            let (head, tail) = tokens.split_at_mut(i + 1);
            self.second_pass(&mut head[i], tail.first());
        }
        tokens
    }

    /// True if the text contains a sentence break that is not on its last token.
    fn text_contains_sentbreak(&self, text: &str) -> bool {
        let tokens = self.annotate(text);
        tokens.iter().take(tokens.len().saturating_sub(1)).any(|t| t.sentbreak)
    }

    /// Candidate sentence ends: each `.`/`?`/`!` followed by a non-word mark or by
    /// whitespace and another token (JS: `period_context_re().finditer`).
    /// Returns `(start, end, next_token_start, after_token_text)` per match.
    fn period_contexts(&self, text: &str) -> Vec<(usize, usize, Option<usize>, String)> {
        let mut out = Vec::new();
        for (i, c) in text.char_indices() {
            if !self.period_chars.contains(&c) {
                continue;
            }
            let end = i + c.len_utf8();
            let rest = &text[end..];
            let mut chars = rest.chars();
            match chars.next() {
                Some(n) if is_non_word(n) => out.push((i, end, None, n.to_string())),
                Some(n) if n.is_whitespace() => {
                    let after_ws = rest.trim_start_matches(char::is_whitespace);
                    let token_len = after_ws.find(char::is_whitespace).unwrap_or(after_ws.len());
                    if token_len > 0 {
                        let ws_len = rest.len() - after_ws.len();
                        let next_start = end + ws_len;
                        out.push((i, end, Some(next_start), rest[..ws_len + token_len].to_string()));
                    }
                }
                _ => {}
            }
        }
        out
    }

    fn last_ascii_whitespace_index(text: &str) -> usize {
        text.rfind([' ', '\t', '\n', '\r', '\x0b', '\x0c']).unwrap_or(0)
    }

    fn slices(&self, text: &str) -> Vec<(usize, usize)> {
        // 1. candidate contexts, with the "previous word" logic of NLTK
        let mut contexts: Vec<(usize, usize, Option<usize>, String)> = Vec::new(); // (match_start, match_end, next_tok, context)
        let (mut prev_start, mut prev_stop) = (0usize, 0usize);
        let mut previous: Option<(usize, usize, Option<usize>, String)> = None; // match + after_tok
        for (m_start, m_end, next_tok, after) in self.period_contexts(text) {
            let before = &text[prev_stop..m_start];
            let mut idx = Self::last_ascii_whitespace_index(before);
            idx = if idx != 0 { idx + prev_stop + 1 } else { prev_start };
            let (word_start, word_stop) = (idx, m_start);
            if let Some((pm_start, pm_end, pm_next, pm_after)) = previous.take() {
                if prev_stop <= word_start {
                    let context = format!(
                        "{}{}{}",
                        &text[prev_start..prev_stop],
                        &text[pm_start..pm_end],
                        pm_after
                    );
                    contexts.push((pm_start, pm_end, pm_next, context));
                } else {
                    // overlapping: the earlier match is dropped
                }
            }
            previous = Some((m_start, m_end, next_tok, after));
            prev_start = word_start;
            prev_stop = word_stop;
        }
        if let Some((pm_start, pm_end, pm_next, pm_after)) = previous {
            let context = format!(
                "{}{}{}",
                &text[prev_start..prev_stop],
                &text[pm_start..pm_end],
                pm_after
            );
            contexts.push((pm_start, pm_end, pm_next, context));
        }

        // 2. keep the candidates whose context really contains a break
        let mut slices = Vec::new();
        let mut last_break = 0usize;
        for (_start, end, next_tok, context) in contexts {
            if self.text_contains_sentbreak(&context) {
                slices.push((last_break, end));
                last_break = next_tok.unwrap_or(end);
            }
        }
        slices.push((last_break, text.trim_end().len()));
        slices
    }

    /// Attach closing quotes/brackets that follow a sentence end to that sentence.
    fn realign(&self, text: &str, slices: Vec<(usize, usize)>) -> Vec<(usize, usize)> {
        let mut out = Vec::new();
        let mut realign = 0usize;
        for i in 0..slices.len() {
            let (s1_start, s1_stop) = slices[i];
            let s1 = (s1_start + realign, s1_stop);
            match slices.get(i + 1) {
                None => {
                    if s1.0 < s1.1 && s1.1 <= text.len() {
                        out.push(s1);
                    }
                }
                Some(&(s2_start, s2_stop)) => {
                    let s2_text = &text[s2_start..s2_stop.max(s2_start)];
                    match self.realign_re.find(s2_text).ok().flatten() {
                        Some(m) => {
                            out.push((s1.0, s2_start + m.as_str().trim_end().len()));
                            realign = m.end();
                        }
                        None => {
                            realign = 0;
                            if s1.0 < s1.1 {
                                out.push(s1);
                            }
                        }
                    }
                }
            }
        }
        out
    }

    /// `sent_tokenize(text)`.
    pub fn sentences<'a>(&self, text: &'a str) -> Vec<&'a str> {
        let slices = self.slices(text);
        self.realign(text, slices)
            .into_iter()
            .map(|(s, e)| &text[s..e])
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Needs NLTK's punkt data; skipped (with a note) where it is not installed.
    fn tokenizer() -> Option<SentenceTokenizer> {
        match SentenceTokenizer::from_nltk_data() {
            Ok(t) => Some(t),
            Err(_) => {
                eprintln!("SKIPPED: NLTK punkt data not installed (run `rhcp-chatbot setup-nltk`)");
                None
            }
        }
    }

    #[test]
    fn splits_on_a_period_even_in_lower_case() {
        let Some(t) = tokenizer() else { return };
        assert_eq!(t.sentences("going. use your brain"), ["going.", "use your brain"]);
    }

    #[test]
    fn abbreviations_do_not_end_a_sentence() {
        let Some(t) = tokenizer() else { return };
        assert_eq!(
            t.sentences("Mr. Smith went to Washington. He was a senator."),
            ["Mr. Smith went to Washington.", "He was a senator."]
        );
    }

    #[test]
    fn question_and_exclamation_marks_end_sentences() {
        let Some(t) = tokenizer() else { return };
        assert_eq!(
            t.sentences("who is flea? tell me! ok"),
            ["who is flea?", "tell me!", "ok"]
        );
    }

    #[test]
    fn empty_and_blank_text_have_no_sentences() {
        let Some(t) = tokenizer() else { return };
        assert!(t.sentences("").is_empty());
        assert!(t.sentences("   ").is_empty());
    }
}
