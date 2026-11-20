"""Shared test-input generator for the Python-vs-Rust comparisons."""
import json, os, random


def make_cases(repo):
    """Deterministic list of ~49k strings: real utterances, joined sentences,
    hard punctuation cases, random fuzz, and stemmer stress words."""
    rng = random.Random(7)

    def py_tokenize(text):                      # copied from app/chatbot/initializer.py
        return [stemmer.stem(t) for t in word_tokenize(text.lower())]

    utts = []
    for f in ["base-corpus.json", "rhcp-corpus-v2.json", "rhcp-corpus.json"]:
        for item in json.load(open(os.path.join(repo, "app/chatbot/data/training", f), encoding="utf-8"))["data"]:
            utts += item["utterances"]

    cases = []
    # 1. real utterances, as written and in odd casings
    for u in utts:
        cases += [u, u.upper(), u.title(), u + ".", u + "?!", "  " + u + "  \n"]
    # 2. two/three utterances joined with every kind of separator
    seps = [". ", "? ", "! ", ", ", "... ", " ", "?! ", "; ", ".\n", "\n", " - ", ": ", ".) ", '." ', "!!! ", " ... "]
    for _ in range(12000):
        parts = rng.sample(utts, rng.choice([2, 2, 3]))
        s = parts[0]
        for p in parts[1:]:
            s += rng.choice(seps) + p
        cases.append(s)
    # 3. hand-picked hard cases: abbreviations, initials, numbers, quotes, brackets, urls, contractions
    cases += [
        "Mr. Smith went to Washington. He was a U.S. senator.", "j. s. bach wrote it", "dr. flea and mr. kiedis",
        "released in 1991. then 1999.", "it cost $3.88 (roughly 3,36 euros) in New York.  Please buy me two.", "e.g. this, i.e. that",
        "he said \"hello there\" and left.", "'quoted' text and 'nested \"double\" quotes'", "don't can't won't I'm you're they've it's",
        "cannot gimme gonna gotta lemme wanna more'n d'ye", "'tis 'twas", "wait... what?! no way...", "a -- b --- c", "(parenthetical.) next one",
        "[brackets] {braces} <angles>", "visit http://example.com/a.b?c=d. now", "u.s.a. vs. u.k.", "3.14 is pi. 2.71 is e.", "end with comma,", "colon: then text",
        "“curly quotes” and ‘single’ and «guillemets»", "wait… no", "— em dash – en dash", "tab\tseparated\ttext", "line one\nline two. line three",
        "", " ", ".", "?", "...", "a.", "a. b. c.", "!!!", "hello", "hello.", "hello .", "  .  ", "x" * 300 + ".", "who is flea?  tell me.\n\nthen more",
        "it's about under the bridge. also the album's tracks!", "I'm good. you? fine. thanks.", "ok. thanks", "bye.", "hi! how are you? i'm fine.",
        "St. Louis", "Jan. 5th and Feb. 6th", "No. 1 hit", "vol. 2 no. 3", "p.m. and a.m.", "J. R. R. Tolkien", "etc.", "approx. 5 min.", "ph.d. student",
    ]
    # 4. random fuzz over a punctuation-heavy alphabet
    words = sorted({w for u in utts for w in u.lower().replace("?", " ").replace(".", " ").split()})
    punct = list(".,;:!?'\"()[]{}<>-*@#$%&/\\|~^`") + ["...", "--", "''", "``", "“", "”", "‘", "’", "«", "»", "…", "—", "–", "n't", "'s", "'re"]
    for _ in range(25000):
        toks = []
        for _ in range(rng.randint(1, 14)):
            r = rng.random()
            toks.append(rng.choice(words) if r < 0.55 else rng.choice(punct) if r < 0.9 else str(rng.randint(0, 3000)) + rng.choice(["", ".", ",", ".5", "th"]))
        glue = [rng.choice(["", " ", " ", " ", "  ", "\n", "\t"]) for _ in toks]
        cases.append("".join(t + g for t, g in zip(toks, glue)))
    # 5. stemmer-only stress: many suffix combinations on real words
    suffixes = ["", "s", "es", "ed", "ing", "ly", "ies", "ied", "ation", "ational", "ness", "ful", "fulness", "ize", "ization", "ive", "iveness", "alli", "logi", "bli", "eli", "ousli", "able", "ible", "ement", "ment", "ent", "ion", "ou", "ism", "ate", "iti", "ous", "ll", "y", "e", "al", "er", "ic", "ance", "ence", "ant", "ator", "iviti", "biliti", "aliti"]
    for w in rng.sample(words, min(len(words), 2500)):
        for suf in rng.sample(suffixes, 6):
            cases.append(w + suf)


    return cases
