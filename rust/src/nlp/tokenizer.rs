//! Word tokenizer. Python equivalent: `nltk.tokenize.word_tokenize` and the
//! `tokenize(text)` helper in `app/chatbot/initializer.py`:
//!
//! ```python
//! def tokenize(text):
//!     tokens = word_tokenize(text.lower())
//!     return [PorterStemmer().stem(t) for t in tokens]
//! ```
//!
//! NLTK's `NLTKWordTokenizer` is a fixed pipeline of regex substitutions (put
//! spaces around punctuation, split contractions like `don't` -> `do`, `n't`,
//! then split on whitespace). Here each Python regex becomes a
//! `(pattern, replacement)` pair applied in the same order. Two translation
//! notes:
//! * Python `\1` becomes `${1}`, and `\g<0>` becomes `${0}`.
//! * Python's `$` also matches just before a trailing newline; where that
//!   mattered the pattern uses `(?=\n?\z)`.

use anyhow::Result;
use fancy_regex::Regex;

use super::porter::Porter;
use super::punkt::SentenceTokenizer;

struct Rule {
    re: Regex,
    replacement: &'static str,
}

fn rule(pattern: &str, replacement: &'static str) -> Result<Rule> {
    Ok(Rule {
        re: Regex::new(pattern)?,
        replacement,
    })
}

/// Apply one substitution to every match, like Python `re.sub`.
fn apply(rule: &Rule, text: &str) -> String {
    rule.re.replace_all(text, rule.replacement).into_owned()
}

pub struct WordTokenizer {
    starting_quotes: Vec<Rule>,
    punctuation: Vec<Rule>,
    parens: Rule,
    double_dashes: Rule,
    ending_quotes: Vec<Rule>,
    contractions: Vec<Rule>,
}

impl WordTokenizer {
    pub fn new() -> Result<Self> {
        Ok(Self {
            starting_quotes: vec![
                rule("([«“‘„]|[`]+)", " ${1} ")?,
                rule(r#"^""#, "``")?,
                rule("(``)", " ${1} ")?,
                rule(r#"([ \(\[{<])("|'{2})"#, "${1} `` ")?,
                rule(r"(?i)(?<!\w)(')(?!(?:re|ve|ll|m|t|s|d|n)\b)(?=\w)", "${1} ")?,
            ],
            punctuation: vec![
                rule(r#"([^\.])(\.)([\]\)}>"'»”’ ]*+)\s*$"#, "${1} ${2} ${3} ")?,
                rule(r"([:,])([^\d])", " ${1} ${2}")?,
                rule(r"([:,])(?=\n?\z)", " ${1} ")?,
                rule(r"\.{2,}", " ${0} ")?,
                rule(r"[;@#$%&]", " ${0} ")?,
                rule(r"[\u{2012}-\u{2015}]", " ${0} ")?,
                // the final period
                rule(r#"([^\.])(\.)([\]\)}>"']*)\s*$"#, "${1} ${2}${3} ")?,
                rule(r"[?!]", " ${0} ")?,
                rule(r"([^'])' ", "${1} ' ")?,
                rule(r"[*]", " ${0} ")?,
            ],
            parens: rule(r"[\]\[\(\)\{\}\<\>]", " ${0} ")?,
            double_dashes: rule("--", " -- ")?,
            ending_quotes: vec![
                rule("([»”’])", " ${1} ")?,
                rule("''", " '' ")?,
                rule("\"", " '' ")?,
                rule(r"\s+", " ")?,
                rule(r"([^' ])('[sS]|'[mM]|'[dD]|') ", "${1} ${2} ")?,
                rule(r"([^' ])('ll|'LL|'re|'RE|'ve|'VE|n't|N'T) ", "${1} ${2} ")?,
            ],
            // NLTK's MacIntyre contractions (the `(?#X)` comments are dropped).
            contractions: vec![
                rule(r"(?i)\b(can)(not)\b", " ${1} ${2} ")?,
                rule(r"(?i)\b(d)('ye)\b", " ${1} ${2} ")?,
                rule(r"(?i)\b(gim)(me)\b", " ${1} ${2} ")?,
                rule(r"(?i)\b(gon)(na)\b", " ${1} ${2} ")?,
                rule(r"(?i)\b(got)(ta)\b", " ${1} ${2} ")?,
                rule(r"(?i)\b(lem)(me)\b", " ${1} ${2} ")?,
                rule(r"(?i)\b(more)('n)\b", " ${1} ${2} ")?,
                rule(r"(?i)\b(wan)(na)(?=\s)", " ${1} ${2} ")?,
                rule(r"(?i) ('t)(is)\b", " ${1} ${2} ")?,
                rule(r"(?i) ('t)(was)\b", " ${1} ${2} ")?,
            ],
        })
    }

    /// Tokenize ONE sentence (NLTK `NLTKWordTokenizer.tokenize`).
    pub fn tokenize_sentence(&self, sentence: &str) -> Vec<String> {
        let mut text = sentence.to_string();
        for r in &self.starting_quotes {
            text = apply(r, &text);
        }
        for r in &self.punctuation {
            text = apply(r, &text);
        }
        text = apply(&self.parens, &text);
        text = apply(&self.double_dashes, &text);
        text = format!(" {text} ");
        for r in &self.ending_quotes {
            text = apply(r, &text);
        }
        for r in &self.contractions {
            text = apply(r, &text);
        }
        text.split_whitespace().map(str::to_string).collect()
    }
}

/// Everything needed to turn a message into the words the model knows.
pub struct TextAnalyzer {
    sentences: SentenceTokenizer,
    words: WordTokenizer,
    stemmer: Porter,
}

impl TextAnalyzer {
    pub fn new(sentences: SentenceTokenizer) -> Result<Self> {
        Ok(Self {
            sentences,
            words: WordTokenizer::new()?,
            stemmer: Porter::new(),
        })
    }

    pub fn from_nltk_data() -> Result<Self> {
        Self::new(SentenceTokenizer::from_nltk_data()?)
    }

    /// `word_tokenize(text)`: split into sentences, then tokenize each.
    pub fn word_tokenize(&self, text: &str) -> Vec<String> {
        self.sentences
            .sentences(text)
            .into_iter()
            .flat_map(|s| self.words.tokenize_sentence(s))
            .collect()
    }

    /// The vectorizer's `tokenize`: lower-case, tokenize, stem every token.
    pub fn tokenize_and_stem(&self, text: &str) -> Vec<String> {
        self.word_tokenize(&text.to_lowercase())
            .iter()
            .map(|t| self.stemmer.stem(t))
            .collect()
    }

    pub fn stem(&self, word: &str) -> String {
        self.stemmer.stem(word)
    }
}
