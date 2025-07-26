import random

CONFIDENCE_THRESHOLD = 0.04  # Further lowered threshold for scikit-learn's probabilities

class ChatbotProcessor:
    def __init__(self, classifier, training_data, static_data):
        self.classifier = classifier
        self.training_data = training_data
        self.static_data = static_data

        # Pre-compile lists of known entities
        self.known_members = [
            member['name'].lower() for member in self.static_data['bandInfo']['currentMembers']
        ] + [
            member['name'].lower() for member in self.static_data['bandInfo']['formerMembers']
        ]
        
        self.known_albums = [
            album['name'].lower() for album in self.static_data['discography']['studioAlbums']
        ] + [
            album['name'].lower() for album in self.static_data['discography']['compilationAlbums']
        ] + [
            album['name'].lower() for album in self.static_data['discography']['liveAlbums']
        ]
        
        self.known_songs = []
        for album_type in ['studioAlbums', 'compilationAlbums', 'liveAlbums']:
            for album in self.static_data['discography'][album_type]:
                if 'tracks' in album and isinstance(album['tracks'], list):
                    for track in album['tracks']:
                        self.known_songs.append({
                            'name': track.lower(),
                            'album': album['name']
                        })

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

        # --- Entity Recognition ---
        entities = []
        # Members
        for member_name in self.known_members:
            if member_name in clean_message:
                member_details = next((m for m in self.static_data['bandInfo']['currentMembers'] if m['name'].lower() == member_name), None) or \
                                 next((m for m in self.static_data['bandInfo']['formerMembers'] if m['name'].lower() == member_name), None)
                if member_details:
                    entities.append({'type': 'member', 'value': member_details})
        # Albums
        for album_name in self.known_albums:
            if album_name in clean_message:
                album_details = next((a for a in self.static_data['discography']['studioAlbums'] if a['name'].lower() == album_name), None) or \
                                next((a for a in self.static_data['discography']['compilationAlbums'] if a['name'].lower() == album_name), None) or \
                                next((a for a in self.static_data['discography']['liveAlbums'] if a['name'].lower() == album_name), None)
                if album_details:
                    entities.append({'type': 'album', 'value': album_details})

        # Songs
        for song_info in self.known_songs:
            if song_info['name'] in clean_message:
                 entities.append({'type': 'song', 'value': {'name': song_info['name'], 'album': song_info['album']}})

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