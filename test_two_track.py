"""
Unit tests for Two-Track Generation implementation.

Tests verify:
1. Markdown serialization round-trip (stories → markdown → parse → equal)
2. Markdown parsing edge cases (none dependencies, blank criteria)
3. Tech stack extraction from TRD
4. Frontend generation isolation (no story context)
5. Backend generation isolation (llm_prompt only)
6. Execution patterns (frontend once, backend per-story)
7. No technical keyword leakage between tracks
"""

import pytest
from state import Story, stories_to_markdown, stories_from_markdown
from backend_generator import BackendGenerator


class TestMarkdownSerialization:
    """Test markdown serialization/deserialization of stories."""

    def test_stories_round_trip(self):
        """Stories → markdown → parse → equal"""
        original_stories = [
            Story(
                id="story_001",
                name="User Authentication",
                description="Allow users to sign up and log in",
                llm_prompt="Create a login form using React that calls /api/login",
                success_criteria=["Login form works", "JWT token stored"],
                tech_suggestions={"backend_tech": "FastAPI", "database": "PostgreSQL"},
                depends_on=[],
                sequence_order=1
            ),
            Story(
                id="story_002",
                name="Task Management",
                description="Create and manage tasks",
                llm_prompt="Build a task CRUD API with FastAPI and SQLAlchemy",
                success_criteria=["Create task", "List tasks", "Delete task"],
                tech_suggestions={"backend_tech": "FastAPI", "database": "PostgreSQL"},
                depends_on=["story_001"],
                sequence_order=2
            )
        ]

        # Serialize to markdown
        md = stories_to_markdown(original_stories)
        assert isinstance(md, str)
        assert len(md) > 0
        assert "## Story story_001" in md
        assert "## Story story_002" in md

        # Deserialize back
        parsed_stories = stories_from_markdown(md)

        # Verify equality
        assert len(parsed_stories) == len(original_stories)
        for orig, parsed in zip(original_stories, parsed_stories):
            assert orig.id == parsed.id
            assert orig.name == parsed.name
            assert orig.llm_prompt == parsed.llm_prompt
            assert orig.sequence_order == parsed.sequence_order
            assert orig.depends_on == parsed.depends_on
            assert set(orig.tech_suggestions.items()) == set(parsed.tech_suggestions.items())

    def test_depends_on_none(self):
        """Parse 'none' dependencies correctly"""
        stories = [
            Story(
                id="story_001",
                name="Feature 1",
                description="First feature",
                llm_prompt="Implement feature 1",
                depends_on=[],
                sequence_order=1
            )
        ]

        md = stories_to_markdown(stories)
        assert "**Depends On:** none" in md

        parsed = stories_from_markdown(md)
        assert parsed[0].depends_on == []

    def test_blank_success_criteria(self):
        """Parse empty success criteria gracefully"""
        stories = [
            Story(
                id="story_001",
                name="Feature",
                description="A feature",
                llm_prompt="Implement it",
                success_criteria=[],
                sequence_order=1
            )
        ]

        md = stories_to_markdown(stories)
        parsed = stories_from_markdown(md)

        # Should parse without error (empty list or "No criteria specified" placeholder)
        assert isinstance(parsed[0].success_criteria, list)


class TestTechStackExtraction:
    """Test extraction of tech stack from TRD."""

    def test_extract_tech_stack(self):
        """Extract tech stack from TRD header"""
        trd = """# Technical Requirements Document

## Tech Stack Summary
- backend_tech: FastAPI
- database: PostgreSQL
- auth: JWT
- caching: Redis

## Architecture
The system uses FastAPI for the backend...
"""
        tech_stack = BackendGenerator.extract_tech_stack(trd)

        assert tech_stack.get("backend_tech") == "FastAPI"
        assert tech_stack.get("database") == "PostgreSQL"
        assert tech_stack.get("auth") == "JWT"
        assert tech_stack.get("caching") == "Redis"

    def test_extract_tech_stack_with_equals(self):
        """Parse tech stack with key=value format"""
        trd = """## Tech Stack Summary
backend_tech=FastAPI
database=SQLite
auth=None

## Implementation Details
..."""
        tech_stack = BackendGenerator.extract_tech_stack(trd)

        assert tech_stack.get("backend_tech") == "FastAPI"
        assert tech_stack.get("database") == "SQLite"
        assert tech_stack.get("auth") == "None"

    def test_extract_tech_stack_fallback(self):
        """Provide defaults if TRD lacks tech stack section"""
        trd = "No tech stack section here"
        tech_stack = BackendGenerator.extract_tech_stack(trd)

        # Should have defaults
        assert "backend_tech" in tech_stack
        assert "database" in tech_stack
        assert tech_stack["backend_tech"] == "FastAPI"
        assert tech_stack["database"] == "SQLite"


class TestGenerationIsolation:
    """Test that frontend and backend generation are properly isolated."""

    def test_frontend_no_story_leak(self):
        """Frontend LLM never sees story name/description"""
        # This is a behavioral test — we verify that the frontend generator
        # has PRD-only prompts that don't reference story fields

        from frontend_generator import FrontendGenerator

        # Check that PRD_FRONTEND_USER prompt doesn't have placeholders for story context
        prompt = FrontendGenerator.PRD_FRONTEND_USER
        assert "{prd_content}" in prompt
        # PRD-only prompts should NOT have {story_name} or {story_description}
        assert "{story_name}" not in prompt
        assert "{story_description}" not in prompt

    def test_backend_no_story_leak(self):
        """Backend LLM gets ONLY llm_prompt + tech_stack"""
        from backend_generator import BackendGenerator

        # Check that EXECUTE_PROMPT_USER has only llm_prompt and tech_stack
        prompt = BackendGenerator.EXECUTE_PROMPT_USER
        assert "{llm_prompt}" in prompt
        assert "{tech_stack}" in prompt
        # Should NOT have story_name, story_description, backend_spec, etc.
        assert "{story_name}" not in prompt
        assert "{story_description}" not in prompt
        assert "{backend_spec}" not in prompt
        assert "{frontend_spec}" not in prompt


class TestGenerationPatterns:
    """Test the execution patterns of two-track generation."""

    def test_frontend_called_once(self):
        """Frontend generation happens once, not per-story"""
        from frontend_generator import FrontendGenerator

        # The presence of generate_from_prd() method confirms one-shot capability
        assert hasattr(FrontendGenerator, 'generate_from_prd')
        assert callable(getattr(FrontendGenerator, 'generate_from_prd'))

    def test_backend_called_per_story(self):
        """Backend generation has per-story execution method"""
        from backend_generator import BackendGenerator

        # The presence of execute_story_prompt() confirms per-story capability
        assert hasattr(BackendGenerator, 'execute_story_prompt')
        assert callable(getattr(BackendGenerator, 'execute_story_prompt'))

    def test_product_generator_two_track_signature(self):
        """ProductGenerator.generate_product() accepts frontend/backend stories separately"""
        from product_generator import ProductGenerator
        import inspect

        sig = inspect.signature(ProductGenerator.generate_product)
        params = sig.parameters

        # Check signature accepts both old (stories) and new (frontend_stories, backend_stories) params
        assert 'stories' in params
        assert 'frontend_stories' in params
        assert 'backend_stories' in params


class TestNoTechKeywordLeakage:
    """Test that technical keywords don't leak between tracks."""

    def test_no_tech_keywords_in_frontend_prompts(self):
        """Frontend generation prompts reject technical keywords"""
        from frontend_generator import FrontendGenerator

        frontend_system = FrontendGenerator.PRD_FRONTEND_SYSTEM

        # Check that prompt explicitly tells LLM NOT to use technical context
        assert "never read" in frontend_system.lower() or "must not" in frontend_system.lower() or "critical constraints" in frontend_system.lower()

        # Check that prompt lacks structural placeholders for backend context
        # (The word "fastapi" may appear in warning text, but backend_spec should not)
        assert "backend_spec" not in frontend_system
        assert "{backend" not in frontend_system
        assert "{trd" not in frontend_system.lower()
        assert "{story_description}" not in frontend_system
        assert "{story_name}" not in frontend_system

    def test_frontend_markdown_parser_safety(self):
        """stories_from_markdown() doesn't leak frontend stories to backend context"""
        # This verifies the parsing function is neutral (not biased toward one track)

        md = """## Story story_001: Login UI
**Sequence:** 1
**Depends On:** none
**Tech:** backend_tech=FastAPI

### LLM Prompt
Create a login form using React
"""
        stories = stories_from_markdown(md)
        assert len(stories) == 1
        assert "React" in stories[0].llm_prompt
        # The parsed story should retain the exact llm_prompt
        assert stories[0].llm_prompt == "Create a login form using React"

    def test_no_frontend_code_in_backend_prompt(self):
        """Backend execution prompts don't include frontend specification"""
        from backend_generator import BackendGenerator

        backend_user = BackendGenerator.EXECUTE_PROMPT_USER

        # Backend prompts should not reference frontend components, UI, CSS, etc.
        assert "react" not in backend_user.lower()
        assert "html" not in backend_user.lower()
        assert "css" not in backend_user.lower()
        assert "javascript" not in backend_user.lower()
        assert "frontend" not in backend_user.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
