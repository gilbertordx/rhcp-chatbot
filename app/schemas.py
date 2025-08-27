from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Entity(BaseModel):
    """Entity model for recognized entities in user input."""

    type: Literal["member", "album", "song", "band"]
    value: dict = Field(..., description="Entity details including name and metadata")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Entity recognition confidence"
    )

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        return v


class ResponseModel(BaseModel):
    """Unified response model for chatbot inference results."""

    intent: Literal[
        "greetings.hello",
        "greetings.bye",
        "member.biography",
        "band.members",
        "album.info",
        "song.info",
        "band.history",
        "intent.outofscope",
        "unknown",
    ] = Field(..., description="Final intent after confidence gating")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score for the intent"
    )
    entities: list[Entity] = Field(
        default_factory=list, description="Recognized entities"
    )
    final_message: str = Field(
        ..., min_length=1, description="Response message to user"
    )
    raw_intent: str | None = Field(
        None, description="Raw intent before gating (for debugging)"
    )
    raw_confidence: float | None = Field(
        None, ge=0.0, le=1.0, description="Raw confidence before gating (for debugging)"
    )

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        return v

    @field_validator("raw_confidence")
    @classmethod
    def validate_raw_confidence(cls, v):
        if v is not None and not 0.0 <= v <= 1.0:
            raise ValueError("raw_confidence must be between 0.0 and 1.0")
        return v

    @field_validator("final_message")
    @classmethod
    def validate_final_message(cls, v):
        if not v or not v.strip():
            raise ValueError("final_message cannot be empty or whitespace")
        return v.strip()


class ChatRequest(BaseModel):
    """Request model for chat API endpoint."""

    message: str = Field(..., min_length=1, max_length=2000, description="User message")

    @field_validator("message")
    @classmethod
    def validate_message(cls, v):
        if not v or not v.strip():
            raise ValueError("message cannot be empty or whitespace")
        return v.strip()


class ChatResponse(BaseModel):
    """Response model for chat API endpoint."""

    response: ResponseModel = Field(..., description="Inference response")
    session_id: str | None = Field(None, description="Session identifier")

    model_config = ConfigDict(extra="forbid")
