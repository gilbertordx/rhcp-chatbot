from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_current_active_user, get_optional_user
from app.models.user import User

class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None

class SessionResponse(BaseModel):
    session_id: str
    message: str
    intent: str
    confidence: float
    entities: list
    classifications: list
    context: Optional[dict] = None
    user_id: Optional[int] = None
    username: Optional[str] = None

router = APIRouter()

@router.post("/", response_model=SessionResponse)
async def process_chat_message(
    chat_message: ChatMessage, 
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    user_message = chat_message.message
    session_id = chat_message.session_id
    
    if not user_message:
        raise HTTPException(status_code=400, detail="User message is required.")

    chatbot_processor = request.app.state.chatbot_processor
    if not chatbot_processor:
        raise HTTPException(status_code=503, detail="Chatbot processor is not initialized.")

    try:
        # Create new session if none provided
        if not session_id:
            session_id = chatbot_processor.memory_manager.create_session()
        
        # Check if session is valid
        if not chatbot_processor.memory_manager.is_session_valid(session_id):
            # Create new session if old one expired
            session_id = chatbot_processor.memory_manager.create_session()
        
        # Process message with session context
        response = chatbot_processor.process_message(user_message, session_id)
        
        # Get classifications
        classifications = chatbot_processor.get_classifications(user_message)
        
        # Get conversation context
        context = chatbot_processor.memory_manager.get_context(session_id)
        
        # Create complete response
        complete_response = {
            'message': response['message'],
            'intent': response['intent'],
            'confidence': response['confidence'],
            'entities': response['entities'],
            'classifications': classifications,
            'context': context,
            'session_id': session_id,
            'user_id': current_user.id if current_user else None,
            'username': current_user.username if current_user else None
        }
        
        return complete_response
    except Exception as e:
        # For debugging, it's helpful to see the error.
        print(f"Error processing message: {e}")
        # In a real app, you'd want more specific error handling and logging
        raise HTTPException(status_code=500, detail="An error occurred while processing your message.")

@router.get("/session/{session_id}/context")
async def get_session_context(
    session_id: str, 
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Get conversation context for a specific session."""
    chatbot_processor = request.app.state.chatbot_processor
    if not chatbot_processor:
        raise HTTPException(status_code=503, detail="Chatbot processor is not initialized.")
    
    if not chatbot_processor.memory_manager.is_session_valid(session_id):
        raise HTTPException(status_code=404, detail="Session not found or expired.")
    
    context = chatbot_processor.memory_manager.get_context(session_id)
    history = chatbot_processor.memory_manager.get_conversation_history(session_id)
    
    return {
        "session_id": session_id,
        "context": context,
        "history": history,
        "user_id": current_user.id if current_user else None,
        "username": current_user.username if current_user else None
    }

@router.delete("/session/{session_id}")
async def delete_session(
    session_id: str, 
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Delete a conversation session."""
    chatbot_processor = request.app.state.chatbot_processor
    if not chatbot_processor:
        raise HTTPException(status_code=503, detail="Chatbot processor is not initialized.")
    
    if session_id in chatbot_processor.memory_manager.sessions:
        del chatbot_processor.memory_manager.sessions[session_id]
        return {"message": "Session deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="Session not found.")

@router.get("/sessions/stats")
async def get_session_stats(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Get statistics about active sessions."""
    chatbot_processor = request.app.state.chatbot_processor
    if not chatbot_processor:
        raise HTTPException(status_code=503, detail="Chatbot processor is not initialized.")
    
    stats = chatbot_processor.memory_manager.get_session_stats()
    
    # Add user-specific stats if authenticated
    if current_user:
        stats["user_id"] = current_user.id
        stats["username"] = current_user.username
    
    return stats

@router.get("/my-sessions")
async def get_user_sessions(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all sessions for the current user."""
    chatbot_processor = request.app.state.chatbot_processor
    if not chatbot_processor:
        raise HTTPException(status_code=503, detail="Chatbot processor is not initialized.")
    
    # This would require storing user_id with sessions in the memory manager
    # For now, return a placeholder response
    return {
        "message": "User session tracking will be implemented in the next iteration",
        "user_id": current_user.id,
        "username": current_user.username
    }

@router.get("/band-stats")
async def get_band_statistics(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Get comprehensive band statistics."""
    chatbot_processor = request.app.state.chatbot_processor
    if not chatbot_processor:
        raise HTTPException(status_code=503, detail="Chatbot processor is not initialized.")
    
    static_data = chatbot_processor.static_data
    
    # Calculate statistics
    total_albums = len(static_data['discography']['studioAlbums']) + \
                   len(static_data['discography']['compilationAlbums']) + \
                   len(static_data['discography']['liveAlbums'])
    
    total_songs = 0
    for album_type in ['studioAlbums', 'compilationAlbums', 'liveAlbums']:
        for album in static_data['discography'][album_type]:
            if 'tracks' in album and isinstance(album['tracks'], list):
                total_songs += len(album['tracks'])
    
    current_year = 2024
    band_age = current_year - static_data['bandInfo']['formed']
    
    stats = {
        "band_name": static_data['bandInfo']['name'],
        "formed": static_data['bandInfo']['formed'],
        "age_years": band_age,
        "location": static_data['bandInfo']['location'],
        "current_members": len(static_data['bandInfo']['currentMembers']),
        "former_members": len(static_data['bandInfo']['formerMembers']),
        "total_albums": total_albums,
        "studio_albums": len(static_data['discography']['studioAlbums']),
        "compilation_albums": len(static_data['discography']['compilationAlbums']),
        "live_albums": len(static_data['discography']['liveAlbums']),
        "total_songs": total_songs,
        "genres": static_data['bandInfo']['genres'],
        "awards_count": len(static_data['bandInfo']['awards']),
        "labels": static_data['bandInfo']['labels']
    }
    
    return stats

@router.get("/recommendations")
async def get_recommendations(
    request: Request,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Get recommendations for albums, songs, or band members."""
    chatbot_processor = request.app.state.chatbot_processor
    if not chatbot_processor:
        raise HTTPException(status_code=503, detail="Chatbot processor is not initialized.")
    
    static_data = chatbot_processor.static_data
    
    recommendations = {}
    
    if not category or category == "albums":
        # Recommend essential albums
        essential_albums = [
            "Blood Sugar Sex Magik",
            "Californication", 
            "By the Way",
            "Stadium Arcadium",
            "Unlimited Love"
        ]
        
        recommendations["albums"] = []
        for album_name in essential_albums:
            for album in static_data['discography']['studioAlbums']:
                if album['name'] == album_name:
                    recommendations["albums"].append({
                        "name": album['name'],
                        "release_date": album['releaseDate'],
                        "producer": album.get('producer', 'Unknown'),
                        "key_tracks": album.get('tracks', [])[:3] if album.get('tracks') else []
                    })
                    break
    
    if not category or category == "songs":
        # Recommend essential songs
        essential_songs = [
            "Under the Bridge",
            "Californication",
            "Scar Tissue", 
            "Otherside",
            "By the Way",
            "Dani California",
            "Snow (Hey Oh)",
            "Give It Away"
        ]
        
        recommendations["songs"] = []
        for song_name in essential_songs:
            for album in static_data['discography']['studioAlbums']:
                if 'tracks' in album and song_name in album['tracks']:
                    recommendations["songs"].append({
                        "name": song_name,
                        "album": album['name'],
                        "release_date": album['releaseDate']
                    })
                    break
    
    if not category or category == "members":
        # Recommend learning about current members
        recommendations["members"] = []
        for member in static_data['bandInfo']['currentMembers']:
            recommendations["members"].append({
                "name": member['name'],
                "role": member['role'],
                "member_since": member['memberSince'],
                "key_contribution": member.get('biography', '').split('.')[0] + '.'
            })
    
    return recommendations

@router.get("/search")
async def search_content(
    request: Request,
    query: str,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Search for albums, songs, or band members."""
    chatbot_processor = request.app.state.chatbot_processor
    if not chatbot_processor:
        raise HTTPException(status_code=503, detail="Chatbot processor is not initialized.")
    
    if not query or len(query.strip()) < 2:
        raise HTTPException(status_code=400, detail="Search query must be at least 2 characters long.")
    
    query_lower = query.lower().strip()
    results = {}
    
    # Search in members
    if not category or category == "members":
        results["members"] = []
        for member in chatbot_processor.static_data['bandInfo']['currentMembers'] + \
                       chatbot_processor.static_data['bandInfo']['formerMembers']:
            if query_lower in member['name'].lower() or \
               query_lower in member.get('role', '').lower() or \
               query_lower in member.get('biography', '').lower():
                results["members"].append({
                    "name": member['name'],
                    "role": member['role'],
                    "member_since": member.get('memberSince'),
                    "type": "current" if member in chatbot_processor.static_data['bandInfo']['currentMembers'] else "former"
                })
    
    # Search in albums
    if not category or category == "albums":
        results["albums"] = []
        for album_type in ['studioAlbums', 'compilationAlbums', 'liveAlbums']:
            for album in chatbot_processor.static_data['discography'][album_type]:
                if query_lower in album['name'].lower() or \
                   query_lower in album.get('producer', '').lower():
                    results["albums"].append({
                        "name": album['name'],
                        "release_date": album['releaseDate'],
                        "producer": album.get('producer', 'Unknown'),
                        "type": album_type,
                        "track_count": len(album.get('tracks', []))
                    })
    
    # Search in songs
    if not category or category == "songs":
        results["songs"] = []
        for album_type in ['studioAlbums', 'compilationAlbums', 'liveAlbums']:
            for album in chatbot_processor.static_data['discography'][album_type]:
                if 'tracks' in album and isinstance(album['tracks'], list):
                    for track in album['tracks']:
                        if query_lower in track.lower():
                            results["songs"].append({
                                "name": track,
                                "album": album['name'],
                                "release_date": album['releaseDate'],
                                "album_type": album_type
                            })
    
    return results 

@router.get("/analytics")
async def get_conversation_analytics(
    request: Request,
    session_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Get conversation analytics and insights."""
    chatbot_processor = request.app.state.chatbot_processor
    if not chatbot_processor:
        raise HTTPException(status_code=503, detail="Chatbot processor is not initialized.")
    
    analytics = {
        "total_sessions": len(chatbot_processor.memory_manager.sessions),
        "active_sessions": sum(1 for session in chatbot_processor.memory_manager.sessions.values() 
                              if chatbot_processor.memory_manager.is_session_valid(session)),
        "session_stats": chatbot_processor.memory_manager.get_session_stats()
    }
    
    # If specific session is provided, get detailed analytics
    if session_id and chatbot_processor.memory_manager.is_session_valid(session_id):
        session = chatbot_processor.memory_manager.sessions[session_id]
        context = session['context']
        history = session['messages']
        
        session_analytics = {
            "session_id": session_id,
            "created_at": session['created_at'].isoformat(),
            "last_activity": session['last_activity'].isoformat(),
            "total_messages": len(history),
            "conversation_duration_minutes": (session['last_activity'] - session['created_at']).total_seconds() / 60,
            "current_topic": context.get('current_topic'),
            "topic_confidence": context.get('topic_confidence', 0.0),
            "patterns": context.get('patterns', {}),
            "mentioned_entities": {
                "members": list(context.get('mentioned_members', [])),
                "albums": list(context.get('mentioned_albums', [])),
                "songs": list(context.get('mentioned_songs', []))
            },
            "conversation_flow": context.get('conversation_flow', [])
        }
        
        # Calculate intent distribution
        intent_counts = {}
        for message in history:
            intent = message.get('intent')
            if intent:
                intent_counts[intent] = intent_counts.get(intent, 0) + 1
        
        session_analytics["intent_distribution"] = intent_counts
        
        # Calculate average confidence
        confidences = [msg.get('confidence', 0.0) for msg in history if msg.get('confidence')]
        if confidences:
            session_analytics["average_confidence"] = sum(confidences) / len(confidences)
            session_analytics["max_confidence"] = max(confidences)
            session_analytics["min_confidence"] = min(confidences)
        
        analytics["session_details"] = session_analytics
    
    # Add user-specific analytics if authenticated
    if current_user:
        analytics["user_id"] = current_user.id
        analytics["username"] = current_user.username
    
    return analytics 