from typing import Any, Literal

from app.chatbot.memory import ConversationMemory
from app.chatbot.processor import ChatbotProcessor
from app.infra.logging import get_logger
from app.schemas import Entity, ResponseModel

# Type alias for valid intents
IntentType = Literal[
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

logger = get_logger(__name__)

# Global instances - initialized by the application
chatbot_processor: ChatbotProcessor | None = None
memory_manager: ConversationMemory | None = None


def initialize_inference(
    processor: ChatbotProcessor, memory: ConversationMemory
) -> None:
    """Initialize the inference pipeline with processor and memory instances."""
    global chatbot_processor, memory_manager
    chatbot_processor = processor
    memory_manager = memory
    logger.info("Inference pipeline initialized")


def classify(message: str) -> tuple[str, float, list[dict[str, Any]]]:
    """
    Run classification on the input message.

    Returns:
        tuple: (raw_intent, raw_confidence, raw_entities)
    """
    if not chatbot_processor:
        raise RuntimeError("Inference pipeline not initialized")

    # Get raw classifications
    classifications = chatbot_processor.get_classifications(message.lower())

    if not classifications:
        return "unknown", 0.0, []

    top_classification = classifications[0]
    raw_intent = top_classification["label"]
    raw_confidence = top_classification["value"]

    # Get raw entities
    raw_entities = chatbot_processor._find_entities_in_text(message.lower())

    logger.debug(f"Raw classification: {raw_intent} ({raw_confidence:.3f})")
    return raw_intent, raw_confidence, raw_entities


def apply_confidence_gating(
    raw_intent: str, raw_confidence: float
) -> tuple[IntentType, float]:
    """
    Apply confidence gating to determine final intent.

    Args:
        raw_intent: Raw intent from classifier
        raw_confidence: Raw confidence score

    Returns:
        tuple: (final_intent, final_confidence)
    """
    CONFIDENCE_THRESHOLD = 0.60

    if raw_confidence >= CONFIDENCE_THRESHOLD:
        # Validate that raw_intent is a valid IntentType
        valid_intents = [
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
        if raw_intent in valid_intents:
            final_intent: IntentType = raw_intent  # type: ignore
        else:
            final_intent: IntentType = "unknown"
        final_confidence = raw_confidence
        logger.debug(f"Confidence gating: accepted {raw_intent} ({raw_confidence:.3f})")
    else:
        final_intent: IntentType = "unknown"
        final_confidence = raw_confidence
        logger.debug(
            f"Confidence gating: rejected {raw_intent} ({raw_confidence:.3f}) -> unknown"
        )

    return final_intent, final_confidence


def canonicalize_entities(raw_entities: list[dict[str, Any]]) -> list[Entity]:
    """
    Canonicalize raw entities to validated Entity objects.

    Args:
        raw_entities: Raw entities from processor

    Returns:
        List of validated Entity objects
    """
    canonical_entities = []

    for raw_entity in raw_entities:
        try:
            # Validate entity type
            entity_type = raw_entity.get("type")
            if entity_type not in ["member", "album", "song", "band"]:
                logger.warning(f"Skipping invalid entity type: {entity_type}")
                continue

            # Create validated Entity
            entity = Entity(
                type=entity_type,
                value=raw_entity.get("value", {}),
                confidence=raw_entity.get("confidence", 0.5),
            )
            canonical_entities.append(entity)

        except Exception as e:
            logger.warning(f"Failed to canonicalize entity {raw_entity}: {e}")
            continue

    logger.debug(
        f"Canonicalized {len(canonical_entities)} entities from {len(raw_entities)} raw entities"
    )
    return canonical_entities


def build_response(
    final_intent: IntentType,
    final_confidence: float,
    canonical_entities: list[Entity],
    raw_intent: str,
    raw_confidence: float,
    session_id: str | None = None,
) -> ResponseModel:
    """
    Build the final response message and create ResponseModel.

    Args:
        final_intent: Intent after confidence gating
        final_confidence: Confidence after gating
        canonical_entities: Validated entities
        raw_intent: Raw intent for debugging
        raw_confidence: Raw confidence for debugging
        session_id: Optional session ID for context

    Returns:
        Validated ResponseModel
    """
    if not chatbot_processor:
        raise RuntimeError("Inference pipeline not initialized")

    # Build response message based on intent and entities
    if final_intent == "unknown":
        final_message = "I'm not sure what you mean. Let's talk about RHCP! What would you like to know about the Red Hot Chili Peppers?"
    else:
        # Use the processor to generate contextual response
        final_message = chatbot_processor._generate_contextual_response(
            "", final_intent, [e.dict() for e in canonical_entities], session_id
        )

    # Create ResponseModel
    response = ResponseModel(
        intent=final_intent,
        confidence=final_confidence,
        entities=canonical_entities,
        final_message=final_message,
        raw_intent=raw_intent,
        raw_confidence=raw_confidence,
    )

    logger.info(f"Final response: {final_intent} ({final_confidence:.3f})")
    return response


def run_inference(message: str, session_id: str | None = None) -> ResponseModel:
    """
    Run the complete inference pipeline.

    Args:
        message: User input message
        session_id: Optional session ID for context

    Returns:
        Validated ResponseModel
    """
    if not chatbot_processor:
        raise RuntimeError("Inference pipeline not initialized")

    logger.info(
        f"Running inference on message: {message[:50]}{'...' if len(message) > 50 else ''}"
    )

    # Step 1: Classify
    raw_intent, raw_confidence, raw_entities = classify(message)

    # Step 2: Apply confidence gating
    final_intent, final_confidence = apply_confidence_gating(raw_intent, raw_confidence)

    # Step 3: Canonicalize entities
    canonical_entities = canonicalize_entities(raw_entities)

    # Step 4: Build response
    response = build_response(
        final_intent,
        final_confidence,
        canonical_entities,
        raw_intent,
        raw_confidence,
        session_id,
    )

    # Update memory if session_id provided
    if session_id and memory_manager:
        try:
            memory_manager.add_message(session_id, message, response.model_dump())
        except Exception as e:
            logger.warning(f"Failed to update memory for session {session_id}: {e}")

    return response
