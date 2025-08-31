from typing import Any, Literal

from app.chatbot.memory import ConversationMemory
from app.chatbot.processor import ChatbotProcessor
from app.infra.logging import get_logger
from app.knowledge.resolver import get_knowledge_resolver
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
    knowledge_resolver = get_knowledge_resolver()

    for raw_entity in raw_entities:
        try:
            # Validate entity type
            entity_type = raw_entity.get("type")
            if entity_type not in ["member", "album", "song", "band"]:
                logger.warning(f"Skipping invalid entity type: {entity_type}")
                continue

            # Get the raw value from the entity
            raw_value = raw_entity.get("value", {})
            if isinstance(raw_value, dict):
                span = raw_value.get("text", "")
            else:
                span = str(raw_value)

            # Use knowledge resolver to get canonical entity
            canonical_entity = None
            if entity_type == "member":
                canonical_entity = knowledge_resolver.resolve_member(span)
            elif entity_type == "album":
                canonical_entity = knowledge_resolver.resolve_album(span)
            elif entity_type == "song":
                canonical_entity = knowledge_resolver.resolve_song(span)

            # Create validated Entity with resolved data
            if canonical_entity:
                entity = Entity(
                    type=entity_type,
                    value=canonical_entity,
                    confidence=raw_entity.get("confidence", 0.5),
                )
                canonical_entities.append(entity)
                logger.debug(f"Resolved entity '{span}' to canonical '{canonical_entity.get('name', canonical_entity.get('title', span))}'")
            else:
                # Fallback to original entity if resolution fails
                entity = Entity(
                    type=entity_type,
                    value=raw_value,
                    confidence=raw_entity.get("confidence", 0.5),
                )
                canonical_entities.append(entity)
                logger.debug(f"Could not resolve entity '{span}', using original")

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
        # Use factual retrieval for entity-specific queries to reduce hallucination
        if canonical_entities and final_intent in ["member.biography", "album.info", "song.info"]:
            final_message = _build_factual_response(final_intent, canonical_entities)
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


def _build_factual_response(intent: IntentType, entities: list[Entity]) -> str:
    """
    Build a factual response using retrieved facts from the knowledge base.
    
    Args:
        intent: The resolved intent
        entities: List of canonical entities
        
    Returns:
        Factual response message
    """
    try:
        from app.knowledge.search import get_facts_by_canonical
        
        if not entities:
            return "I don't have enough information to answer that question."
        
        # Get facts for the first entity (most relevant)
        entity = entities[0]
        entity_type = entity.type
        entity_value = entity.value
        
        # Extract canonical name from entity value
        if isinstance(entity_value, dict):
            if entity_type == "member":
                canonical = entity_value.get("canonical", entity_value.get("name", ""))
            elif entity_type == "album":
                canonical = entity_value.get("canonical", entity_value.get("title", ""))
            elif entity_type == "song":
                canonical = entity_value.get("canonical", entity_value.get("title", ""))
            else:
                canonical = str(entity_value)
        else:
            canonical = str(entity_value)
        
        if not canonical:
            return "I don't have enough information to answer that question."
        
        # Retrieve facts for this entity
        facts = get_facts_by_canonical(canonical, entity_type)
        
        if not facts:
            return f"I don't have specific information about {canonical}."
        
        # Build factual response based on intent and entity type
        if intent == "member.biography":
            return _build_member_response(facts, canonical)
        elif intent == "album.info":
            return _build_album_response(facts, canonical)
        elif intent == "song.info":
            return _build_song_response(facts, canonical)
        else:
            return _build_generic_response(facts, canonical, entity_type)
            
    except Exception as e:
        logger.warning(f"Failed to build factual response: {e}")
        # Fallback to generic response
        return f"I have information about {entities[0].value if entities else 'this topic'}, but I'm having trouble retrieving the details right now."


def _build_member_response(facts: list, canonical: str) -> str:
    """Build a factual response for member queries."""
    # Extract key facts
    name = ""
    roles = []
    join_year = None
    active = None
    notes = ""
    
    for fact in facts:
        if fact.field == "name":
            name = fact.value
        elif fact.field == "role":
            roles.append(fact.value)
        elif fact.field == "join_year":
            join_year = fact.value
        elif fact.field == "active":
            active = fact.value
        elif fact.field == "notes":
            notes = fact.value
    
    # Build response
    response_parts = []
    
    if name:
        response_parts.append(f"{name}")
    
    if roles:
        response_parts.append(f"plays {', '.join(roles)}")
    
    if join_year:
        response_parts.append(f"joined in {join_year}")
    
    if active is not None:
        status = "currently active" if active.lower() == "true" else "not currently active"
        response_parts.append(f"is {status}")
    
    if notes:
        response_parts.append(f"Note: {notes}")
    
    if response_parts:
        return " is ".join(response_parts) + "."
    else:
        return f"I have information about {canonical} but the details are incomplete."


def _build_album_response(facts: list, canonical: str) -> str:
    """Build a factual response for album queries."""
    # Extract key facts
    title = ""
    year = None
    label = ""
    tracks = None
    notes = ""
    
    for fact in facts:
        if fact.field == "title":
            title = fact.value
        elif fact.field == "year":
            year = fact.value
        elif fact.field == "label":
            label = fact.value
        elif fact.field == "tracks":
            tracks = fact.value
        elif fact.field == "notes":
            notes = fact.value
    
    # Build response
    response_parts = []
    
    if title:
        response_parts.append(f"{title}")
    
    if year:
        response_parts.append(f"released in {year}")
    
    if label:
        response_parts.append(f"on {label}")
    
    if tracks:
        response_parts.append(f"has {tracks} tracks")
    
    if notes:
        response_parts.append(f"Note: {notes}")
    
    if response_parts:
        return " is ".join(response_parts) + "."
    else:
        return f"I have information about {canonical} but the details are incomplete."


def _build_song_response(facts: list, canonical: str) -> str:
    """Build a factual response for song queries."""
    # Extract key facts
    title = ""
    year = None
    album = ""
    track_no = None
    notes = ""
    
    for fact in facts:
        if fact.field == "title":
            title = fact.value
        elif fact.field == "year":
            year = fact.value
        elif fact.field == "album":
            album = fact.value
        elif fact.field == "track_no":
            track_no = fact.value
        elif fact.field == "notes":
            notes = fact.value
    
    # Build response
    response_parts = []
    
    if title:
        response_parts.append(f"{title}")
    
    if year:
        response_parts.append(f"released in {year}")
    
    if album:
        response_parts.append(f"from the album {album}")
    
    if track_no:
        response_parts.append(f"track {track_no}")
    
    if notes:
        response_parts.append(f"Note: {notes}")
    
    if response_parts:
        return " is ".join(response_parts) + "."
    else:
        return f"I have information about {canonical} but the details are incomplete."


def _build_generic_response(facts: list, canonical: str, entity_type: str) -> str:
    """Build a generic factual response."""
    # Group facts by field for better organization
    field_values = {}
    for fact in facts:
        if fact.field not in field_values:
            field_values[fact.field] = []
        field_values[fact.field].append(fact.value)
    
    response_parts = [f"Here's what I know about {canonical}:"]
    
    for field, values in field_values.items():
        if field in ["name", "title"]:  # Skip redundant fields
            continue
        unique_values = list(set(values))
        if len(unique_values) == 1:
            response_parts.append(f"{field}: {unique_values[0]}")
        else:
            response_parts.append(f"{field}: {', '.join(unique_values)}")
    
    if len(response_parts) > 1:
        return " ".join(response_parts)
    else:
        return f"I have basic information about {canonical} but not many details."


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
