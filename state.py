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


def stories_to_markdown(stories: List[Story]) -> str:
    """
    Serialize a list of Story objects to markdown format.

    Args:
        stories: List of Story objects to serialize

    Returns:
        Markdown string representation of stories
    """
    lines = []
    for story in stories:
        # Story header
        lines.append(f"## Story {story.id}: {story.name}")
        lines.append(f"**Sequence:** {story.sequence_order}")

        # Dependencies
        if story.depends_on:
            deps = ", ".join(story.depends_on)
            lines.append(f"**Depends On:** {deps}")
        else:
            lines.append("**Depends On:** none")

        # Tech suggestions
        if story.tech_suggestions:
            tech_str = ", ".join([f"{k}={v}" for k, v in story.tech_suggestions.items()])
            lines.append(f"**Tech:** {tech_str}")

        # LLM Prompt section
        lines.append("")
        lines.append("### LLM Prompt")
        lines.append(story.llm_prompt)

        # Success Criteria section
        lines.append("")
        lines.append("### Success Criteria")
        if story.success_criteria:
            for criterion in story.success_criteria:
                lines.append(f"- {criterion}")
        else:
            lines.append("- No criteria specified")

        # Section divider
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def stories_from_markdown(md: str) -> List[Story]:
    """
    Deserialize stories from markdown format back to Story objects.

    Args:
        md: Markdown string containing serialized stories

    Returns:
        List of Story objects
    """
    stories = []

    # Split by story headers (## Story ID: Name)
    import re
    story_blocks = re.split(r"^## Story ", md, flags=re.MULTILINE)

    # First element is empty or preamble, skip it
    for block in story_blocks[1:]:
        if not block.strip():
            continue

        lines = block.split("\n")

        # Parse header (first line has "ID: Name")
        header_line = lines[0]
        match = re.match(r"([^:]+):\s*(.*)", header_line)
        if not match:
            continue

        story_id = match.group(1).strip()
        story_name = match.group(2).strip()

        # Initialize story data
        story_data = {
            "id": story_id,
            "name": story_name,
            "description": "",
            "llm_prompt": "",
            "success_criteria": [],
            "tech_suggestions": {},
            "depends_on": [],
            "sequence_order": 0
        }

        # Parse remaining metadata and sections
        current_section = None
        section_content = []

        for line in lines[1:]:
            line_stripped = line.strip()

            # Check for metadata lines (with ** markdown bold markers)
            if line_stripped.startswith("**Sequence:**"):
                try:
                    value_str = line_stripped.replace("**Sequence:**", "").strip()
                    story_data["sequence_order"] = int(value_str)
                except ValueError:
                    pass

            elif line_stripped.startswith("**Depends On:**"):
                value_str = line_stripped.replace("**Depends On:**", "").strip()
                if value_str.lower() != "none":
                    story_data["depends_on"] = [d.strip() for d in value_str.split(",")]
                else:
                    story_data["depends_on"] = []

            elif line_stripped.startswith("**Tech:**"):
                tech_str = line_stripped.replace("**Tech:**", "").strip()
                # Parse tech_suggestions as key=value pairs
                for pair in tech_str.split(","):
                    pair = pair.strip()
                    if "=" in pair:
                        k, v = pair.split("=", 1)
                        story_data["tech_suggestions"][k.strip()] = v.strip()

            # Check for section headers
            elif line_stripped.startswith("### LLM Prompt"):
                if current_section and section_content:
                    _store_section(story_data, current_section, section_content)
                current_section = "llm_prompt"
                section_content = []

            elif line_stripped.startswith("### Success Criteria"):
                if current_section and section_content:
                    _store_section(story_data, current_section, section_content)
                current_section = "success_criteria"
                section_content = []

            elif line_stripped == "---":
                if current_section and section_content:
                    _store_section(story_data, current_section, section_content)
                break

            # Accumulate section content (only if not a metadata line)
            elif current_section and line.strip() and not line_stripped.startswith("**"):
                section_content.append(line)

        # Store final section if exists
        if current_section and section_content:
            _store_section(story_data, current_section, section_content)

        # Create Story object
        try:
            story = Story(**story_data)
            stories.append(story)
        except Exception:
            # Skip malformed stories
            continue

    return stories


def _store_section(story_data: dict, section: str, content: List[str]) -> None:
    """
    Helper to store parsed section content into story_data dict.

    Args:
        story_data: Dict to update
        section: Section name ("llm_prompt" or "success_criteria")
        content: List of content lines from the section
    """
    if section == "llm_prompt":
        story_data["llm_prompt"] = "\n".join(content).strip()
    elif section == "success_criteria":
        # Parse bullet points
        criteria = []
        for line in content:
            line = line.strip()
            if line.startswith("- "):
                criteria.append(line[2:].strip())
            elif line and not line.startswith("#"):
                # Add non-empty lines that aren't headers
                if criteria and line:
                    criteria[-1] += " " + line
        # Filter out placeholder and empty strings
        story_data["success_criteria"] = [
            c for c in criteria
            if c and c != "No criteria specified"
        ]
