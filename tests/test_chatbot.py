import pytest
from app.chatbot.initializer import initialize_chatbot

# Fixture to initialize the chatbot once for the entire test session
@pytest.fixture(scope="session", autouse=True)
def chatbot_processor():
    # Using 'session' scope to initialize only once.
    # The timeout for initialization might need to be handled if it's very long.
    # For now, we assume it completes in a reasonable time for testing.
    # In a more complex setup, you might have a separate, faster test model.
    import asyncio
    loop = asyncio.get_event_loop()
    processor = loop.run_until_complete(initialize_chatbot())
    return processor

def test_handle_simple_greeting(chatbot_processor):
    response = chatbot_processor.process_message('Hello')
    assert response['intent'] == 'greetings.hello'
    assert response['message'] is not None
    assert len(response['message']) > 0

def test_band_members_query(chatbot_processor):
    response = chatbot_processor.process_message('Who are the members of the band?')
    assert response['intent'] == 'band.members'
    assert 'Anthony Kiedis' in response['message']
    assert 'Flea' in response['message']
    assert 'John Frusciante' in response['message']
    assert 'Chad Smith' in response['message']

def test_out_of_scope_query(chatbot_processor):
    response = chatbot_processor.process_message('Tell me about quantum physics')
    assert response['intent'] == 'intent.outofscope'
    oos_answers = [
        "Sorry, I can only help with questions about the Red Hot Chili Peppers.",
        "That's a bit outside of what I know. I'm focused on the Red Hot Chili Peppers.",
        "I'm not equipped to answer that. My expertise is the Red Hot Chili Peppers.",
        "My knowledge is limited to the Red Hot Chili Peppers. Is there anything about them I can help with?"
    ]
    assert response['message'] in oos_answers

def test_agent_chatbot_intent(chatbot_processor):
    response = chatbot_processor.process_message('are you a bot')
    assert response['intent'] == 'agent.chatbot'
    assert response['message'] is not None
    assert len(response['message']) > 0

def test_greetings_bye_intent(chatbot_processor):
    response = chatbot_processor.process_message('bye for now')
    assert response['intent'] == 'greetings.bye'
    assert response['message'] is not None
    assert len(response['message']) > 0

def test_band_history_intent(chatbot_processor):
    response = chatbot_processor.process_message('when was RHCP formed')
    assert response['intent'] == 'band.history'
    assert response['message'] is not None
    assert len(response['message']) > 0

def test_album_info_intent(chatbot_processor):
    response = chatbot_processor.process_message('list their albums')
    assert response['intent'] == 'album.info'
    assert response['message'] is not None
    assert len(response['message']) > 0

def test_song_info_intent(chatbot_processor):
    response = chatbot_processor.process_message('name some of their songs')
    assert response['intent'] == 'song.info'
    assert response['message'] is not None
    assert len(response['message']) > 0 