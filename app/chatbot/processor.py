import random
import re
from typing import Dict, List, Any, Optional

CONFIDENCE_THRESHOLD = 0.04  # Further lowered threshold for scikit-learn's probabilities

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
        band_info = self.static_data.get('bandInfo', {})
        current_members = band_info.get('currentMembers', [])
        former_members = band_info.get('formerMembers', [])
        
        # Current members
        for member in current_members:
            name = member['name'].lower()
            variations = [name, name.replace("'", ""), name.replace(" ", ""), name.split()[0], name.split()[-1]]
            
            # Add common nicknames and variations
            if "flea" in name or "balzary" in name:
                variations.extend(["flea", "michael flea", "michael balzary", "balzary", "mike flea"])
            elif "anthony" in name or "kiedis" in name:
                variations.extend(["anthony", "kiedis", "tony", "anthony kiedis", "ak"])
            elif "john" in name or "frusciante" in name:
                variations.extend(["john", "frusciante", "johnny", "john frusciante", "jf"])
            elif "chad" in name or "smith" in name:
                variations.extend(["chad", "smith", "chad smith", "chadwick"])
            
            members.append({
                'name': name,
                'variations': variations,
                'details': member,
                'type': 'current'
            })
        
        # Former members
        for member in former_members:
            name = member['name'].lower()
            variations = [name, name.replace("'", ""), name.replace(" ", ""), name.split()[0], name.split()[-1]]
            
            # Add common nicknames for former members
            if "hillel" in name or "slovak" in name:
                variations.extend(["hillel", "slovak", "hillel slovak"])
            elif "jack" in name or "irons" in name:
                variations.extend(["jack", "irons", "jack irons"])
            elif "josh" in name or "klinghoffer" in name:
                variations.extend(["josh", "klinghoffer", "josh klinghoffer", "jk"])
            elif "dave" in name or "navarro" in name:
                variations.extend(["dave", "navarro", "dave navarro", "dn"])
            
            members.append({
                'name': name,
                'variations': variations,
                'details': member,
                'type': 'former'
            })
        
        return members

    def validate_static_data(self):
        """Validate that static data is properly loaded and accessible."""
        issues = []
        
        if not self.static_data:
            issues.append("No static data provided")
            return issues
        
        band_info = self.static_data.get('bandInfo')
        if not band_info:
            issues.append("bandInfo not found in static data")
        else:
            if not band_info.get('currentMembers'):
                issues.append("No current members found in bandInfo")
            if not band_info.get('formerMembers'):
                issues.append("No former members found in bandInfo")
        
        discography = self.static_data.get('discography')
        if not discography:
            issues.append("discography not found in static data")
        else:
            for album_type in ['studioAlbums', 'compilationAlbums', 'liveAlbums']:
                if not discography.get(album_type):
                    issues.append(f"No {album_type} found in discography")
        
        return issues

    def _build_album_variations(self):
        """Build comprehensive album name variations."""
        albums = []
        
        # Safely access discography with fallback
        discography = self.static_data.get('discography', {})
        
        for album_type in ['studioAlbums', 'compilationAlbums', 'liveAlbums']:
            album_list = discography.get(album_type, [])
            for album in album_list:
                name = album['name'].lower()
                variations = [name, name.replace("'", ""), name.replace(" ", ""), name.replace("&", "and")]
                
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
                
                albums.append({
                    'name': name,
                    'variations': variations,
                    'details': album,
                    'type': album_type
                })
        
        return albums

    def _build_song_variations(self):
        """Build comprehensive song name variations."""
        songs = []
        
        # Safely access discography with fallback
        discography = self.static_data.get('discography', {})
        
        for album_type in ['studioAlbums', 'compilationAlbums', 'liveAlbums']:
            album_list = discography.get(album_type, [])
            for album in album_list:
                if 'tracks' in album and isinstance(album['tracks'], list):
                    for track in album['tracks']:
                        name = track.lower()
                        variations = [name, name.replace("'", ""), name.replace(" ", ""), name.replace("&", "and")]
                        
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
                            variations.extend(["white braids", "pillow chair", "wbp", "braids", "pillow"])
                        
                        songs.append({
                            'name': name,
                            'variations': variations,
                            'album': album['name'],
                            'album_details': album
                        })
        
        return songs

    def _find_entities_in_text(self, text):
        """Enhanced entity recognition with fuzzy matching and context awareness."""
        entities = []
        
        # Find members
        for member_info in self.known_members:
            for variation in member_info['variations']:
                if variation in text:
                    # Check if it's not part of a larger word
                    pattern = r'\b' + re.escape(variation) + r'\b'
                    if re.search(pattern, text):
                        entities.append({
                            'type': 'member',
                            'value': member_info['details'],
                            'matched_text': variation,
                            'member_type': member_info['type']
                        })
                        break  # Found this member, move to next
        
        # Find albums
        for album_info in self.known_albums:
            for variation in album_info['variations']:
                if variation in text:
                    pattern = r'\b' + re.escape(variation) + r'\b'
                    if re.search(pattern, text):
                        entities.append({
                            'type': 'album',
                            'value': album_info['details'],
                            'matched_text': variation,
                            'album_type': album_info['type']
                        })
                        break
        
        # Find songs
        for song_info in self.known_songs:
            for variation in song_info['variations']:
                if variation in text:
                    pattern = r'\b' + re.escape(variation) + r'\b'
                    if re.search(pattern, text):
                        entities.append({
                            'type': 'song',
                            'value': {
                                'name': song_info['name'],
                                'album': song_info['album'],
                                'album_details': song_info['album_details']
                            },
                            'matched_text': variation
                        })
                        break
        
        return entities

    def _enhance_message_with_context(self, message: str, session_id: Optional[str] = None) -> str:
        """Enhance the message with context from conversation history."""
        if not self.memory_manager or not session_id:
            return message
        
        context = self.memory_manager.get_context(session_id)
        history = self.memory_manager.get_conversation_history(session_id, max_messages=3)
        
        # Add context keywords to help with intent classification
        context_keywords = []
        
        # Add mentioned entities as context
        if context.get('mentioned_members'):
            context_keywords.extend(context['mentioned_members'])
        if context.get('mentioned_albums'):
            context_keywords.extend(context['mentioned_albums'])
        if context.get('mentioned_songs'):
            context_keywords.extend(context['mentioned_songs'])
        
        # Add conversation flow context
        if context.get('conversation_flow'):
            recent_intents = context['conversation_flow'][-2:]  # Last 2 intents
            for intent in recent_intents:
                if 'member' in intent:
                    context_keywords.append('member')
                elif 'album' in intent:
                    context_keywords.append('album')
                elif 'song' in intent:
                    context_keywords.append('song')
                elif 'band' in intent:
                    context_keywords.append('band')
        
        # Enhance message with context if it's a follow-up question
        if context_keywords and self._is_follow_up_question(message):
            enhanced_message = f"{message} {' '.join(context_keywords)}"
            return enhanced_message
        
        return message

    def _is_follow_up_question(self, message: str) -> bool:
        """Detect if this is a follow-up question that needs context."""
        follow_up_indicators = [
            'what about', 'how about', 'tell me more', 'and', 'also', 'too',
            'what else', 'anything else', 'more', 'other', 'different'
        ]
        
        message_lower = message.lower()
        return any(indicator in message_lower for indicator in follow_up_indicators)

    def _generate_contextual_response(self, message: str, intent: str, entities: List[Dict], 
                                    session_id: Optional[str] = None) -> str:
        """Generate a response that takes conversation context into account."""
        if not self.memory_manager or not session_id:
            return self._generate_basic_response(intent, entities)
        
        context = self.memory_manager.get_context(session_id)
        history = self.memory_manager.get_conversation_history(session_id, max_messages=2)
        
        # Handle follow-up questions about previously mentioned entities
        if self._is_follow_up_question(message):
            return self._handle_follow_up_question(message, intent, entities, context, history)
        
        # Handle contextual responses based on conversation flow
        if context.get('conversation_flow'):
            return self._handle_conversation_flow(message, intent, entities, context, history)
        
        return self._generate_basic_response(intent, entities)

    def _handle_follow_up_question(self, message: str, intent: str, entities: List[Dict], 
                                 context: Dict, history: List[Dict]) -> str:
        """Handle follow-up questions by using context from previous messages."""
        # If no entities in current message but we have context, use previous entities
        if not entities and context.get('mentioned_members'):
            # User is asking about a previously mentioned member
            if 'member' in intent or 'biography' in intent:
                member_name = context['mentioned_members'][-1]  # Most recently mentioned
                member_details = next((m for m in self.known_members if m['name'] == member_name.lower()), None)
                if member_details:
                    return member_details['details'].get('biography', f"I know about {member_name}, but I don't have a detailed biography.")
        
        if not entities and context.get('mentioned_albums'):
            # User is asking about a previously mentioned album
            if 'album' in intent:
                album_name = context['mentioned_albums'][-1]
                album_details = next((a for a in self.known_albums if a['name'] == album_name.lower()), None)
                if album_details:
                    album = album_details['details']
                    return f"{album['name']} was released on {album['releaseDate']} and produced by {album.get('producer', 'unknown')}."
        
        return self._generate_basic_response(intent, entities)

    def _handle_conversation_flow(self, message: str, intent: str, entities: List[Dict], 
                                context: Dict, history: List[Dict]) -> str:
        """Handle responses based on conversation flow patterns."""
        conversation_flow = context.get('conversation_flow', [])
        patterns = context.get('patterns', {})
        current_topic = context.get('current_topic')
        
        # If user is asking about members after discussing albums
        if intent == 'band.members' and current_topic == 'albums':
            return "Speaking of the band members, the current lineup includes Anthony Kiedis (vocals), Flea (bass), John Frusciante (guitar), and Chad Smith (drums). Each member brings their unique style to create RHCP's signature sound."
        
        # If user is asking about albums after discussing members
        if intent == 'album.info' and current_topic == 'band_members':
            return "The band has released many albums over the years. Some of their most popular include 'Blood Sugar Sex Magik', 'Californication', 'By the Way', and 'Stadium Arcadium'. Each album showcases the band's evolution and different musical phases."
        
        # If user is asking about songs after discussing albums
        if intent == 'song.info' and current_topic == 'albums':
            return "RHCP has many iconic songs across their albums. Some of their biggest hits include 'Under the Bridge', 'Californication', 'Scar Tissue', 'Otherside', and 'By the Way'. Each song has its own unique story and musical style."
        
        # Handle follow-up questions based on conversation patterns
        if patterns.get('follow_up_questions', 0) > 0:
            if current_topic == 'band_members':
                return "Is there a specific member you'd like to know more about? I can tell you about their musical contributions, background, or role in the band."
            elif current_topic == 'albums':
                return "Would you like to know more about a specific album? I can tell you about the recording process, key tracks, or the album's significance in their career."
            elif current_topic == 'songs':
                return "Is there a particular song you're interested in? I can share details about its meaning, creation, or the album it's from."
        
        # Handle repeated questions about the same topic
        if patterns.get('member_questions', 0) > 2:
            return "I notice you're interested in the band members! Have you heard about their individual solo projects or collaborations outside of RHCP?"
        elif patterns.get('album_questions', 0) > 2:
            return "You seem to be exploring their discography! Would you like to know about their musical evolution over the years or their recording process?"
        elif patterns.get('song_questions', 0) > 2:
            return "You're really diving into their songs! Have you explored their live performances or acoustic versions of these tracks?"
        
        # Handle general conversation flow
        if len(conversation_flow) > 3:
            recent_intents = [flow['intent'] for flow in conversation_flow[-3:]]
            if all(intent in ['member.biography', 'band.members'] for intent in recent_intents):
                return "You're really getting to know the band members! Have you thought about how their individual styles come together to create RHCP's unique sound?"
            elif all(intent in ['album.specific', 'album.info'] for intent in recent_intents):
                return "You're exploring their discography thoroughly! Each album represents a different phase in their musical journey. Would you like to know about their creative process?"
        
        return self._generate_basic_response(intent, entities)

    def _generate_basic_response(self, intent: str, entities: List[Dict]) -> str:
        """Generate a basic response without context."""
        response_message = ""
        handled = False
        
        member_entity = next((e for e in entities if e['type'] == 'member'), None)
        album_entity = next((e for e in entities if e['type'] == 'album'), None)
        song_entity = next((e for e in entities if e['type'] == 'song'), None)

        if intent == 'unrecognized' or intent == 'None':
            response_message = "I'm not sure I understood that. Could you try asking about the band members, albums, songs, or band history?"
            handled = True
        elif intent == 'member.biography' and member_entity:
            member = member_entity['value']
            name = member['name']
            role = member.get('role', 'member')
            member_since = member.get('memberSince', 'unknown year')
            
            # Enhanced biography response
            if name.lower() in ['anthony kiedis', 'anthony', 'kiedis']:
                response_message = f"Anthony Kiedis is the lead vocalist and primary lyricist of RHCP. He's been with the band since {member_since} and is known for his unique vocal style and energetic stage presence. He's also written a memoir called 'Scar Tissue' about his life and struggles."
            elif name.lower() in ['flea', 'michael flea', 'michael balzary']:
                response_message = f"Flea (Michael Balzary) is the bassist and co-founding member of RHCP. He's been with the band since {member_since} and is known for his distinctive funky bass lines, energetic performances, and his work as an actor. He's considered one of the most influential bassists in rock music."
            elif name.lower() in ['john frusciante', 'john', 'frusciante']:
                response_message = f"John Frusciante is the guitarist of RHCP. He first joined in 1988, left in 1992, returned in 1998, left again in 2009, and rejoined in 2019. He's known for his unique guitar style, melodic solos, and contributions to albums like 'Blood Sugar Sex Magik' and 'Californication'."
            elif name.lower() in ['chad smith', 'chad', 'smith']:
                response_message = f"Chad Smith is the drummer of RHCP, joining in {member_since}. He's known for his powerful drumming style, technical proficiency, and his work with other bands like Chickenfoot. He's been a consistent member and has played on most of their albums."
            else:
                response_message = member.get('biography', f"I know about {name}, but I don't have a detailed biography.")
            handled = True
        elif intent == 'album.specific' and album_entity:
            album = album_entity['value']
            album_name = album['name']
            release_date = album.get('releaseDate', 'unknown date')
            producer = album.get('producer', 'unknown producer')
            
            # Enhanced album response
            if album_name.lower() in ['blood sugar sex magik', 'blood sugar']:
                response_message = f"'{album_name}' was released on {release_date} and produced by {producer}. This album was a breakthrough for RHCP, featuring hits like 'Under the Bridge' and 'Give It Away'. It's considered one of their most influential albums and helped define the alternative rock sound of the 1990s."
            elif album_name.lower() in ['californication']:
                response_message = f"'{album_name}' was released on {release_date} and produced by {producer}. This album marked a return to form for the band and includes hits like 'Scar Tissue', 'Otherside', and 'Californication'. It's one of their most successful albums commercially."
            elif album_name.lower() in ['by the way']:
                response_message = f"'{album_name}' was released on {release_date} and produced by {producer}. This album shows a more melodic side of RHCP with hits like 'By the Way' and 'Can't Stop'. It's known for its more polished sound compared to their earlier work."
            elif album_name.lower() in ['stadium arcadium']:
                response_message = f"'{album_name}' was released on {release_date} and produced by {producer}. This double album won the Grammy for Best Rock Album and includes hits like 'Dani California' and 'Snow (Hey Oh)'. It's one of their most ambitious projects."
            elif album_name.lower() in ['unlimited love']:
                response_message = f"'{album_name}' was released on {release_date} and produced by {producer}. This is their latest album and marks the return of John Frusciante to the band. It includes the hit single 'Black Summer' and shows the band returning to their classic sound."
            else:
                album_info = f"'{album_name}' was released on {release_date} and produced by {producer}"
                if album.get('tracks'):
                    tracks_preview = ', '.join(album['tracks'][:5])
                    album_info += f". It includes tracks like {tracks_preview}{'...' if len(album['tracks']) > 5 else ''}."
                response_message = album_info
            handled = True
        elif intent in ('song.specific', 'song.lyrics') and song_entity:
            song = song_entity['value']
            song_name = song['name']
            album_name = song['album']
            
            # Enhanced song response
            if song_name.lower() in ['under the bridge']:
                response_message = f"'{song_name}' is from the album '{album_name}'. It's one of RHCP's most iconic songs, written by Anthony Kiedis about his feelings of isolation in Los Angeles. The song features a beautiful melody and is considered one of their signature tracks."
            elif song_name.lower() in ['californication']:
                response_message = f"'{song_name}' is from the album '{album_name}'. This song critiques the artificial nature of Hollywood and California culture. It features John Frusciante's distinctive guitar work and is one of their most recognizable songs."
            elif song_name.lower() in ['scar tissue']:
                response_message = f"'{song_name}' is from the album '{album_name}'. This song deals with themes of addiction and recovery, reflecting Anthony Kiedis's personal struggles. It won a Grammy for Best Rock Song."
            elif song_name.lower() in ['otherside']:
                response_message = f"'{song_name}' is from the album '{album_name}'. This song addresses the theme of drug addiction and the struggle to overcome it. It features a memorable bass line from Flea and emotional vocals from Kiedis."
            elif song_name.lower() in ['by the way']:
                response_message = f"'{song_name}' is from the album '{album_name}'. This song shows a more melodic side of RHCP with its catchy chorus and harmonies. It was a major hit and helped define their sound in the 2000s."
            else:
                response_message = f"'{song_name}' is from the album '{album_name}'. It's a great track that showcases the band's unique style and musical chemistry."
            handled = True

        if not handled and intent not in ['unrecognized', 'None']:
            found_intent_data = None
            for corpus_name in ['base', 'rhcp']:
                corpus_data = self.training_data[corpus_name]['data']
                found_intent_data = next((item for item in corpus_data if item['intent'] == intent), None)
                if found_intent_data and found_intent_data.get('answers'):
                    response_message = random.choice(found_intent_data['answers'])
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
        class_probabilities = zip(self.classifier.classes_, probabilities)
        # Sort by probability in descending order
        sorted_classifications = sorted(class_probabilities, key=lambda item: item[1], reverse=True)
        # Format to match the original structure
        return [{"label": label, "value": value} for label, value in sorted_classifications]

    def process_message(self, message: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        # Enhance message with context if memory manager is available
        enhanced_message = self._enhance_message_with_context(message, session_id)
        
        clean_message = enhanced_message.lower()
        classifications = self.get_classifications(clean_message)
        
        intent = 'None'
        confidence = 0.0

        if classifications:
            top_classification = classifications[0]
            if top_classification['value'] > CONFIDENCE_THRESHOLD:
                intent = top_classification['label']
                confidence = top_classification['value']
            else:
                intent = 'unrecognized'
        else:
            intent = 'unrecognized'

        # --- Enhanced Entity Recognition ---
        entities = self._find_entities_in_text(clean_message)

        # --- Entity-based Intent Override ---
        # If we have entities but low confidence, override the intent based on entity types
        if entities and confidence < CONFIDENCE_THRESHOLD:
            entity_types = [e['type'] for e in entities]
            if 'album' in entity_types:
                intent = 'album.specific'
                confidence = 0.5  # Set a reasonable confidence for entity-based detection
            elif 'song' in entity_types:
                intent = 'song.specific'
                confidence = 0.5
            elif 'member' in entity_types:
                intent = 'member.biography'
                confidence = 0.5
        
        # --- Entity-based Intent Override (Enhanced) ---
        # Also override when we have entities but the intent doesn't match the entity types
        if entities:
            entity_types = [e['type'] for e in entities]
            intent_matches_entities = (
                ('album' in entity_types and intent in ['album.specific', 'album.info']) or
                ('song' in entity_types and intent in ['song.specific', 'song.info', 'song.lyrics']) or
                ('member' in entity_types and intent in ['member.biography', 'band.members'])
            )
            
            if not intent_matches_entities:
                if 'album' in entity_types:
                    intent = 'album.specific'
                    confidence = 0.5
                elif 'song' in entity_types:
                    intent = 'song.specific'
                    confidence = 0.5
                elif 'member' in entity_types:
                    intent = 'member.biography'
                    confidence = 0.5

        # --- Contextual Response Generation ---
        response_message = self._generate_contextual_response(message, intent, entities, session_id)

        response = {
            "message": response_message,
            "intent": intent,
            "confidence": float(confidence),
            "entities": entities
        }

        # Store in memory if available
        if self.memory_manager and session_id:
            self.memory_manager.add_message(session_id, message, response)

        return response 