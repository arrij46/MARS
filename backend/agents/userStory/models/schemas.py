"""
Data models and schemas for the MARS User Story Generation Pipeline.

This module defines all Pydantic models used for input/output validation
and data structure throughout the pipeline.
"""
from typing import List
from pydantic import BaseModel, Field, field_validator


class Requirement(BaseModel):
    """
    Single requirement model.
    
    Attributes:
        id: Unique requirement identifier (e.g., "R1")
        type: Requirement type ("FR" for Functional, "NFR" for Non-Functional)
        text: Requirement text description
    """
    id: str = Field(..., description="Requirement identifier")
    type: str = Field(..., description="Requirement type (FR or NFR)")
    text: str = Field(..., description="Requirement text")
    
    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate requirement type is FR or NFR."""
        if v.upper() not in ["FR", "NFR"]:
            raise ValueError(f"Requirement type must be 'FR' or 'NFR', got '{v}'")
        return v.upper()
    
    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate requirement ID is not empty."""
        if not v or not v.strip():
            raise ValueError("Requirement ID cannot be empty")
        return v.strip()
    
    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        """Validate requirement text is not empty."""
        if not v or not v.strip():
            raise ValueError("Requirement text cannot be empty")
        return v.strip()


class RequirementsInput(BaseModel):
    """
    Input model for requirements JSON file.
    
    Attributes:
        requirements: List of requirements
    """
    requirements: List[Requirement] = Field(..., min_length=1)


class UserStory(BaseModel):
    """
    Generated user story model.
    
    Attributes:
        requirement_id: ID of the source requirement
        user_story_id: Unique user story identifier (e.g., "R1-US1")
        type: Requirement type (inherited from requirement)
        text: User story text in format "As a <role>, I want <action>, so that <benefit>"
    """
    requirement_id: str = Field(..., description="Source requirement ID")
    user_story_id: str = Field(..., description="User story identifier")
    type: str = Field(..., description="Requirement type (FR or NFR)")
    text: str = Field(..., description="User story text")
    
    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        """Validate user story text follows standard format."""
        if not v or not v.strip():
            raise ValueError("User story text cannot be empty")
        v = v.strip()
        # Basic validation: should contain "As a", "I want", "so that"
        if "as a" not in v.lower() or "i want" not in v.lower():
            raise ValueError(
                "User story must follow format: 'As a <role>, I want <action>, so that <benefit>'"
            )
        return v


class OutputMetadata(BaseModel):
    """
    Metadata for output JSON file.
    
    Attributes:
        total_requirements: Total number of input requirements
        total_user_stories: Total number of generated user stories
        batch_size: Average batch size used
        model: GPT model used for generation
        failed_batches: List of batch IDs that failed (if graceful fallback enabled)
        total_batches: Total number of batches processed
        successful_batches: Number of successfully processed batches
    """
    total_requirements: int = Field(..., ge=0)
    total_user_stories: int = Field(..., ge=0)
    batch_size: int = Field(..., ge=0)
    model: str = Field(..., description="GPT model identifier")
    failed_batches: List[str] = Field(default_factory=list, description="Batch IDs that failed")
    total_batches: int = Field(default=0, ge=0)
    successful_batches: int = Field(default=0, ge=0)


class UserStoriesOutput(BaseModel):
    """
    Output model for user stories JSON file.
    
    Attributes:
        user_stories: List of generated user stories
        metadata: Output metadata
    """
    user_stories: List[UserStory]
    metadata: OutputMetadata


class RequirementBatch(BaseModel):
    """
    Batch of requirements for processing.
    
    Attributes:
        batch_id: Unique batch identifier
        type: Batch type (FR or NFR)
        requirements: List of requirements in this batch
        estimated_tokens: Estimated token count for this batch
    """
    batch_id: str = Field(..., description="Batch identifier")
    type: str = Field(..., description="Batch type (FR or NFR)")
    requirements: List[Requirement] = Field(..., min_length=1)
    estimated_tokens: int = Field(..., ge=0, description="Estimated token count")

