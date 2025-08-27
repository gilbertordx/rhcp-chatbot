import random
import re
from typing import Any

CONFIDENCE_THRESHOLD = 0.05  # Adjusted threshold based on actual model performance


class ChatbotProcessor:
    def __init__(self, classifier, training_data, static_data, memory_manager=None):
        self.classifier = classifier
        self.training_data = training_data
        self.static_data = static_data or {}
        self.memory_manager = memory_manager

        # Pre-compile lists of known entities with multiple variations
        # Use safe defaults if static_data is missing or incomplete
        self.known_members = self._build_member_variations()
        self.known_albums = self._build_album_variations()
        self.known_songs = self._build_song_variations()

    def _build_member_variations(self):
        """Build comprehensive member name variations including nicknames and aliases."""
        members = []

        # Safely access bandInfo with fallback
        band_info = self.static_data.get("bandInfo", {})
        current_members = band_info.get("currentMembers", [])
        former_members = band_info.get("formerMembers", [])

        # Current members
        for member in current_members:
            name = member["name"].lower()
            variations = [
                name,
                name.replace("'", ""),
                name.replace(" ", ""),
                name.split()[0],
                name.split()[-1],
            ]

            # Add common nicknames and variations
            if "flea" in name or "balzary" in name:
                variations.extend(
                    ["flea", "michael flea", "michael balzary", "balzary", "mike flea"]
                )
            elif "anthony" in name or "kiedis" in name:
                variations.extend(["anthony", "kiedis", "tony", "anthony kiedis", "ak"])
            elif "john" in name or "frusciante" in name:
                variations.extend(
                    ["john", "frusciante", "johnny", "john frusciante", "jf"]
                )
            elif "chad" in name or "smith" in name:
                variations.extend(["chad", "smith", "chad smith", "chadwick"])

            members.append(
                {
                    "name": name,
                    "variations": variations,
                    "details": member,
                    "type": "current",
                }
            )

        # Former members
        for member in former_members:
            name = member["name"].lower()
            variations = [
                name,
                name.replace("'", ""),
                name.replace(" ", ""),
                name.split()[0],
                name.split()[-1],
            ]

            # Add common nicknames for former members
            if "hillel" in name or "slovak" in name:
                variations.extend(["hillel", "slovak", "hillel slovak"])
            elif "jack" in name or "irons" in name:
                variations.extend(["jack", "irons", "jack irons"])
            elif "josh" in name or "klinghoffer" in name:
                variations.extend(["josh", "klinghoffer", "josh klinghoffer", "jk"])
            elif "dave" in name or "navarro" in name:
                variations.extend(["dave", "navarro", "dave navarro", "dn"])

            members.append(
                {
                    "name": name,
                    "variations": variations,
                    "details": member,
                    "type": "former",
                }
            )

        return members

    def validate_static_data(self):
        """Validate that static data is properly loaded and accessible."""
        issues = []

        if not self.static_data:
            issues.append("No static data provided")
            return issues

        band_info = self.static_data.get("bandInfo")
        if not band_info:
            issues.append("bandInfo not found in static data")
        else:
            if not band_info.get("currentMembers"):
                issues.append("No current members found in bandInfo")
            if not band_info.get("formerMembers"):
                issues.append("No former members found in bandInfo")

        discography = self.static_data.get("discography")
        if not discography:
            issues.append("discography not found in static data")
        else:
            for album_type in ["studioAlbums", "compilationAlbums", "liveAlbums"]:
                if not discography.get(album_type):
                    issues.append(f"No {album_type} found in discography")

        return issues

    def _build_album_variations(self):
        """Build comprehensive album name variations."""
        albums = []

        # Safely access discography with fallback
        discography = self.static_data.get("discography", {})

        for album_type in ["studioAlbums", "compilationAlbums", "liveAlbums"]:
            album_list = discography.get(album_type, [])
            for album in album_list:
                name = album["name"].lower()
                variations = [
                    name,
                    name.replace("'", ""),
                    name.replace(" ", ""),
                    name.replace("&", "and"),
                ]

                # Add common abbreviations and alternative names
                if "blood sugar sex magik" in name:
                    variations.extend(["blood sugar", "bssm", "blood sugar sex magic"])
                elif "californication" in name:
                    variations.extend(["cali", "californication"])
                elif "by the way" in name:
                    variations.extend(["btw", "by the way"])
                elif "stadium arcadium" in name:
                    variations.extend(["stadium", "arcadium", "sa"])
                elif "unlimited love" in name:
                    variations.extend(["unlimited", "ul"])
                elif "the getaway" in name:
                    variations.extend(["getaway", "tg"])
                elif "i'm with you" in name:
                    variations.extend(["im with you", "iwy"])
                elif "one hot minute" in name:
                    variations.extend(["ohm", "one hot minute"])
                elif "mother's milk" in name:
                    variations.extend(["mothers milk", "mother milk", "mm"])
                elif "uplift mofo party plan" in name:
                    variations.extend(["uplift", "mofo", "umpp"])
                elif "freaky styley" in name:
                    variations.extend(["freaky", "styley", "fs"])
                elif "the red hot chili peppers" in name:
                    variations.extend(["debut", "first album", "rhcp debut"])

                albums.append(
                    {
                        "name": name,
                        "variations": variations,
                        "details": album,
                        "type": album_type,
                    }
                )

        return albums

    def _build_song_variations(self):
        """Build comprehensive song name variations."""
        songs = []

        # Safely access discography with fallback
        discography = self.static_data.get("discography", {})

        for album_type in ["studioAlbums", "compilationAlbums", "liveAlbums"]:
            album_list = discography.get(album_type, [])
            for album in album_list:
                if "tracks" in album and isinstance(album["tracks"], list):
                    for track in album["tracks"]:
                        name = track.lower()
                        variations = [
                            name,
                            name.replace("'", ""),
                            name.replace(" ", ""),
                            name.replace("&", "and"),
                        ]

                        # Add common abbreviations and alternative names for popular songs
                        if "under the bridge" in name:
                            variations.extend(["utb", "under bridge"])
                        elif "californication" in name:
                            variations.extend(["cali"])
                        elif "scar tissue" in name:
                            variations.extend(["scar"])
                        elif "otherside" in name:
                            variations.extend(["other side"])
                        elif "by the way" in name:
                            variations.extend(["btw"])
                        elif "dani california" in name:
                            variations.extend(["dani", "dani cali"])
                        elif "snow (hey oh)" in name:
                            variations.extend(["snow", "hey oh", "snow hey oh"])
                        elif "give it away" in name:
                            variations.extend(["give away", "gia"])
                        elif "breaking the girl" in name:
                            variations.extend(["breaking girl", "btg"])
                        elif "suck my kiss" in name:
                            variations.extend(["smk"])
                        elif "around the world" in name:
                            variations.extend(["atw"])
                        elif "parallel universe" in name:
                            variations.extend(["parallel", "pu"])
                        elif "get on top" in name:
                            variations.extend(["got"])
                        elif "easily" in name:
                            variations.extend(["easy"])
                        elif "porcelain" in name:
                            variations.extend(["porc"])
                        elif "emit remmus" in name:
                            variations.extend(["emit", "remmus"])
                        elif "i like dirt" in name:
                            variations.extend(["dirt"])
                        elif "this velvet glove" in name:
                            variations.extend(["velvet glove", "tvg"])
                        elif "savior" in name:
                            variations.extend(["save"])
                        elif "purple stain" in name:
                            variations.extend(["purple", "stain"])
                        elif "right on time" in name:
                            variations.extend(["rot"])
                        elif "road trippin" in name:
                            variations.extend(["road trip", "rt"])
                        elif "black summer" in name:
                            variations.extend(["black", "summer", "bs"])
                        elif "here ever after" in name:
                            variations.extend(["here after", "hea"])
                        elif "aquatic mouth dance" in name:
                            variations.extend(["aquatic", "mouth dance", "amd"])
                        elif "not the one" in name:
                            variations.extend(["nto"])
                        elif "poster child" in name:
                            variations.extend(["poster", "child", "pc"])
                        elif "the great apes" in name:
                            variations.extend(["great apes", "tga"])
                        elif "it's only natural" in name:
                            variations.extend(["its only natural", "ion", "natural"])
                        elif "she's a lover" in name:
                            variations.extend(["shes a lover", "sal", "lover"])
                        elif "these are the ways" in name:
                            variations.extend(["these ways", "tatw", "ways"])
                        elif "whatchu thinkin" in name:
                            variations.extend(["whatchu", "thinkin", "wt"])
                        elif "bastards of light" in name:
                            variations.extend(["bastards", "light", "bol"])
                        elif "white braids & pillow chair" in name:
                            variations.extend(
                                [
                                    "white braids",
                                    "pillow chair",
                                    "wbp",
                                    "braids",
                                    "pillow",
                                ]
                            )

                        songs.append(
                            {
                                "name": name,
                                "variations": variations,
                                "album": album["name"],
                                "album_details": album,
                            }
                        )

        return songs

    def _find_entities_in_text(self, text):
        """Enhanced entity recognition with fuzzy matching and context awareness."""
        entities = []

        # Find members
        for member_info in self.known_members:
            for variation in member_info["variations"]:
                if variation in text:
                    # Check if it's not part of a larger word
                    pattern = r"\b" + re.escape(variation) + r"\b"
                    if re.search(pattern, text):
                        entities.append(
                            {
                                "type": "member",
                                "value": member_info["details"],
                                "matched_text": variation,
                                "member_type": member_info["type"],
                            }
                        )
                        break  # Found this member, move to next

        # Find albums
        for album_info in self.known_albums:
            for variation in album_info["variations"]:
                if variation in text:
                    pattern = r"\b" + re.escape(variation) + r"\b"
                    if re.search(pattern, text):
                        entities.append(
                            {
                                "type": "album",
                                "value": album_info["details"],
                                "matched_text": variation,
                                "album_type": album_info["type"],
                            }
                        )
                        break

        # Find songs
        for song_info in self.known_songs:
            for variation in song_info["variations"]:
                if variation in text:
                    pattern = r"\b" + re.escape(variation) + r"\b"
                    if re.search(pattern, text):
                        entities.append(
                            {
                                "type": "song",
                                "value": {
                                    "name": song_info["name"],
                                    "album": song_info["album"],
                                    "album_details": song_info["album_details"],
                                },
                                "matched_text": variation,
                            }
                        )
                        break

        return entities

    def _enhance_message_with_context(
        self, message: str, session_id: str | None = None
    ) -> str:
        """Enhance message with context from memory for better understanding."""
        if not self.memory_manager or not session_id:
            return message

        # Get follow-up context
        context = self.memory_manager.get_follow_up_context(session_id)
        if not context:
            return message

        enhanced_message = message

        # Resolve pronouns and ellipses
        if "in what year" in message.lower() or "when was" in message.lower():
            if context.get("last_album"):
                enhanced_message = f"what year was {context['last_album']} released"
            elif context.get("last_song"):
                enhanced_message = f"what year was {context['last_song']} released"

        if "who wrote" in message.lower() and not any(
            entity in message.lower() for entity in ["album", "song", "track"]
        ):
            if context.get("last_song"):
                enhanced_message = f"who wrote {context['last_song']}"
            elif context.get("last_album"):
                enhanced_message = f"who wrote songs on {context['last_album']}"

        if "tell me more about" in message.lower() or "what about" in message.lower():
            if context.get("last_member"):
                enhanced_message = f"tell me about {context['last_member']}"
            elif context.get("last_album"):
                enhanced_message = f"tell me about {context['last_album']}"
            elif context.get("last_song"):
                enhanced_message = f"tell me about {context['last_song']}"

        return enhanced_message

    def _is_follow_up_question(self, message: str) -> bool:
        """Detect if this is a follow-up question."""
        follow_up_indicators = [
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
        return any(indicator in message.lower() for indicator in follow_up_indicators)

    def _detect_ambiguity(self, entities: list[dict]) -> dict | None:
        """Detect ambiguous entities that could be both songs and albums."""
        ambiguous_entities = []

        for entity in entities:
            if entity["type"] in ["song", "album"]:
                entity_name = entity["value"]["name"].lower()

                # Check if this name exists in both songs and albums
                is_song = any(
                    song["name"].lower() == entity_name for song in self.known_songs
                )
                is_album = any(
                    album["name"].lower() == entity_name for album in self.known_albums
                )

                if is_song and is_album:
                    ambiguous_entities.append(
                        {
                            "name": entity["value"]["name"],
                            "type": entity["type"],
                            "original_type": entity["type"],
                        }
                    )

        if ambiguous_entities:
            return {"ambiguous": True, "entities": ambiguous_entities}

        return None

    def _generate_contextual_response(
        self,
        message: str,
        intent: str,
        entities: list[dict],
        session_id: str | None = None,
    ) -> str:
        """Generate contextual response based on intent, entities, and conversation history."""

        # Check for ambiguity first
        ambiguity = self._detect_ambiguity(entities)
        if ambiguity:
            entity_name = ambiguity["entities"][0]["name"]
            return f"Do you mean the song or the album '{entity_name}'?"

        # Handle follow-up questions
        if self._is_follow_up_question(message) and self.memory_manager and session_id:
            context = self.memory_manager.get_follow_up_context(session_id)
            history = self.memory_manager.get_conversation_history(session_id, 3)

            if history:
                return self._handle_follow_up_question(
                    message, intent, entities, context, history
                )

        # Generate basic response
        return self._generate_basic_response(intent, entities)

    def _handle_follow_up_question(
        self,
        message: str,
        intent: str,
        entities: list[dict],
        context: dict,
        history: list[dict],
    ) -> str:
        """Handle follow-up questions using context from conversation history."""

        message_lower = message.lower()

        # Handle "in what year" questions
        if "in what year" in message_lower or "when was" in message_lower:
            if context.get("last_album"):
                # Find album release year
                for album in self.known_albums:
                    if album["name"].lower() == context["last_album"].lower():
                        album_data = album.get("details", {})
                        release_date = album_data.get("releaseDate", "")
                        if release_date:
                            year = (
                                release_date.split("-")[0]
                                if "-" in release_date
                                else release_date
                            )
                            return f"{context['last_album']} was released in {year}."
                return f"I don't have the release year for {context['last_album']}."

            elif context.get("last_song"):
                # Find song release year (from album)
                for song in self.known_songs:
                    if song["name"].lower() == context["last_song"].lower():
                        album_name = song.get("album", "")
                        if album_name:
                            for album in self.known_albums:
                                if album["name"].lower() == album_name.lower():
                                    album_data = album.get("details", {})
                                    release_date = album_data.get("releaseDate", "")
                                    if release_date:
                                        year = (
                                            release_date.split("-")[0]
                                            if "-" in release_date
                                            else release_date
                                        )
                                        return f"{context['last_song']} was released in {year} on the album {album_name}."
                return f"I don't have the release year for {context['last_song']}."

        # Handle "who wrote" questions
        if "who wrote" in message_lower:
            if context.get("last_song"):
                # Find song writers
                for song in self.known_songs:
                    if song["name"].lower() == context["last_song"].lower():
                        song_data = song.get("details", {})
                        writers = song_data.get("writers", [])
                        if writers:
                            return f"{context['last_song']} was written by {', '.join(writers)}."
                        else:
                            return f"I don't have writer information for {context['last_song']}."

        # Default to basic response if no specific follow-up handling
        return self._generate_basic_response(intent, entities)

    def _generate_basic_response(self, intent: str, entities: list[dict]) -> str:
        """Generate a basic response without context."""
        response_message = ""
        handled = False

        member_entity = next((e for e in entities if e["type"] == "member"), None)
        album_entity = next((e for e in entities if e["type"] == "album"), None)
        song_entity = next((e for e in entities if e["type"] == "song"), None)

        if intent == "unrecognized" or intent == "None":
            response_message = "I'm not sure I understood that. Could you try asking about the band members, albums, songs, or band history?"
            handled = True
        elif intent == "member.biography" and member_entity:
            member = member_entity["value"]
            name = member["name"]
            _role = member.get("role", "member")
            member_since = member.get("memberSince", "unknown year")

            # Enhanced biography response
            if name.lower() in ["anthony kiedis", "anthony", "kiedis"]:
                response_message = f"Anthony Kiedis is the lead vocalist and primary lyricist of RHCP. He's been with the band since {member_since} and is known for his unique vocal style and energetic stage presence. He's also written a memoir called 'Scar Tissue' about his life and struggles."
            elif name.lower() in ["flea", "michael flea", "michael balzary"]:
                response_message = f"Flea (Michael Balzary) is the bassist and co-founding member of RHCP. He's been with the band since {member_since} and is known for his distinctive funky bass lines, energetic performances, and his work as an actor. He's considered one of the most influential bassists in rock music."
            elif name.lower() in ["john frusciante", "john", "frusciante"]:
                response_message = "John Frusciante is the guitarist of RHCP. He first joined in 1988, left in 1992, returned in 1998, left again in 2009, and rejoined in 2019. He's known for his unique guitar style, melodic solos, and contributions to albums like 'Blood Sugar Sex Magik' and 'Californication'."
            elif name.lower() in ["chad smith", "chad", "smith"]:
                response_message = f"Chad Smith is the drummer of RHCP, joining in {member_since}. He's known for his powerful drumming style, technical proficiency, and his work with other bands like Chickenfoot. He's been a consistent member and has played on most of their albums."
            else:
                response_message = member.get(
                    "biography",
                    f"I know about {name}, but I don't have a detailed biography.",
                )
            handled = True
        elif intent == "album.specific" and album_entity:
            album = album_entity["value"]
            album_name = album["name"]
            release_date = album.get("releaseDate", "unknown date")
            producer = album.get("producer", "unknown producer")

            # Enhanced album response
            if album_name.lower() in ["blood sugar sex magik", "blood sugar"]:
                response_message = f"'{album_name}' was released on {release_date} and produced by {producer}. This album was a breakthrough for RHCP, featuring hits like 'Under the Bridge' and 'Give It Away'. It's considered one of their most influential albums and helped define the alternative rock sound of the 1990s."
            elif album_name.lower() in ["californication"]:
                response_message = f"'{album_name}' was released on {release_date} and produced by {producer}. This album marked a return to form for the band and includes hits like 'Scar Tissue', 'Otherside', and 'Californication'. It's one of their most successful albums commercially."
            elif album_name.lower() in ["by the way"]:
                response_message = f"'{album_name}' was released on {release_date} and produced by {producer}. This album shows a more melodic side of RHCP with hits like 'By the Way' and 'Can't Stop'. It's known for its more polished sound compared to their earlier work."
            elif album_name.lower() in ["stadium arcadium"]:
                response_message = f"'{album_name}' was released on {release_date} and produced by {producer}. This double album won the Grammy for Best Rock Album and includes hits like 'Dani California' and 'Snow (Hey Oh)'. It's one of their most ambitious projects."
            elif album_name.lower() in ["unlimited love"]:
                response_message = f"'{album_name}' was released on {release_date} and produced by {producer}. This is their latest album and marks the return of John Frusciante to the band. It includes the hit single 'Black Summer' and shows the band returning to their classic sound."
            else:
                album_info = f"'{album_name}' was released on {release_date} and produced by {producer}"
                if album.get("tracks"):
                    tracks_preview = ", ".join(album["tracks"][:5])
                    album_info += f". It includes tracks like {tracks_preview}{'...' if len(album['tracks']) > 5 else ''}."
                response_message = album_info
            handled = True
        elif intent in ("song.specific", "song.lyrics") and song_entity:
            song = song_entity["value"]
            song_name = song["name"]
            album_name = song["album"]

            # Enhanced song response
            if song_name.lower() in ["under the bridge"]:
                response_message = f"'{song_name}' is from the album '{album_name}'. It's one of RHCP's most iconic songs, written by Anthony Kiedis about his feelings of isolation in Los Angeles. The song features a beautiful melody and is considered one of their signature tracks."
            elif song_name.lower() in ["californication"]:
                response_message = f"'{song_name}' is from the album '{album_name}'. This song critiques the artificial nature of Hollywood and California culture. It features John Frusciante's distinctive guitar work and is one of their most recognizable songs."
            elif song_name.lower() in ["scar tissue"]:
                response_message = f"'{song_name}' is from the album '{album_name}'. This song deals with themes of addiction and recovery, reflecting Anthony Kiedis's personal struggles. It won a Grammy for Best Rock Song."
            elif song_name.lower() in ["otherside"]:
                response_message = f"'{song_name}' is from the album '{album_name}'. This song addresses the theme of drug addiction and the struggle to overcome it. It features a memorable bass line from Flea and emotional vocals from Kiedis."
            elif song_name.lower() in ["by the way"]:
                response_message = f"'{song_name}' is from the album '{album_name}'. This song shows a more melodic side of RHCP with its catchy chorus and harmonies. It was a major hit and helped define their sound in the 2000s."
            else:
                response_message = f"'{song_name}' is from the album '{album_name}'. It's a great track that showcases the band's unique style and musical chemistry."
            handled = True

        if not handled and intent not in ["unrecognized", "None"]:
            found_intent_data = None
            for corpus_name in ["base", "rhcp"]:
                corpus_data = self.training_data[corpus_name]["data"]
                found_intent_data = next(
                    (item for item in corpus_data if item["intent"] == intent), None
                )
                if found_intent_data and found_intent_data.get("answers"):
                    response_message = random.choice(found_intent_data["answers"])
                    break
            if not response_message:
                response_message = f"I understood your intent is '{intent}', but I don't have a specific response for that yet."

        if not response_message:
            response_message = "Sorry, I couldn't process your request. Try asking about band members, albums, songs, or band history!"

        return response_message

    def get_classifications(self, message):
        """
        Returns a list of classifications for a message, sorted by confidence.
        """
        # The classifier is a scikit-learn pipeline, so we predict probabilities.
        probabilities = self.classifier.predict_proba([message])[0]
        # Pair class labels with their probabilities
        class_probabilities = zip(self.classifier.classes_, probabilities, strict=False)
        # Sort by probability in descending order
        sorted_classifications = sorted(
            class_probabilities, key=lambda item: item[1], reverse=True
        )
        # Format to match the original structure
        return [
            {"label": label, "value": value} for label, value in sorted_classifications
        ]

    def process_message(
        self, message: str, session_id: str | None = None
    ) -> dict[str, Any]:
        # Enhance message with context if memory manager is available
        enhanced_message = self._enhance_message_with_context(message, session_id)

        clean_message = enhanced_message.lower()
        classifications = self.get_classifications(clean_message)

        intent = "unknown"
        confidence = 0.0

        if classifications:
            top_classification = classifications[0]
            confidence = top_classification["value"]

            # Confidence gating: only accept high-confidence predictions
            if confidence >= CONFIDENCE_THRESHOLD:
                intent = top_classification["label"]
            else:
                intent = "unknown"
        else:
            intent = "unknown"

        # --- Enhanced Entity Recognition ---
        entities = self._find_entities_in_text(clean_message)

        # --- Entity-based Intent Override ---
        # If we have entities but low confidence, override the intent based on entity types
        if entities and confidence < CONFIDENCE_THRESHOLD:
            entity_types = [e["type"] for e in entities]
            if "album" in entity_types:
                intent = "album.info"
                confidence = (
                    0.5  # Set a reasonable confidence for entity-based detection
                )
            elif "song" in entity_types:
                intent = "song.info"
                confidence = 0.5
            elif "member" in entity_types:
                intent = "member.biography"
                confidence = 0.5

        # --- Entity-based Intent Override (Enhanced) ---
        # Also override when we have entities but the intent doesn't match the entity types
        if entities:
            entity_types = [e["type"] for e in entities]
            intent_matches_entities = (
                ("album" in entity_types and intent in ["album.specific", "album.info"])
                or (
                    "song" in entity_types
                    and intent in ["song.specific", "song.info", "song.lyrics"]
                )
                or (
                    "member" in entity_types
                    and intent in ["member.biography", "band.members"]
                )
            )

            if not intent_matches_entities:
                if "album" in entity_types:
                    intent = "album.info"
                    confidence = 0.5
                elif "song" in entity_types:
                    intent = "song.info"
                    confidence = 0.5
                elif "member" in entity_types:
                    intent = "member.biography"
                    confidence = 0.5

        # --- Contextual Response Generation ---
        response_message = self._generate_contextual_response(
            message, intent, entities, session_id
        )

        response = {
            "message": response_message,
            "intent": intent,
            "confidence": float(confidence),
            "entities": entities,
        }

        # Store in memory if available
        if self.memory_manager and session_id:
            self.memory_manager.add_message(session_id, message, response)

        return response
