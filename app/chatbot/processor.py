import random
import re

CONFIDENCE_THRESHOLD = 0.04  # Further lowered threshold for scikit-learn's probabilities

class ChatbotProcessor:
    def __init__(self, classifier, training_data, static_data):
        self.classifier = classifier
        self.training_data = training_data
        self.static_data = static_data

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

    def process_message(self, message):
        clean_message = message.lower()
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

        # --- Response Generation ---
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

        return {
            "message": response_message,
            "intent": intent,
            "confidence": float(confidence),
            "entities": entities
        } 