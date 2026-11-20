//! Entity recognition and response writing. Python equivalent:
//! `app/chatbot/processor.py` (class `ChatbotProcessor`).
//!
//! Responsibilities:
//! * build lists of every way a user might name a band member, album or song
//!   (nicknames, abbreviations) from the static data files;
//! * find those names in a message (`find_entities`);
//! * write a reply for an intent + entities (`generate_basic_response` and the
//!   follow-up handling);
//! * the older all-in-one `process_message` flow.
//!
//! Behaviour is transcribed from the Python, including its quirks. Where a quirk
//! looks like a bug it is kept and noted, because the goal is a faithful port.

use std::sync::{Arc, Mutex};

use rand::seq::IndexedRandom;
use regex::Regex;
use serde_json::{Map, Value, json};

use crate::data::{StaticData, TrainingData};
use crate::memory::{BotResponse, ConversationMemory};
use crate::nlp::classifier::Classifier;
use crate::nlp::tokenizer::TextAnalyzer;
use crate::pyfmt::py_str;

/// An entity as a JSON object, exactly as the Python dicts looked.
pub type RawEntity = Map<String, Value>;

/// The legacy threshold used by `process_message` (the API uses 0.60).
pub const LEGACY_CONFIDENCE_THRESHOLD: f64 = 0.05;

/// Text analysis + classifier, shared by everything that needs probabilities.
pub struct Nlu {
    pub analyzer: TextAnalyzer,
    pub classifier: Classifier,
}

impl Nlu {
    /// `(label, probability)` best first (Python: `get_classifications`).
    pub fn classifications(&self, message: &str) -> Vec<(String, f64)> {
        self.classifier.classifications(&self.analyzer, message)
    }
}

struct Variation {
    text: String,
    regex: Regex,
}

fn variations(texts: Vec<String>) -> Vec<Variation> {
    texts
        .into_iter()
        .map(|text| {
            let regex = Regex::new(&format!(r"\b{}\b", regex::escape(&text))).expect("escaped text is a valid pattern");
            Variation { text, regex }
        })
        .collect()
}

/// `name.split()[0]` / `name.split()[-1]`
fn first_last_word(name: &str) -> (String, String) {
    let words: Vec<&str> = name.split_whitespace().collect();
    (
        words.first().copied().unwrap_or("").to_string(),
        words.last().copied().unwrap_or("").to_string(),
    )
}

fn base_variations(name: &str) -> Vec<String> {
    let (first, last) = first_last_word(name);
    vec![
        name.to_string(),
        name.replace('\'', ""),
        name.replace(' ', ""),
        first,
        last,
    ]
}

fn strs(items: &[&str]) -> Vec<String> {
    items.iter().map(|s| s.to_string()).collect()
}

struct MemberInfo {
    variations: Vec<Variation>,
    details: Map<String, Value>,
    member_type: &'static str,
}

struct AlbumInfo {
    name: String,
    variations: Vec<Variation>,
    details: Map<String, Value>,
    album_type: String,
}

struct SongInfo {
    name: String,
    variations: Vec<Variation>,
    album: String,
    album_details: Map<String, Value>,
}

pub struct ChatbotProcessor {
    nlu: Arc<Nlu>,
    training_data: TrainingData,
    memory: Option<Mutex<ConversationMemory>>,
    members: Vec<MemberInfo>,
    albums: Vec<AlbumInfo>,
    songs: Vec<SongInfo>,
    static_data: StaticData,
}

fn album_extras(name: &str) -> Vec<String> {
    // Python: an if/elif chain, so only the first matching branch applies.
    let extras: &[&str] = if name.contains("blood sugar sex magik") {
        &["blood sugar", "bssm", "blood sugar sex magic"]
    } else if name.contains("californication") {
        &["cali", "californication"]
    } else if name.contains("by the way") {
        &["btw", "by the way"]
    } else if name.contains("stadium arcadium") {
        &["stadium", "arcadium", "sa"]
    } else if name.contains("unlimited love") {
        &["unlimited", "ul"]
    } else if name.contains("the getaway") {
        &["getaway", "tg"]
    } else if name.contains("i'm with you") {
        &["im with you", "iwy"]
    } else if name.contains("one hot minute") {
        &["ohm", "one hot minute"]
    } else if name.contains("mother's milk") {
        &["mothers milk", "mother milk", "mm"]
    } else if name.contains("uplift mofo party plan") {
        &["uplift", "mofo", "umpp"]
    } else if name.contains("freaky styley") {
        &["freaky", "styley", "fs"]
    } else if name.contains("the red hot chili peppers") {
        &["debut", "first album", "rhcp debut"]
    } else {
        &[]
    };
    strs(extras)
}

fn song_extras(name: &str) -> Vec<String> {
    let extras: &[&str] = if name.contains("under the bridge") {
        &["utb", "under bridge"]
    } else if name.contains("californication") {
        &["cali"]
    } else if name.contains("scar tissue") {
        &["scar"]
    } else if name.contains("otherside") {
        &["other side"]
    } else if name.contains("by the way") {
        &["btw"]
    } else if name.contains("dani california") {
        &["dani", "dani cali"]
    } else if name.contains("snow (hey oh)") {
        &["snow", "hey oh", "snow hey oh"]
    } else if name.contains("give it away") {
        &["give away", "gia"]
    } else if name.contains("breaking the girl") {
        &["breaking girl", "btg"]
    } else if name.contains("suck my kiss") {
        &["smk"]
    } else if name.contains("around the world") {
        &["atw"]
    } else if name.contains("parallel universe") {
        &["parallel", "pu"]
    } else if name.contains("get on top") {
        &["got"]
    } else if name.contains("easily") {
        &["easy"]
    } else if name.contains("porcelain") {
        &["porc"]
    } else if name.contains("emit remmus") {
        &["emit", "remmus"]
    } else if name.contains("i like dirt") {
        &["dirt"]
    } else if name.contains("this velvet glove") {
        &["velvet glove", "tvg"]
    } else if name.contains("savior") {
        &["save"]
    } else if name.contains("purple stain") {
        &["purple", "stain"]
    } else if name.contains("right on time") {
        &["rot"]
    } else if name.contains("road trippin") {
        &["road trip", "rt"]
    } else if name.contains("black summer") {
        &["black", "summer", "bs"]
    } else if name.contains("here ever after") {
        &["here after", "hea"]
    } else if name.contains("aquatic mouth dance") {
        &["aquatic", "mouth dance", "amd"]
    } else if name.contains("not the one") {
        &["nto"]
    } else if name.contains("poster child") {
        &["poster", "child", "pc"]
    } else if name.contains("the great apes") {
        &["great apes", "tga"]
    } else if name.contains("it's only natural") {
        &["its only natural", "ion", "natural"]
    } else if name.contains("she's a lover") {
        &["shes a lover", "sal", "lover"]
    } else if name.contains("these are the ways") {
        &["these ways", "tatw", "ways"]
    } else if name.contains("whatchu thinkin") {
        &["whatchu", "thinkin", "wt"]
    } else if name.contains("bastards of light") {
        &["bastards", "light", "bol"]
    } else if name.contains("white braids & pillow chair") {
        &["white braids", "pillow chair", "wbp", "braids", "pillow"]
    } else {
        &[]
    };
    strs(extras)
}

fn current_member_extras(name: &str) -> Vec<String> {
    let extras: &[&str] = if name.contains("flea") || name.contains("balzary") {
        &["flea", "michael flea", "michael balzary", "balzary", "mike flea"]
    } else if name.contains("anthony") || name.contains("kiedis") {
        &["anthony", "kiedis", "tony", "anthony kiedis", "ak"]
    } else if name.contains("john") || name.contains("frusciante") {
        &["john", "frusciante", "johnny", "john frusciante", "jf"]
    } else if name.contains("chad") || name.contains("smith") {
        &["chad", "smith", "chad smith", "chadwick"]
    } else {
        &[]
    };
    strs(extras)
}

fn former_member_extras(name: &str) -> Vec<String> {
    let extras: &[&str] = if name.contains("hillel") || name.contains("slovak") {
        &["hillel", "slovak", "hillel slovak"]
    } else if name.contains("jack") || name.contains("irons") {
        &["jack", "irons", "jack irons"]
    } else if name.contains("josh") || name.contains("klinghoffer") {
        &["josh", "klinghoffer", "josh klinghoffer", "jk"]
    } else if name.contains("dave") || name.contains("navarro") {
        &["dave", "navarro", "dave navarro", "dn"]
    } else {
        &[]
    };
    strs(extras)
}

fn name_of(item: &Map<String, Value>) -> String {
    item.get("name").and_then(Value::as_str).unwrap_or("").to_string()
}

/// `release_date.split("-")[0] if "-" in release_date else release_date`
fn year_of(release_date: &str) -> &str {
    release_date.split('-').next().unwrap_or(release_date)
}

impl ChatbotProcessor {
    pub fn new(
        nlu: Arc<Nlu>,
        training_data: TrainingData,
        static_data: StaticData,
        memory: Option<ConversationMemory>,
    ) -> Self {
        let mut members = Vec::new();
        for (list, member_type) in [("currentMembers", "current"), ("formerMembers", "former")] {
            for member in static_data.band_list(list) {
                let name = name_of(member).to_lowercase();
                let mut v = base_variations(&name);
                v.extend(if member_type == "current" {
                    current_member_extras(&name)
                } else {
                    former_member_extras(&name)
                });
                members.push(MemberInfo {
                    variations: variations(v),
                    details: member.clone(),
                    member_type,
                });
            }
        }

        let mut albums = Vec::new();
        let mut songs = Vec::new();
        for album_type in ["studioAlbums", "compilationAlbums", "liveAlbums"] {
            for album in static_data.album_list(album_type) {
                let name = name_of(album).to_lowercase();
                let mut v = vec![
                    name.clone(),
                    name.replace('\'', ""),
                    name.replace(' ', ""),
                    name.replace('&', "and"),
                ];
                v.extend(album_extras(&name));
                albums.push(AlbumInfo {
                    name,
                    variations: variations(v),
                    details: album.clone(),
                    album_type: album_type.to_string(),
                });
            }
        }
        // Songs come from every album's `tracks` list, after the albums are built.
        for album_type in ["studioAlbums", "compilationAlbums", "liveAlbums"] {
            for album in static_data.album_list(album_type) {
                if let Some(tracks) = album.get("tracks").and_then(Value::as_array) {
                    for track in tracks.iter().filter_map(Value::as_str) {
                        let name = track.to_lowercase();
                        let mut v = vec![
                            name.clone(),
                            name.replace('\'', ""),
                            name.replace(' ', ""),
                            name.replace('&', "and"),
                        ];
                        v.extend(song_extras(&name));
                        songs.push(SongInfo {
                            name,
                            variations: variations(v),
                            album: name_of(album),
                            album_details: album.clone(),
                        });
                    }
                }
            }
        }

        Self {
            nlu,
            training_data,
            memory: memory.map(Mutex::new),
            members,
            albums,
            songs,
            static_data,
        }
    }

    pub fn nlu(&self) -> &Nlu {
        &self.nlu
    }

    pub fn validate_static_data(&self) -> Vec<String> {
        self.static_data.validation_issues()
    }

    /// Mutable access to the processor's own memory (tests / CLI use `create_session`).
    pub fn with_memory<R>(&self, f: impl FnOnce(&mut ConversationMemory) -> R) -> Option<R> {
        self.memory.as_ref().map(|m| f(&mut m.lock().expect("memory lock")))
    }

    // ------------------------------------------------------------------ entities

    /// Find every known member, album and song named in `text` (already lower-case).
    pub fn find_entities(&self, text: &str) -> Vec<RawEntity> {
        fn first_match<'a>(vs: &'a [Variation], text: &str) -> Option<&'a str> {
            vs.iter()
                .find(|v| text.contains(&v.text) && v.regex.is_match(text))
                .map(|v| v.text.as_str())
        }
        let mut out = Vec::new();
        for m in &self.members {
            if let Some(matched) = first_match(&m.variations, text) {
                out.push(entity(
                    "member",
                    Value::Object(m.details.clone()),
                    matched,
                    &[("member_type", m.member_type)],
                ));
            }
        }
        for a in &self.albums {
            if let Some(matched) = first_match(&a.variations, text) {
                out.push(entity(
                    "album",
                    Value::Object(a.details.clone()),
                    matched,
                    &[("album_type", &a.album_type)],
                ));
            }
        }
        for s in &self.songs {
            if let Some(matched) = first_match(&s.variations, text) {
                let value = json!({"name": s.name, "album": s.album, "album_details": s.album_details});
                out.push(entity("song", value, matched, &[]));
            }
        }
        out
    }

    /// An entity whose name is both a song title and an album title ("Do you mean...?").
    fn detect_ambiguity(&self, entities: &[RawEntity]) -> Option<String> {
        for e in entities {
            let kind = e.get("type").and_then(Value::as_str).unwrap_or("");
            if kind != "song" && kind != "album" {
                continue;
            }
            let Some(name) = e.get("value").and_then(|v| v.get("name")).and_then(Value::as_str) else {
                continue;
            };
            let lowered = name.to_lowercase();
            let is_song = self.songs.iter().any(|s| s.name.to_lowercase() == lowered);
            let is_album = self.albums.iter().any(|a| a.name.to_lowercase() == lowered);
            if is_song && is_album {
                return Some(name.to_string());
            }
        }
        None
    }

    // ------------------------------------------------------------------ follow-ups

    fn enhance_message_with_context(&self, message: &str, session_id: Option<&str>) -> String {
        let (Some(memory), Some(session_id)) = (&self.memory, session_id) else {
            return message.to_string();
        };
        let ctx = memory.lock().expect("memory lock").follow_up_context(session_id);
        let lowered = message.to_lowercase();
        let mut enhanced = message.to_string();

        // Python truthiness: a missing OR empty slot counts as "no context".
        let slot = |v: &Option<String>| v.clone().filter(|s| !s.is_empty());
        let (album, song, member) = (slot(&ctx.last_album), slot(&ctx.last_song), slot(&ctx.last_member));
        // (an entirely empty context returns early in Python via `if not context`)
        if ctx == Default::default() {
            return enhanced;
        }

        if lowered.contains("in what year") || lowered.contains("when was") {
            if let Some(a) = &album {
                enhanced = format!("what year was {a} released");
            } else if let Some(s) = &song {
                enhanced = format!("what year was {s} released");
            }
        }
        if lowered.contains("who wrote") && !["album", "song", "track"].iter().any(|w| lowered.contains(w)) {
            if let Some(s) = &song {
                enhanced = format!("who wrote {s}");
            } else if let Some(a) = &album {
                enhanced = format!("who wrote songs on {a}");
            }
        }
        if lowered.contains("tell me more about") || lowered.contains("what about") {
            if let Some(m) = &member {
                enhanced = format!("tell me about {m}");
            } else if let Some(a) = &album {
                enhanced = format!("tell me about {a}");
            } else if let Some(s) = &song {
                enhanced = format!("tell me about {s}");
            }
        }
        enhanced
    }

    fn is_follow_up_question(message: &str) -> bool {
        let lowered = message.to_lowercase();
        [
            "in what year",
            "when was",
            "who wrote",
            "tell me more",
            "what about",
            "how about",
            "and",
            "also",
            "too",
        ]
        .iter()
        .any(|w| lowered.contains(w))
    }

    fn album_year(&self, album_name: &str) -> Option<String> {
        let wanted = album_name.to_lowercase();
        for album in self.albums.iter().filter(|a| a.name.to_lowercase() == wanted) {
            let release = album.details.get("releaseDate").map(py_str).unwrap_or_default();
            if !release.is_empty() {
                return Some(year_of(&release).to_string());
            }
        }
        None
    }

    fn handle_follow_up_question(
        &self,
        message: &str,
        intent: &str,
        entities: &[RawEntity],
        ctx: &crate::memory::FollowUpContext,
    ) -> String {
        let lowered = message.to_lowercase();
        let slot = |v: &Option<String>| v.clone().filter(|s| !s.is_empty());

        if lowered.contains("in what year") || lowered.contains("when was") {
            if let Some(album) = slot(&ctx.last_album) {
                return match self.album_year(&album) {
                    Some(year) => format!("{album} was released in {year}."),
                    None => format!("I don't have the release year for {album}."),
                };
            } else if let Some(song) = slot(&ctx.last_song) {
                for s in self
                    .songs
                    .iter()
                    .filter(|s| s.name.to_lowercase() == song.to_lowercase())
                {
                    if !s.album.is_empty() {
                        if let Some(year) = self.album_year(&s.album) {
                            return format!("{song} was released in {year} on the album {}.", s.album);
                        }
                    }
                }
                return format!("I don't have the release year for {song}.");
            }
        }

        if lowered.contains("who wrote") {
            if let Some(song) = slot(&ctx.last_song) {
                // Quirk kept from Python: song records have no "details" key, so the
                // writers list is always empty and this answer is always the same.
                if self.songs.iter().any(|s| s.name.to_lowercase() == song.to_lowercase()) {
                    return format!("I don't have writer information for {song}.");
                }
            }
        }

        self.generate_basic_response(intent, entities)
    }

    // ------------------------------------------------------------------ responses

    /// Entry point used by the API pipeline (`message` is `""` there, so the
    /// follow-up branch never runs over HTTP).
    pub fn generate_contextual_response(
        &self,
        message: &str,
        intent: &str,
        entities: &[RawEntity],
        session_id: Option<&str>,
    ) -> String {
        if let Some(name) = self.detect_ambiguity(entities) {
            return format!("Do you mean the song or the album '{name}'?");
        }
        if Self::is_follow_up_question(message) {
            if let (Some(memory), Some(session_id)) = (&self.memory, session_id) {
                let (ctx, history) = {
                    let m = memory.lock().expect("memory lock");
                    (m.follow_up_context(session_id), m.conversation_history(session_id, 3))
                };
                if !history.is_empty() {
                    return self.handle_follow_up_question(message, intent, entities, &ctx);
                }
            }
        }
        self.generate_basic_response(intent, entities)
    }

    pub fn generate_basic_response(&self, intent: &str, entities: &[RawEntity]) -> String {
        let find = |kind: &str| {
            entities
                .iter()
                .find(|e| e.get("type").and_then(Value::as_str) == Some(kind))
        };
        let member_entity = find("member");
        let album_entity = find("album");
        let song_entity = find("song");

        let mut response = String::new();
        let mut handled = false;

        if intent == "unrecognized" || intent == "None" {
            response = "I'm not sure I understood that. Could you try asking about the band members, albums, songs, or band history?".into();
            handled = true;
        } else if intent == "member.biography"
            && let Some(entity) = member_entity
        {
            let member = entity
                .get("value")
                .and_then(Value::as_object)
                .cloned()
                .unwrap_or_default();
            let name = member.get("name").map(py_str).unwrap_or_default();
            let member_since = member
                .get("memberSince")
                .map(py_str)
                .unwrap_or_else(|| "unknown year".into());
            let lowered = name.to_lowercase();
            response = if ["anthony kiedis", "anthony", "kiedis"].contains(&lowered.as_str()) {
                format!(
                    "Anthony Kiedis is the lead vocalist and primary lyricist of RHCP. He's been with the band since {member_since} and is known for his unique vocal style and energetic stage presence. He's also written a memoir called 'Scar Tissue' about his life and struggles."
                )
            } else if ["flea", "michael flea", "michael balzary"].contains(&lowered.as_str()) {
                format!(
                    "Flea (Michael Balzary) is the bassist and co-founding member of RHCP. He's been with the band since {member_since} and is known for his distinctive funky bass lines, energetic performances, and his work as an actor. He's considered one of the most influential bassists in rock music."
                )
            } else if ["john frusciante", "john", "frusciante"].contains(&lowered.as_str()) {
                "John Frusciante is the guitarist of RHCP. He first joined in 1988, left in 1992, returned in 1998, left again in 2009, and rejoined in 2019. He's known for his unique guitar style, melodic solos, and contributions to albums like 'Blood Sugar Sex Magik' and 'Californication'.".to_string()
            } else if ["chad smith", "chad", "smith"].contains(&lowered.as_str()) {
                format!(
                    "Chad Smith is the drummer of RHCP, joining in {member_since}. He's known for his powerful drumming style, technical proficiency, and his work with other bands like Chickenfoot. He's been a consistent member and has played on most of their albums."
                )
            } else {
                match member.get("biography") {
                    Some(b) => py_str(b),
                    None => format!("I know about {name}, but I don't have a detailed biography."),
                }
            };
            handled = true;
        } else if intent == "album.specific"
            && let Some(entity) = album_entity
        {
            let album = entity
                .get("value")
                .and_then(Value::as_object)
                .cloned()
                .unwrap_or_default();
            let album_name = album.get("name").map(py_str).unwrap_or_default();
            let release_date = album
                .get("releaseDate")
                .map(py_str)
                .unwrap_or_else(|| "unknown date".into());
            let producer = album
                .get("producer")
                .map(py_str)
                .unwrap_or_else(|| "unknown producer".into());
            let lowered = album_name.to_lowercase();
            let head = format!("'{album_name}' was released on {release_date} and produced by {producer}");
            response = match lowered.as_str() {
                "blood sugar sex magik" | "blood sugar" => format!(
                    "{head}. This album was a breakthrough for RHCP, featuring hits like 'Under the Bridge' and 'Give It Away'. It's considered one of their most influential albums and helped define the alternative rock sound of the 1990s."
                ),
                "californication" => format!(
                    "{head}. This album marked a return to form for the band and includes hits like 'Scar Tissue', 'Otherside', and 'Californication'. It's one of their most successful albums commercially."
                ),
                "by the way" => format!(
                    "{head}. This album shows a more melodic side of RHCP with hits like 'By the Way' and 'Can't Stop'. It's known for its more polished sound compared to their earlier work."
                ),
                "stadium arcadium" => format!(
                    "{head}. This double album won the Grammy for Best Rock Album and includes hits like 'Dani California' and 'Snow (Hey Oh)'. It's one of their most ambitious projects."
                ),
                "unlimited love" => format!(
                    "{head}. This is their latest album and marks the return of John Frusciante to the band. It includes the hit single 'Black Summer' and shows the band returning to their classic sound."
                ),
                _ => {
                    let mut info = head;
                    if let Some(tracks) = album.get("tracks").and_then(Value::as_array).filter(|t| !t.is_empty()) {
                        let preview: Vec<String> = tracks.iter().take(5).map(py_str).collect();
                        info.push_str(&format!(
                            ". It includes tracks like {}{}.",
                            preview.join(", "),
                            if tracks.len() > 5 { "..." } else { "" }
                        ));
                    }
                    info
                }
            };
            handled = true;
        } else if (intent == "song.specific" || intent == "song.lyrics")
            && let Some(entity) = song_entity
        {
            let song = entity
                .get("value")
                .and_then(Value::as_object)
                .cloned()
                .unwrap_or_default();
            let song_name = song.get("name").map(py_str).unwrap_or_default();
            let album_name = song.get("album").map(py_str).unwrap_or_default();
            response = match song_name.to_lowercase().as_str() {
                "under the bridge" => format!(
                    "'{song_name}' is from the album '{album_name}'. It's one of RHCP's most iconic songs, written by Anthony Kiedis about his feelings of isolation in Los Angeles. The song features a beautiful melody and is considered one of their signature tracks."
                ),
                "californication" => format!(
                    "'{song_name}' is from the album '{album_name}'. This song critiques the artificial nature of Hollywood and California culture. It features John Frusciante's distinctive guitar work and is one of their most recognizable songs."
                ),
                "scar tissue" => format!(
                    "'{song_name}' is from the album '{album_name}'. This song deals with themes of addiction and recovery, reflecting Anthony Kiedis's personal struggles. It won a Grammy for Best Rock Song."
                ),
                "otherside" => format!(
                    "'{song_name}' is from the album '{album_name}'. This song addresses the theme of drug addiction and the struggle to overcome it. It features a memorable bass line from Flea and emotional vocals from Kiedis."
                ),
                "by the way" => format!(
                    "'{song_name}' is from the album '{album_name}'. This song shows a more melodic side of RHCP with its catchy chorus and harmonies. It was a major hit and helped define their sound in the 2000s."
                ),
                _ => format!(
                    "'{song_name}' is from the album '{album_name}'. It's a great track that showcases the band's unique style and musical chemistry."
                ),
            };
            handled = true;
        }

        if !handled && intent != "unrecognized" && intent != "None" {
            if let Some(answers) = self.training_data.answers_for(intent) {
                if let Some(answer) = answers.choose(&mut rand::rng()) {
                    response = answer.clone();
                }
            }
            if response.is_empty() {
                response = format!(
                    "I understood your intent is '{intent}', but I don't have a specific response for that yet."
                );
            }
        }
        if response.is_empty() {
            response = "Sorry, I couldn't process your request. Try asking about band members, albums, songs, or band history!".into();
        }
        response
    }

    // ------------------------------------------------------------------ legacy flow

    /// The older single-call pipeline (Python `process_message`). The HTTP API and
    /// the CLI use `inference::run_inference` instead; this stays for parity and tests.
    pub fn process_message(&self, message: &str, session_id: Option<&str>) -> Value {
        let enhanced = self.enhance_message_with_context(message, session_id);
        let clean = enhanced.to_lowercase();
        let classifications = self.nlu.classifications(&clean);

        let (mut intent, mut confidence) = ("unknown".to_string(), 0.0_f64);
        if let Some((label, value)) = classifications.first() {
            confidence = *value;
            if confidence >= LEGACY_CONFIDENCE_THRESHOLD {
                intent = label.clone();
            }
        }

        let entities = self.find_entities(&clean);
        let types: Vec<&str> = entities
            .iter()
            .filter_map(|e| e.get("type").and_then(Value::as_str))
            .collect();

        // Entity-based override when confidence is low
        if !entities.is_empty() && confidence < LEGACY_CONFIDENCE_THRESHOLD {
            if types.contains(&"album") {
                (intent, confidence) = ("album.info".into(), 0.5);
            } else if types.contains(&"song") {
                (intent, confidence) = ("song.info".into(), 0.5);
            } else if types.contains(&"member") {
                (intent, confidence) = ("member.biography".into(), 0.5);
            }
        }
        // ...and also whenever the intent does not fit the entities found
        if !entities.is_empty() {
            let i = intent.as_str();
            let matches = (types.contains(&"album") && ["album.specific", "album.info"].contains(&i))
                || (types.contains(&"song") && ["song.specific", "song.info", "song.lyrics"].contains(&i))
                || (types.contains(&"member") && ["member.biography", "band.members"].contains(&i));
            if !matches {
                if types.contains(&"album") {
                    (intent, confidence) = ("album.info".into(), 0.5);
                } else if types.contains(&"song") {
                    (intent, confidence) = ("song.info".into(), 0.5);
                } else if types.contains(&"member") {
                    (intent, confidence) = ("member.biography".into(), 0.5);
                }
            }
        }

        let message_text = self.generate_contextual_response(message, &intent, &entities, session_id);
        if let (Some(memory), Some(session_id)) = (&self.memory, session_id) {
            memory.lock().expect("memory lock").add_message(
                session_id,
                message,
                &BotResponse {
                    message: message_text.clone(),
                    intent: Some(intent.clone()),
                    confidence: Some(confidence),
                    entities: entities.clone(),
                },
            );
        }
        json!({
            "message": message_text,
            "intent": intent,
            "confidence": confidence,
            "entities": entities,
        })
    }
}

fn entity(kind: &str, value: Value, matched: &str, extra: &[(&str, &str)]) -> RawEntity {
    let mut m = Map::new();
    m.insert("type".into(), json!(kind));
    m.insert("value".into(), value);
    m.insert("matched_text".into(), json!(matched));
    for (k, v) in extra {
        m.insert((*k).into(), json!(v));
    }
    m
}
