"""
Module 1: Global State Management
Core schema for the multi-agent SDLC system using Pydantic.
"""

from datetime import datetime
from typing import ClassVar, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class Story(BaseModel):
    """
    Represents a user story with embedded LLM prompt for code generators.
    Each story is self-contained with all information needed to generate code.
    """
    id: str = Field(..., description="Unique story identifier")
    name: str = Field(..., description="Story name/title")
    description: str = Field(..., description="Story description and context")
    llm_prompt: str = Field(..., description="Explicit LLM prompt for code generator (what to build)")
    success_criteria: List[str] = Field(default_factory=list, description="How to validate the story")
    tech_suggestions: Dict[str, str] = Field(default_factory=dict, description="Tech stack hints from TRD (e.g., backend_tech, frontend_tech, database)")
    depends_on: List[str] = Field(default_factory=list, description="IDs of stories this depends on")
    sequence_order: int = Field(default=0, description="Execution order for sequential building")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "story_001",
                "name": "User Authentication",
                "description": "Allow users to sign up and log in",
                "llm_prompt": "Create a user authentication system with login/signup forms using FastAPI backend and React frontend. Use JWT tokens for session management.",
                "success_criteria": ["Login form works", "User data persisted", "JWT tokens valid"],
                "tech_suggestions": {"backend_tech": "FastAPI", "frontend_tech": "React", "database": "PostgreSQL"},
                "depends_on": [],
                "sequence_order": 1
            }
        }
    )


class CritiqueEntry(BaseModel):
    """Represents a critique or feedback entry from an agent."""
    agent_name: str = Field(..., description="Name of the agent providing feedback")
    feedback: str = Field(..., description="The critique or feedback content")
    timestamp: datetime = Field(default_factory=datetime.now, description="When the critique was made")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "agent_name": "architect-agent",
                "feedback": "The API design lacks proper error handling",
                "timestamp": "2026-05-02T10:30:00"
            }
        }
    )


class Document(BaseModel):
    """Represents a project document with versioning and critique tracking."""
    content: str = Field(..., description="The document content")
    version: int = Field(..., ge=1, description="Document version number")
    critiques: List[CritiqueEntry] = Field(default_factory=list, description="List of critiques")
    status: str = Field(default="draft", description="Document status (draft, approved, stale, archived)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "content": "## Business Requirements Document\n\n1. User authentication...\n",
                "version": 1,
                "critiques": [],
                "status": "draft"
            }
        }
    )

    def add_critique(self, agent_name: str, feedback: str) -> None:
        """Add a new critique to the document."""
        self.critiques.append(CritiqueEntry(
            agent_name=agent_name,
            feedback=feedback,
            timestamp=datetime.now()
        ))

    def increment_version(self) -> None:
        """Increment the document version."""
        self.version += 1


class ProjectState(BaseModel):
    """
    Central state management for the entire project.
    Tracks all documents, stories, codebase, and execution history.
    """
    project_id: str = Field(..., description="Unique identifier for the project")
    rough_idea: str = Field(..., description="Initial project idea or description")
    current_phase: str = Field(default="IDEA", description="Current development phase")
    docs: Dict[str, Document] = Field(default_factory=dict, description="Project documents keyed by type")
    stories: List[Story] = Field(default_factory=list, description="User stories with embedded code generation prompts")
    codebase: Dict[str, str] = Field(default_factory=dict, description="File paths and their contents")
    history: List[Dict] = Field(default_factory=list, description="Event log for audit trail")

    # Document type constants
    BRD: ClassVar[str] = "BRD"  # Business Requirements Document
    PRD: ClassVar[str] = "PRD"  # Product Requirements Document
    TRD: ClassVar[str] = "TRD"  # Technical Requirements Document

    # Phase constants
    IDEA: ClassVar[str] = "IDEA"
    DESIGN: ClassVar[str] = "DESIGN"
    IMPLEMENTATION: ClassVar[str] = "IMPLEMENTATION"
    TESTING: ClassVar[str] = "TESTING"
    DEPLOYMENT: ClassVar[str] = "DEPLOYMENT"

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "project_id": "proj_abc123",
                "rough_idea": "Build a task management API",
                "current_phase": "IDEA",
                "docs": {},
                "stories": [],
                "codebase": {},
                "history": []
            }
        }
    )

    def add_event(self, event_type: str, details: Dict) -> None:
        """Log an event to the history."""
        self.history.append({
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "details": details
        })

    def get_document(self, doc_type: str) -> Optional[Document]:
        """Retrieve a document by type."""
        return self.docs.get(doc_type)

    def set_document(self, doc_type: str, document: Document) -> None:
        """Set a document in the state."""
        self.docs[doc_type] = document
        self.add_event("document_updated", {"doc_type": doc_type, "version": document.version})

    def demote(self, target_phase: str, reason: str) -> None:
        """
        Demote the current phase and flag subsequent documents as stale.

        Args:
            target_phase: The phase to demote to (must be BRD, PRD, TRD, or STORIES)
            reason: Explanation for the demotion
        """
        # Map phase types to order
        phase_order = ["BRD", "PRD", "TRD", "STORIES", "IMPLEMENTATION"]

        if target_phase not in phase_order:
            raise ValueError(f"Invalid target_phase. Must be one of: {phase_order}")

        current_idx = phase_order.index(self.current_phase) if self.current_phase in phase_order else -1
        target_idx = phase_order.index(target_phase)

        if current_idx < 0:
            current_idx = 0  # IDEA phase is before BRD

        if target_idx > current_idx:
            raise ValueError(f"Cannot demote from {self.current_phase} to {target_phase}")

        # Flag all documents created after the target phase as stale
        for doc_type, doc in self.docs.items():
            doc_idx = phase_order.index(doc_type) if doc_type in phase_order else -1
            if doc_idx > target_idx:
                doc.status = "stale"
                doc.increment_version()
        
        # Update current phase
        old_phase = self.current_phase
        self.current_phase = target_phase
        
        self.add_event("phase_demoted", {
            "from": old_phase,
            "to": target_phase,
            "reason": reason
        })

    def to_json(self) -> str:
        """Serialize state to JSON string."""
        return self.model_dump_json()

    @classmethod
    def from_json(cls, json_str: str) -> "ProjectState":
        """Deserialize JSON string to ProjectState."""
        return cls.model_validate_json(json_str)
