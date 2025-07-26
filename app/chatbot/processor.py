import random
import re
from typing import Dict, List, Any, Optional

CONFIDENCE_THRESHOLD = 0.04  # Further lowered threshold for scikit-learn's probabilities

class ChatbotProcessor:
    def __init__(self, classifier, training_data, static_data, memory_manager=None):
        self.classifier = classifier
        self.training_data = training_data
        self.static_data = static_data
        self.memory_manager = memory_manager

        # Pre-compile lists of known entities with multiple variations
        self.known_members = self._build_member_variations()
        self.known_albums = self._build_album_variations()
        self.known_songs = self._build_song_variations()

    def _build_member_variations(self):
        """Build comprehensive member name variations including nicknames and aliases."""
        members = []
        
        # Current members
        for member in self.static_data['bandInfo']['currentMembers']:
            name = member['name'].lower()
            variations = [name, name.replace("'", ""), name.replace(" ", ""), name.split()[0], name.split()[-1]]
            
            # Add common nicknames
            if "flea" in name or "balzary" in name:
                variations.extend(["flea", "michael flea", "michael balzary"])
            elif "anthony" in name or "kiedis" in name:
                variations.extend(["anthony", "kiedis", "tony"])
            elif "john" in name or "frusciante" in name:
                variations.extend(["john", "frusciante", "johnny"])
            elif "chad" in name or "smith" in name:
                variations.extend(["chad", "smith"])
            
            members.append({
                'name': name,
                'variations': variations,
                'details': member,
                'type': 'current'
            })
        
        # Former members
        for member in self.static_data['bandInfo']['formerMembers']:
            name = member['name'].lower()
            variations = [name, name.replace("'", ""), name.replace(" ", ""), name.split()[0], name.split()[-1]]
            
            # Add common nicknames for former members
            if "hillel" in name or "slovak" in name:
                variations.extend(["hillel", "slovak"])
            elif "jack" in name or "irons" in name:
                variations.extend(["jack", "irons"])
            elif "josh" in name or "klinghoffer" in name:
                variations.extend(["josh", "klinghoffer"])
            
            members.append({
                'name': name,
                'variations': variations,
                'details': member,
                'type': 'former'
            })
        
        return members

    def _build_album_variations(self):
        """Build comprehensive album name variations."""
        albums = []
        
        for album_type in ['studioAlbums', 'compilationAlbums', 'liveAlbums']:
            for album in self.static_data['discography'][album_type]:
                name = album['name'].lower()
                albums.append({
                    'name': name,
                    'variations': [name, name.replace("'", ""), name.replace(" ", ""), name.replace("&", "and")],
                    'details': album,
                    'type': album_type
                })
        
        return albums

    def _build_song_variations(self):
        """Build comprehensive song name variations."""
        songs = []
        
        for album_type in ['studioAlbums', 'compilationAlbums', 'liveAlbums']:
            for album in self.static_data['discography'][album_type]:
                if 'tracks' in album and isinstance(album['tracks'], list):
                    for track in album['tracks']:
                        name = track.lower()
                        songs.append({
                            'name': name,
                            'variations': [name, name.replace("'", ""), name.replace(" ", ""), name.replace("&", "and")],
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
        
        # If user is asking about members after discussing albums
        if intent == 'band.members' and 'album' in conversation_flow[-2:]:
            return "Speaking of the band members, the current lineup includes Anthony Kiedis (vocals), Flea (bass), John Frusciante (guitar), and Chad Smith (drums)."
        
        # If user is asking about albums after discussing members
        if intent == 'album.info' and 'member' in conversation_flow[-2:]:
            return "The band has released many albums over the years. Some of their most popular include 'Blood Sugar Sex Magik', 'Californication', and 'Stadium Arcadium'."
        
        return self._generate_basic_response(intent, entities)

    def _generate_basic_response(self, intent: str, entities: List[Dict]) -> str:
        """Generate a basic response without context."""
        response_message = ""
        handled = False
        
        member_entity = next((e for e in entities if e['type'] == 'member'), None)
        album_entity = next((e for e in entities if e['type'] == 'album'), None)
        song_entity = next((e for e in entities if e['type'] == 'song'), None)

        if intent == 'unrecognized' or intent == 'None':
            response_message = "Sorry, I didn't understand that."
            handled = True
        elif intent == 'member.biography' and member_entity:
            member = member_entity['value']
            response_message = member.get('biography', f"I know about {member['name']}, but I don't have a detailed biography.")
            handled = True
        elif intent == 'album.specific' and album_entity:
            album = album_entity['value']
            album_info = f"{album['name']} was released on {album['releaseDate']}"
            if album.get('producer'):
                album_info += f" and produced by {album['producer']}"
            if album.get('tracks'):
                tracks_preview = ', '.join(album['tracks'][:5])
                album_info += f". It includes tracks like {tracks_preview}{'...' if len(album['tracks']) > 5 else ''}."
            response_message = album_info
            handled = True
        elif intent in ('album.specific', 'song.specific') and song_entity:
            song = song_entity['value']
            response_message = f"{song['name'].title()} is from the album {song['album']}."
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
            response_message = "Sorry, I couldn't process your request."

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