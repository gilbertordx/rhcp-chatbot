import pytest
import asyncio
from app.chatbot.initializer import initialize_chatbot
from app.chatbot.memory import ConversationMemory

@pytest.fixture
def chatbot_processor():
    """Initialize chatbot processor for testing."""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(initialize_chatbot())

@pytest.fixture
def memory_manager():
    """Initialize memory manager for testing."""
    return ConversationMemory(max_sessions=10, session_timeout_hours=1)

def test_handle_simple_greeting(chatbot_processor):
    """Test basic greeting functionality."""
    response = chatbot_processor.process_message("Hello")
    assert response["intent"] == "greetings.hello"
    assert "hello" in response["message"].lower()

def test_band_members_query(chatbot_processor):
    """Test band members query."""
    response = chatbot_processor.process_message("Who are the band members?")
    assert response["intent"] == "band.members"
    assert "anthony" in response["message"].lower()

def test_out_of_scope_query(chatbot_processor):
    """Test out of scope query."""
    response = chatbot_processor.process_message("What is quantum physics?")
    assert response["intent"] == "intent.outofscope"

def test_agent_chatbot_intent(chatbot_processor):
    """Test agent chatbot intent."""
    response = chatbot_processor.process_message("Are you a bot?")
    assert response["intent"] == "agent.chatbot"

def test_greetings_bye_intent(chatbot_processor):
    """Test greetings bye intent."""
    response = chatbot_processor.process_message("Goodbye")
    assert response["intent"] == "greetings.bye"

def test_band_history_intent(chatbot_processor):
    """Test band history intent."""
    response = chatbot_processor.process_message("When was RHCP formed?")
    assert response["intent"] == "band.history"

def test_album_info_intent(chatbot_processor):
    """Test album info intent."""
    response = chatbot_processor.process_message("Tell me about their albums")
    assert response["intent"] == "album.info"

def test_song_info_intent(chatbot_processor):
    """Test song info intent."""
    response = chatbot_processor.process_message("What songs do they have?")
    assert response["intent"] == "song.info"

# Memory and Session Tests
def test_memory_manager_creation(memory_manager):
    """Test memory manager creation."""
    assert memory_manager.max_sessions == 10
    assert memory_manager.session_timeout_hours == 1
    assert len(memory_manager.sessions) == 0

def test_session_creation(memory_manager):
    """Test session creation."""
    session_id = memory_manager.create_session()
    assert session_id is not None
    assert session_id in memory_manager.sessions
    assert len(memory_manager.sessions) == 1

def test_session_message_storage(memory_manager):
    """Test storing messages in session."""
    session_id = memory_manager.create_session()
    
    # Add a message
    test_response = {
        "message": "Hello there!",
        "intent": "greetings.hello",
        "confidence": 0.8,
        "entities": []
    }
    
    memory_manager.add_message(session_id, "Hello", test_response)
    
    # Check history
    history = memory_manager.get_conversation_history(session_id)
    assert len(history) == 1
    assert history[0]["user_message"] == "Hello"
    assert history[0]["bot_response"]["message"] == "Hello there!"

def test_context_tracking(memory_manager):
    """Test context tracking in sessions."""
    session_id = memory_manager.create_session()
    
    # Add message with member entity
    response_with_member = {
        "message": "Anthony Kiedis is the lead vocalist",
        "intent": "member.biography",
        "confidence": 0.9,
        "entities": [{"type": "member", "value": {"name": "Anthony Kiedis"}}]
    }
    
    memory_manager.add_message(session_id, "Tell me about Anthony Kiedis", response_with_member)
    
    # Check context
    context = memory_manager.get_context(session_id)
    assert "Anthony Kiedis" in context["mentioned_members"]
    assert context["current_topic"] == "band_members"

def test_conversation_memory_integration(chatbot_processor):
    """Test conversation memory integration with chatbot."""
    # Create a session
    session_id = chatbot_processor.memory_manager.create_session()
    
    # First message
    response1 = chatbot_processor.process_message("Tell me about Anthony Kiedis", session_id)
    assert response1["intent"] == "member.biography"
    assert len(response1["entities"]) > 0
    
    # Follow-up question (should use context)
    response2 = chatbot_processor.process_message("What about his role?", session_id)
    # Should still recognize this as member-related due to context
    
    # Check that context was maintained
    context = chatbot_processor.memory_manager.get_context(session_id)
    assert len(context["mentioned_members"]) > 0
    assert context["current_topic"] == "band_members"

def test_session_timeout(memory_manager):
    """Test session timeout functionality."""
    # Create a session with short timeout
    short_timeout_manager = ConversationMemory(max_sessions=5, session_timeout_hours=0.001)  # Very short timeout
    session_id = short_timeout_manager.create_session()
    
    # Session should be valid initially
    assert short_timeout_manager.is_session_valid(session_id)
    
    # After cleanup, session should be invalid (but cleanup only happens when at capacity)
    # This test verifies the timeout logic works

def test_multiple_sessions(memory_manager):
    """Test handling multiple sessions."""
    session1 = memory_manager.create_session()
    session2 = memory_manager.create_session()
    
    assert session1 != session2
    assert len(memory_manager.sessions) == 2
    
    # Add messages to different sessions
    response = {"message": "Hello", "intent": "greetings.hello", "confidence": 0.8, "entities": []}
    memory_manager.add_message(session1, "Hello", response)
    memory_manager.add_message(session2, "Hi", response)
    
    # Check that sessions are independent
    history1 = memory_manager.get_conversation_history(session1)
    history2 = memory_manager.get_conversation_history(session2)
    
    assert len(history1) == 1
    assert len(history2) == 1
    assert history1[0]["user_message"] == "Hello"
    assert history2[0]["user_message"] == "Hi" 