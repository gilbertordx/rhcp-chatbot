import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json

class ConversationMemory:
    def __init__(self, max_sessions: int = 100, session_timeout_hours: int = 24):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.max_sessions = max_sessions
        self.session_timeout_hours = session_timeout_hours
    
    def create_session(self) -> str:
        """Create a new conversation session and return its ID."""
        session_id = str(uuid.uuid4())
        
        # Clean up old sessions if we're at capacity
        if len(self.sessions) >= self.max_sessions:
            self._cleanup_old_sessions()
        
        self.sessions[session_id] = {
            'created_at': datetime.now(),
            'last_activity': datetime.now(),
            'messages': [],
            'entities': [],
            'context': {
                'current_topic': None,
                'mentioned_members': set(),
                'mentioned_albums': set(),
                'mentioned_songs': set(),
                'conversation_flow': []
            }
        }
        
        return session_id
    
    def add_message(self, session_id: str, user_message: str, bot_response: Dict[str, Any]) -> None:
        """Add a message exchange to the conversation history."""
        if session_id not in self.sessions:
            return
        
        session = self.sessions[session_id]
        session['last_activity'] = datetime.now()
        
        # Add message to history
        message_entry = {
            'timestamp': datetime.now().isoformat(),
            'user_message': user_message,
            'bot_response': bot_response,
            'intent': bot_response.get('intent'),
            'confidence': bot_response.get('confidence'),
            'entities': bot_response.get('entities', [])
        }
        
        session['messages'].append(message_entry)
        
        # Update context
        self._update_context(session_id, message_entry)
        
        # Keep only last 10 messages to prevent memory bloat
        if len(session['messages']) > 10:
            session['messages'] = session['messages'][-10:]
    
    def get_conversation_history(self, session_id: str, max_messages: int = 5) -> List[Dict[str, Any]]:
        """Get recent conversation history for context."""
        if session_id not in self.sessions:
            return []
        
        session = self.sessions[session_id]
        return session['messages'][-max_messages:]
    
    def get_context(self, session_id: str) -> Dict[str, Any]:
        """Get conversation context including mentioned entities and topics."""
        if session_id not in self.sessions:
            return {}
        
        session = self.sessions[session_id]
        context = session['context'].copy()
        
        # Convert sets to lists for JSON serialization
        context['mentioned_members'] = list(context['mentioned_members'])
        context['mentioned_albums'] = list(context['mentioned_albums'])
        context['mentioned_songs'] = list(context['mentioned_songs'])
        
        return context
    
    def _update_context(self, session_id: str, message_entry: Dict[str, Any]) -> None:
        """Update conversation context based on the latest message."""
        session = self.sessions[session_id]
        context = session['context']
        
        # Update mentioned entities
        entities = message_entry.get('entities', [])
        for entity in entities:
            if entity['type'] == 'member':
                member_name = entity['value']['name']
                context['mentioned_members'].add(member_name)
                # Track member type (current/former)
                if entity.get('member_type'):
                    if 'member_types' not in context:
                        context['member_types'] = {}
                    context['member_types'][member_name] = entity['member_type']
            elif entity['type'] == 'album':
                album_name = entity['value']['name']
                context['mentioned_albums'].add(album_name)
                # Track album type
                if entity.get('album_type'):
                    if 'album_types' not in context:
                        context['album_types'] = {}
                    context['album_types'][album_name] = entity['album_type']
            elif entity['type'] == 'song':
                song_name = entity['value']['name']
                context['mentioned_songs'].add(song_name)
                # Track song album
                if 'song_albums' not in context:
                    context['song_albums'] = {}
                context['song_albums'][song_name] = entity['value']['album']
        
        # Update conversation flow with more detailed tracking
        intent = message_entry.get('intent')
        if intent and intent not in ['unrecognized', 'None']:
            # Add intent with timestamp for better flow analysis
            flow_entry = {
                'intent': intent,
                'timestamp': message_entry['timestamp'],
                'confidence': message_entry.get('confidence', 0.0),
                'entities_count': len(entities)
            }
            context['conversation_flow'].append(flow_entry)
            
            # Keep only last 10 flow entries
            if len(context['conversation_flow']) > 10:
                context['conversation_flow'] = context['conversation_flow'][-10:]
        
        # Update current topic based on intent and entities
        if intent in ['member.biography', 'band.members'] or any(e['type'] == 'member' for e in entities):
            context['current_topic'] = 'band_members'
            context['topic_confidence'] = 0.9
        elif intent in ['album.specific', 'album.info'] or any(e['type'] == 'album' for e in entities):
            context['current_topic'] = 'albums'
            context['topic_confidence'] = 0.9
        elif intent in ['song.specific', 'song.info', 'song.lyrics'] or any(e['type'] == 'song' for e in entities):
            context['current_topic'] = 'songs'
            context['topic_confidence'] = 0.9
        elif intent in ['band.history', 'band.tours']:
            context['current_topic'] = 'band_history'
            context['topic_confidence'] = 0.8
        elif intent in ['band.style', 'band.influence']:
            context['current_topic'] = 'band_style'
            context['topic_confidence'] = 0.8
        elif intent in ['band.awards', 'band.collaborations']:
            context['current_topic'] = 'band_achievements'
            context['topic_confidence'] = 0.8
        else:
            # Lower confidence for general topics
            context['topic_confidence'] = context.get('topic_confidence', 0.0) * 0.8
        
        # Track conversation patterns
        if 'patterns' not in context:
            context['patterns'] = {
                'member_questions': 0,
                'album_questions': 0,
                'song_questions': 0,
                'follow_up_questions': 0,
                'general_questions': 0
            }
        
        # Update pattern counts
        if intent in ['member.biography', 'band.members']:
            context['patterns']['member_questions'] += 1
        elif intent in ['album.specific', 'album.info']:
            context['patterns']['album_questions'] += 1
        elif intent in ['song.specific', 'song.info', 'song.lyrics']:
            context['patterns']['song_questions'] += 1
        elif intent in ['band.history', 'band.tours', 'band.style', 'band.influence', 'band.awards', 'band.collaborations']:
            context['patterns']['general_questions'] += 1
        
        # Detect follow-up questions
        user_message = message_entry.get('user_message', '').lower()
        follow_up_indicators = ['what about', 'how about', 'tell me more', 'and', 'also', 'too', 'what else', 'anything else', 'more', 'other', 'different']
        if any(indicator in user_message for indicator in follow_up_indicators):
            context['patterns']['follow_up_questions'] += 1
    
    def _cleanup_old_sessions(self) -> None:
        """Remove old sessions to prevent memory bloat."""
        current_time = datetime.now()
        timeout_threshold = current_time - timedelta(hours=self.session_timeout_hours)
        
        sessions_to_remove = []
        for session_id, session in self.sessions.items():
            if session['last_activity'] < timeout_threshold:
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            del self.sessions[session_id]
    
    def is_session_valid(self, session_id: str) -> bool:
        """Check if a session is still valid (not expired)."""
        if session_id not in self.sessions:
            return False
        
        session = self.sessions[session_id]
        timeout_threshold = datetime.now() - timedelta(hours=self.session_timeout_hours)
        return session['last_activity'] > timeout_threshold
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics about active sessions."""
        return {
            'total_sessions': len(self.sessions),
            'max_sessions': self.max_sessions,
            'session_timeout_hours': self.session_timeout_hours
        } 