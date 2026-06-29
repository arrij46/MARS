"""
Data models for user story generation.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class Requirement(BaseModel):
    """Requirement model."""
    id: str
    type: str  # "FR" or "NFR"
    text: str
    
    @field_validator('type')
    def validate_type(cls, v):
        if v not in ["FR", "NFR"]:
            raise ValueError(f"Requirement type must be FR or NFR, got {v}")
        return v


class RequirementsInput(BaseModel):
    """Input model for requirements."""
    requirements: List[Requirement]


class UserStory(BaseModel):
    """User story model."""
    requirement_id: str
    user_story_id: str
    type: str  # "FR" or "NFR"
    text: str
    
    @field_validator('type')
    def validate_type(cls, v):
        if v not in ["FR", "NFR"]:
            raise ValueError(f"User story type must be FR or NFR, got {v}")
        return v
    
    @field_validator('text')
    def validate_text(cls, v):
        if not v or v.strip() == "":
            raise ValueError("User story text cannot be empty")
        return v


class RequirementBatch(BaseModel):
    """Batch of requirements for processing."""
    batch_id: str
    type: str  # "FR" or "NFR"
    requirements: List[Requirement]
    estimated_tokens: int = 0


class OpenRouterResponse(BaseModel):
    """Response model for OpenRouter API."""
    stories: List[Dict[str, Any]] = Field(default_factory=list)
    batch_id: Optional[str] = None
    requirement_ids: List[str] = Field(default_factory=list)


class OllamaResponse(BaseModel):
    """Response model for Ollama API."""
    stories: List[Dict[str, Any]] = Field(default_factory=list)
    batch_id: Optional[str] = None
    requirement_ids: List[str] = Field(default_factory=list)
    failed_requirements: List[str] = Field(default_factory=list)


class OutputMetadata(BaseModel):
    """Metadata for output."""
    total_requirements: int
    total_user_stories: int
    batch_size: int
    model: str
    failed_batches: List[str] = Field(default_factory=list)
    total_batches: int
    successful_batches: int


class UserStoriesOutput(BaseModel):
    """Complete output model."""
    user_stories: List[UserStory]
    metadata: OutputMetadata