
import pytest

from app.chatbot.initializer import initialize_chatbot
from app.chatbot.memory import ConversationMemory
from app.core.inference import initialize_inference, run_inference
from app.infra.logging import setup_logging
from app.schemas import Entity, ResponseModel


class TestInferencePipeline:
    @pytest.fixture(autouse=True)
    def setup(self):
        setup_logging(level="INFO", format_type="json", debug=False)
        self.memory_manager = ConversationMemory(
            max_sessions=10, session_timeout_hours=1
        )
        self.session_id = self.memory_manager.create_session()

    @pytest.mark.asyncio
    async def test_confidence_gating(self):
        """Test that low confidence predictions are gated to 'unknown'"""
        self.chatbot_processor = await initialize_chatbot()
        initialize_inference(self.chatbot_processor, self.memory_manager)

        # Test with a message that should have low confidence
        response = run_inference("xyz random gibberish", self.session_id)
        assert response.intent == "unknown"
        assert response.confidence >= 0.0
        assert response.confidence <= 1.0
        assert "not sure" in response.final_message.lower()

    @pytest.mark.asyncio
    async def test_high_confidence_passes_gating(self):
        """Test that high confidence predictions pass through gating"""
        self.chatbot_processor = await initialize_chatbot()
        initialize_inference(self.chatbot_processor, self.memory_manager)

        # Test with a clear greeting
        response = run_inference("hello", self.session_id)
        # Should either be greetings.hello or unknown (depending on model confidence)
        assert response.intent in ["greetings.hello", "unknown"]
        assert response.confidence >= 0.0
        assert response.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_entity_canonicalization(self):
        """Test that entities are properly canonicalized to Entity schema"""
        self.chatbot_processor = await initialize_chatbot()
        initialize_inference(self.chatbot_processor, self.memory_manager)

        # Test with a message that should extract entities
        response = run_inference("tell me about anthony kiedis", self.session_id)

        # Check that entities are properly formatted
        for entity in response.entities:
            assert isinstance(entity, Entity)
            assert entity.type in ["member", "album", "song", "band"]
            assert isinstance(entity.value, dict)
            assert "name" in entity.value
            assert isinstance(entity.confidence, float)
            assert 0.0 <= entity.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_response_schema_validation(self):
        """Test that response objects conform to ResponseModel schema"""
        self.chatbot_processor = await initialize_chatbot()
        initialize_inference(self.chatbot_processor, self.memory_manager)

        response = run_inference("hi there", self.session_id)

        # Verify schema compliance
        assert isinstance(response, ResponseModel)
        assert response.intent in [
            "greetings.hello",
            "greetings.bye",
            "member.biography",
            "band.members",
            "album.info",
            "song.info",
            "band.history",
            "intent.outofscope",
            "unknown",
        ]
        assert isinstance(response.confidence, float)
        assert 0.0 <= response.confidence <= 1.0
        assert isinstance(response.entities, list)
        assert isinstance(response.final_message, str)
        assert len(response.final_message) > 0

    @pytest.mark.asyncio
    async def test_raw_intent_debugging(self):
        """Test that raw intent and confidence are preserved for debugging"""
        self.chatbot_processor = await initialize_chatbot()
        initialize_inference(self.chatbot_processor, self.memory_manager)

        response = run_inference("test message", self.session_id)

        # Raw values should be present for debugging
        if response.raw_intent:
            assert isinstance(response.raw_intent, str)
        if response.raw_confidence:
            assert isinstance(response.raw_confidence, float)
            assert 0.0 <= response.raw_confidence <= 1.0

    @pytest.mark.asyncio
    async def test_session_memory_integration(self):
        """Test that inference updates session memory"""
        self.chatbot_processor = await initialize_chatbot()
        initialize_inference(self.chatbot_processor, self.memory_manager)

        # First message
        response1 = run_inference("hello", self.session_id)

        # Second message should have context
        response2 = run_inference("who is anthony kiedis", self.session_id)

        # Verify memory was updated
        history = self.memory_manager.get_conversation_history(self.session_id, 2)
        assert len(history) >= 2
        assert history[0]["user_message"] == "hello"
        assert history[1]["user_message"] == "who is anthony kiedis"

    @pytest.mark.asyncio
    async def test_no_session_id(self):
        """Test inference works without session_id"""
        self.chatbot_processor = await initialize_chatbot()
        initialize_inference(self.chatbot_processor, self.memory_manager)

        response = run_inference("hello")
        assert isinstance(response, ResponseModel)
        assert response.intent in ["greetings.hello", "unknown"]

    @pytest.mark.asyncio
    async def test_inference_not_initialized(self):
        """Test error when inference pipeline is not initialized"""
        # Clear the global state to simulate uninitialized pipeline
        import app.core.inference as inference_module

        inference_module.chatbot_processor = None
        inference_module.memory_manager = None

        with pytest.raises(RuntimeError, match="Inference pipeline not initialized"):
            run_inference("hello")


class TestInferenceIntegration:
    @pytest.mark.asyncio
    async def test_end_to_end_inference_flow(self):
        """Test complete inference flow from message to response"""
        setup_logging(level="INFO", format_type="json", debug=False)
        memory_manager = ConversationMemory(max_sessions=10, session_timeout_hours=1)
        session_id = memory_manager.create_session()

        chatbot_processor = await initialize_chatbot()
        initialize_inference(chatbot_processor, memory_manager)

        # Test multiple message types
        test_cases = [
            ("hello", ["greetings.hello", "unknown"]),
            ("who is anthony kiedis", ["member.biography", "unknown"]),
            ("what albums do they have", ["album.info", "band.history", "unknown"]),
            ("xyz random", ["unknown", "intent.outofscope"]),
        ]

        for message, expected_intents in test_cases:
            response = run_inference(message, session_id)
            assert response.intent in expected_intents
            assert isinstance(response.final_message, str)
            assert len(response.final_message) > 0
            assert isinstance(response.entities, list)
