# schemas.py
from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

# ------------------------------
# User / Auth Schemas (UNCHANGED)
# ------------------------------
class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

# ------------------------------
# Project Schemas (UNCHANGED)
# ------------------------------
class CreateProjectRequest(BaseModel):
    title: str
    description: str

class ProjectResponse(BaseModel):
    project_id: str
    title: str
    description: str
    created_at: datetime

# ------------------------------
# Enums for consistency
# ------------------------------
class RequirementType(str, Enum):
    FUNCTIONAL = "functional"
    NON_FUNCTIONAL = "non_functional"

class RequirementPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class RequirementStatus(str, Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    MODIFIED = "modified"

# ------------------------------
# SRS Document Schemas
# ------------------------------
class SRSSection(BaseModel):
    """Non-feature sections (1, 2, 3, 5, etc.)"""
    content: List[str]  # Array of text paragraphs

class Feature(BaseModel):
    """Feature from Section 4"""
    feature_id: str  # e.g., "FEAT-001"
    description: str
    functional_overview: List[str]
    order: int  # Display order

class CreateSRSRequest(BaseModel):
    """Request to create SRS from parsed JSON"""
    project_id: str
    srs_text: str  # Raw SRS text to be parsed
    system_name: str

class SRSDocumentResponse(BaseModel):
    """Response with SRS document info"""
    srs_id: str
    project_id: str
    title: str
    version: str
    created_at: datetime
    updated_at: datetime
    total_features: int
    total_requirements: int

# ------------------------------
# Requirement Schemas (UPDATED)
# ------------------------------
class RequirementBase(BaseModel):
    text: str
    type: RequirementType = RequirementType.FUNCTIONAL
    subtype: Optional[str] = "general"  # e.g., Performance, Security, UI
    priority: RequirementPriority = RequirementPriority.MEDIUM
    status: RequirementStatus = RequirementStatus.ACTIVE
    
    @field_validator('type', mode='before')
    @classmethod
    def normalize_type(cls, v):
        """Normalize requirement type: convert case-insensitive and replace hyphens with underscores"""
        if isinstance(v, str):
            # Convert to lowercase and replace hyphens with underscores
            normalized = v.lower().replace('-', '_').replace(' ', '_')
            # Map common variations to enum values
            if normalized in ['functional', 'fr']:
                return RequirementType.FUNCTIONAL
            elif normalized in ['non_functional', 'nfr', 'non functional']:
                return RequirementType.NON_FUNCTIONAL
        return v

class CreateRequirementRequest(RequirementBase):
    project_id: str
    id: str  # Changed from int to str for more flexible IDs like "REQ-001"
    req_id: str  # Changed to string: "REQ-001" (more standard than int)
    feature_id: Optional[str] = None  # Link to feature if applicable
    feature_name: Optional[str] = None
    
    @field_validator('req_id', mode='before')
    @classmethod
    def convert_req_id_to_str(cls, v):
        """Convert req_id to string if it's an integer"""
        if isinstance(v, int):
            return str(v)
        return v

class RequirementResponse(RequirementBase):
    requirement_id: str  # MongoDB _id
    project_id: str
    req_id: str
    feature_id: Optional[str] = None
    feature_name: Optional[str] = None
    version: int
    created_at: datetime
    updated_at: datetime

class UpdateRequirementRequest(BaseModel):
    """Use when user edits a requirement"""
    req_id: str  # Changed to string
    new_text: str
    change_reason: Optional[str] = None
    
    @field_validator('req_id', mode='before')
    @classmethod
    def convert_req_id_to_str(cls, v):
        """Convert req_id to string if it's an integer"""
        if isinstance(v, int):
            return str(v)
        return v

class BulkCreateRequirementsRequest(BaseModel):
    requirements: List[CreateRequirementRequest]

class RequirementHistoryEntry(BaseModel):
    """Single history entry for a requirement"""
    version: int
    text: str
    updated_at: datetime
    change_reason: Optional[str] = None

class RequirementWithHistory(RequirementResponse):
    """Requirement with full change history"""
    change_history: List[RequirementHistoryEntry]



# user srs template schema
class SubSection(BaseModel):
    id: str
    heading: str

class Section(BaseModel):
    id: str
    heading: str
    sub: List[SubSection] = []

class TemplateCreate(BaseModel):
    name: str
    format: str
    sections: List[Section]
    fontStyle: str
    fontSizes: dict


# ------------------------------
# template linking schema
# ------------------------------
class LinkTemplateRequest(BaseModel):
    template_id: str
    project_id: str



# ------------------------------
# Generic / Chat Schemas
# ------------------------------
class ProcessRequest(BaseModel):
    message: str

class DocumentUploadRequest(BaseModel):
    project_id: str
    document_name: str
    content: str


# ── Schemas ────────────────────────────────────────────────────────────────

class TitlePageResponse(BaseModel):
    title:   str
    version: str
    date:    str
    org:     str = ""
    author:  str
    
class TitlePageUpdate(BaseModel):
    title:   str | None = None
    version: str | None = None
    date:    str | None = None
    org:     str | None = None