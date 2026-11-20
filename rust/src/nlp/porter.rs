//! Porter stemmer: cuts a word down to its stem ("running" -> "run").
//!
//! Python equivalent: `nltk.stem.PorterStemmer()` in its default
//! `NLTK_EXTENSIONS` mode, which is what `app/chatbot/initializer.py` used.
//! This is a rule-by-rule port of NLTK's source so the stems (and therefore the
//! words the saved model knows) are identical.
//!
//! It works on `char`s, not bytes, because Rust strings are UTF-8 and a
//! "position in the word" must mean a letter, not a byte.

use std::collections::HashMap;

/// A suffix rule: `(suffix, replacement, condition on the remaining stem)`.
type Condition<'a> = Option<Box<dyn Fn(&Porter, &str) -> bool + 'a>>;

pub struct Porter {
    /// Irregular words handled before any rule runs ("skies" -> "sky").
    pool: HashMap<&'static str, &'static str>,
}

impl Default for Porter {
    fn default() -> Self {
        Self::new()
    }
}

fn is_vowel(c: char) -> bool {
    matches!(c, 'a' | 'e' | 'i' | 'o' | 'u')
}

/// `word[:-n]` for characters.
fn drop_last(word: &str, n: usize) -> String {
    let count = word.chars().count();
    word.chars().take(count.saturating_sub(n)).collect()
}

fn chars(word: &str) -> Vec<char> {
    word.chars().collect()
}

impl Porter {
    pub fn new() -> Self {
        let irregular: [(&'static str, &[&'static str]); 12] = [
            ("sky", &["sky", "skies"]),
            ("die", &["dying"]),
            ("lie", &["lying"]),
            ("tie", &["tying"]),
            ("news", &["news"]),
            ("inning", &["innings", "inning"]),
            ("outing", &["outings", "outing"]),
            ("canning", &["cannings", "canning"]),
            ("howe", &["howe"]),
            ("proceed", &["proceed"]),
            ("exceed", &["exceed"]),
            ("succeed", &["succeed"]),
        ];
        let mut pool = HashMap::new();
        for (stem, forms) in irregular {
            for form in forms {
                pool.insert(*form, stem);
            }
        }
        Self { pool }
    }

    /// Is the letter at `i` a consonant? "y" counts as a vowel after a
    /// consonant, so this walks back over a run of y's (NLTK `_is_consonant`).
    fn is_consonant(&self, word: &[char], mut i: usize) -> bool {
        if is_vowel(word[i]) {
            return false;
        }
        if word[i] == 'y' {
            let mut negate = false;
            while i > 0 && word[i] == 'y' {
                negate = !negate;
                i -= 1;
            }
            return !is_vowel(word[i]) != negate;
        }
        true
    }

    /// Same question for every letter at once (NLTK `_consonant_flags`).
    fn consonant_flags(&self, word: &str) -> Vec<bool> {
        let mut flags: Vec<bool> = Vec::new();
        for (i, ch) in word.chars().enumerate() {
            let flag = if is_vowel(ch) {
                false
            } else if ch == 'y' {
                if i == 0 { true } else { !flags[i - 1] }
            } else {
                true
            };
            flags.push(flag);
        }
        flags
    }

    /// Porter's "measure": how many vowel-then-consonant groups the stem has.
    fn measure(&self, stem: &str) -> usize {
        let cv: String = self
            .consonant_flags(stem)
            .iter()
            .map(|c| if *c { 'c' } else { 'v' })
            .collect();
        cv.matches("vc").count()
    }

    fn has_positive_measure(&self, stem: &str) -> bool {
        self.measure(stem) > 0
    }

    fn contains_vowel(&self, stem: &str) -> bool {
        !self.consonant_flags(stem).iter().all(|c| *c)
    }

    fn ends_double_consonant(&self, word: &str) -> bool {
        let w = chars(word);
        w.len() >= 2 && w[w.len() - 1] == w[w.len() - 2] && self.is_consonant(&w, w.len() - 1)
    }

    fn ends_cvc(&self, word: &str) -> bool {
        let w = chars(word);
        let n = w.len();
        (n >= 3
            && self.is_consonant(&w, n - 3)
            && !self.is_consonant(&w, n - 2)
            && self.is_consonant(&w, n - 1)
            && !matches!(w[n - 1], 'w' | 'x' | 'y'))
            // NLTK extension: two-letter words like "at" also count.
            || (n == 2 && !self.is_consonant(&w, 0) && self.is_consonant(&w, 1))
    }

    /// Try the rules in order; the first rule whose suffix matches decides.
    /// (Even if its condition fails, no later rule is tried.)
    fn apply_rule_list(&self, word: &str, rules: Vec<(&str, String, Condition<'_>)>) -> String {
        for (suffix, replacement, condition) in rules {
            if suffix == "*d" && self.ends_double_consonant(word) {
                let stem = drop_last(word, 2);
                return if condition.as_ref().is_none_or(|c| c(self, &stem)) {
                    stem + &replacement
                } else {
                    word.to_string()
                };
            }
            if word.ends_with(suffix) {
                let stem = drop_last(word, suffix.chars().count());
                return if condition.as_ref().is_none_or(|c| c(self, &stem)) {
                    stem + &replacement
                } else {
                    word.to_string()
                };
            }
        }
        word.to_string()
    }

    fn step1a(&self, word: &str) -> String {
        if word.ends_with("ies") && word.chars().count() == 4 {
            return drop_last(word, 3) + "ie";
        }
        self.apply_rule_list(
            word,
            vec![
                ("sses", "ss".into(), None),
                ("ies", "i".into(), None),
                ("ss", "ss".into(), None),
                ("s", String::new(), None),
            ],
        )
    }

    fn step1b(&self, word: &str) -> String {
        if word.ends_with("ied") {
            return if word.chars().count() == 4 {
                drop_last(word, 3) + "ie"
            } else {
                drop_last(word, 3) + "i"
            };
        }
        if word.ends_with("eed") {
            let stem = drop_last(word, 3);
            return if self.measure(&stem) > 0 {
                stem + "ee"
            } else {
                word.to_string()
            };
        }

        let mut intermediate: Option<String> = None;
        for suffix in ["ed", "ing"] {
            if word.ends_with(suffix) {
                let candidate = drop_last(word, suffix.chars().count());
                if self.contains_vowel(&candidate) {
                    intermediate = Some(candidate);
                    break;
                }
            }
        }
        let Some(intermediate) = intermediate else {
            return word.to_string();
        };

        let last: char = intermediate.chars().last().expect("contains a vowel, so not empty");
        self.apply_rule_list(
            &intermediate,
            vec![
                ("at", "ate".into(), None),
                ("bl", "ble".into(), None),
                ("iz", "ize".into(), None),
                // double consonant -> single, unless it is l, s or z
                (
                    "*d",
                    last.to_string(),
                    Some(Box::new(move |_, _| !matches!(last, 'l' | 's' | 'z'))),
                ),
                (
                    "",
                    "e".into(),
                    Some(Box::new(|p, stem| p.measure(stem) == 1 && p.ends_cvc(stem))),
                ),
            ],
        )
    }

    fn step1c(&self, word: &str) -> String {
        self.apply_rule_list(
            word,
            vec![(
                "y",
                "i".into(),
                Some(Box::new(|p, stem| {
                    let s = chars(stem);
                    s.len() > 1 && p.is_consonant(&s, s.len() - 1)
                })),
            )],
        )
    }

    fn step2(&self, word: &str) -> String {
        if word.ends_with("alli") && self.has_positive_measure(&drop_last(word, 4)) {
            return self.step2(&(drop_last(word, 4) + "al"));
        }
        let pm = || -> Condition<'_> { Some(Box::new(|p, s| p.has_positive_measure(s))) };
        let owned_word = word.to_string();
        let rules: Vec<(&str, String, Condition<'_>)> = vec![
            ("ational", "ate".into(), pm()),
            ("tional", "tion".into(), pm()),
            ("enci", "ence".into(), pm()),
            ("anci", "ance".into(), pm()),
            ("izer", "ize".into(), pm()),
            ("bli", "ble".into(), pm()),
            ("alli", "al".into(), pm()),
            ("entli", "ent".into(), pm()),
            ("eli", "e".into(), pm()),
            ("ousli", "ous".into(), pm()),
            ("ization", "ize".into(), pm()),
            ("ation", "ate".into(), pm()),
            ("ator", "ate".into(), pm()),
            ("alism", "al".into(), pm()),
            ("iveness", "ive".into(), pm()),
            ("fulness", "ful".into(), pm()),
            ("ousness", "ous".into(), pm()),
            ("aliti", "al".into(), pm()),
            ("iviti", "ive".into(), pm()),
            ("biliti", "ble".into(), pm()),
            ("fulli", "ful".into(), pm()),
            // NLTK quirk: the "logi" rule checks the measure of `word[:-3]`, not of the stem.
            (
                "logi",
                "log".into(),
                Some(Box::new(move |p, _| p.has_positive_measure(&drop_last(&owned_word, 3)))),
            ),
        ];
        self.apply_rule_list(word, rules)
    }

    fn step3(&self, word: &str) -> String {
        let pm = || -> Condition<'_> { Some(Box::new(|p, s| p.has_positive_measure(s))) };
        self.apply_rule_list(
            word,
            vec![
                ("icate", "ic".into(), pm()),
                ("ative", String::new(), pm()),
                ("alize", "al".into(), pm()),
                ("iciti", "ic".into(), pm()),
                ("ical", "ic".into(), pm()),
                ("ful", String::new(), pm()),
                ("ness", String::new(), pm()),
            ],
        )
    }

    fn step4(&self, word: &str) -> String {
        let gt1 = || -> Condition<'_> { Some(Box::new(|p, s| p.measure(s) > 1)) };
        self.apply_rule_list(
            word,
            vec![
                ("al", String::new(), gt1()),
                ("ance", String::new(), gt1()),
                ("ence", String::new(), gt1()),
                ("er", String::new(), gt1()),
                ("ic", String::new(), gt1()),
                ("able", String::new(), gt1()),
                ("ible", String::new(), gt1()),
                ("ant", String::new(), gt1()),
                ("ement", String::new(), gt1()),
                ("ment", String::new(), gt1()),
                ("ent", String::new(), gt1()),
                (
                    "ion",
                    String::new(),
                    Some(Box::new(|p, s| {
                        p.measure(s) > 1 && s.chars().last().is_some_and(|c| c == 's' || c == 't')
                    })),
                ),
                ("ou", String::new(), gt1()),
                ("ism", String::new(), gt1()),
                ("ate", String::new(), gt1()),
                ("iti", String::new(), gt1()),
                ("ous", String::new(), gt1()),
                ("ive", String::new(), gt1()),
                ("ize", String::new(), gt1()),
            ],
        )
    }

    fn step5a(&self, word: &str) -> String {
        if word.ends_with('e') {
            let stem = drop_last(word, 1);
            if self.measure(&stem) > 1 {
                return stem;
            }
            if self.measure(&stem) == 1 && !self.ends_cvc(&stem) {
                return stem;
            }
        }
        word.to_string()
    }

    fn step5b(&self, word: &str) -> String {
        let owned = word.to_string();
        self.apply_rule_list(
            word,
            vec![(
                "ll",
                "l".into(),
                Some(Box::new(move |p, _| p.measure(&drop_last(&owned, 1)) > 1)),
            )],
        )
    }

    /// Stem one word (lower-cased first, like NLTK).
    pub fn stem(&self, word: &str) -> String {
        let lowered = word.to_lowercase();
        if let Some(irregular) = self.pool.get(lowered.as_str()) {
            return (*irregular).to_string();
        }
        // NLTK checks the length of the ORIGINAL word here.
        if word.chars().count() <= 2 {
            return lowered;
        }
        let mut stem = self.step1a(&lowered);
        stem = self.step1b(&stem);
        stem = self.step1c(&stem);
        stem = self.step2(&stem);
        stem = self.step3(&stem);
        stem = self.step4(&stem);
        stem = self.step5a(&stem);
        self.step5b(&stem)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn classic_examples() {
        let p = Porter::new();
        for (word, stem) in [
            ("caresses", "caress"),
            ("ponies", "poni"),
            ("running", "run"),
            ("happiness", "happi"),
            ("relational", "relat"),
            ("conditional", "condit"),
            ("generalization", "gener"),
            ("agreed", "agre"),
            ("hopping", "hop"),
            ("skies", "sky"),
            ("dying", "die"),
            ("is", "is"),
            ("Albums", "album"),
        ] {
            assert_eq!(p.stem(word), stem, "{word}");
        }
    }
}
