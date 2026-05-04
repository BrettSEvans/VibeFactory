"""
Module 6: Backend Generator
Generates FastAPI backend code from BackendSpec specifications.
Uses Claude to write production-quality Python code.
"""

import json
import re
from typing import Dict, Optional, Tuple
import instructor
import litellm
from pydantic import BaseModel, Field
from story_translator import BackendSpec, DatabaseModel, APIEndpoint, HTTPMethod


class GeneratedBackendCode(BaseModel):
    """Response from backend code generation."""
    models_py: str = Field(..., description="SQLAlchemy models.py code")
    main_py_endpoints: str = Field(..., description="FastAPI endpoint implementations")
    conftest_py: str = Field(..., description="Pytest configuration for tests")
    test_routes_py: str = Field(..., description="Test cases for all endpoints")
    requirements_txt: str = Field(..., description="Python package requirements")


class BackendGeneratorConfig(BaseModel):
    """Configuration for the backend generator."""
    llm_model: str = Field(
        default="meta-llama/llama-3.3-70b-instruct:free",
        description="LLM model to use"
    )
    api_key: Optional[str] = Field(default=None, description="API key for LLM")


class BackendGenerator:
    """
    Generates FastAPI backend code from BackendSpec.
    Creates models, endpoints, tests, and requirements.
    """

    SYSTEM_PROMPT = """You are a Senior Python Backend Developer specializing in FastAPI.
Your task is to generate production-quality code that:
- Uses SQLAlchemy for ORM with SQLite
- Implements RESTful API design principles
- Includes comprehensive pytest test coverage
- Has proper error handling and validation with Pydantic
- Follows PEP 8 style guidelines
- Uses dependency injection patterns

CRITICAL SECURITY REQUIREMENTS:
- SQL injection prevention (use SQLAlchemy ORM, never raw SQL)
- Input validation with Pydantic models
- Proper HTTP status codes
- CORS handling for frontend integration
- No hardcoded secrets or credentials

PRODUCTION CODE STANDARDS:
- Type hints on all functions
- Docstrings for all classes and functions
- Error handling for database operations
- Pagination support for list endpoints
- Proper logging setup
- No print() statements, use logging instead

Generate complete, runnable code that can be dropped into a FastAPI project."""

    USER_PROMPT_TEMPLATE = """Generate FastAPI backend code for this story:

STORY: {story_name}
DESCRIPTION: {story_description}

PRODUCT CONTEXT (use this to match complexity and domain to the actual product):
PRD Summary: {prd_context}
TRD Summary: {trd_context}

BACKEND SPECIFICATION:
{backend_spec}

Generate the following code files:

1. models.py
   - SQLAlchemy ORM models
   - Pydantic schemas for request/response
   - Proper relationships and foreign keys
   - Database constraints

2. endpoint implementations
   - FastAPI route handlers
   - Proper dependency injection
   - Request/response validation
   - Error handling

3. conftest.py
   - Pytest fixtures (test_client, test_db)
   - Database session setup for testing
   - Cleanup after tests

4. test_routes.py
   - Unit tests for all endpoints
   - Tests for success and error cases
   - Database transaction isolation
   - At least 80% code coverage

5. requirements.txt additions
   - Only new packages needed (fastapi, sqlalchemy, etc. are baseline)
   - Pin versions for reproducibility

Return valid JSON with keys: models_py, main_py_endpoints, conftest_py, test_routes_py, requirements_txt"""

    EXECUTE_PROMPT_SYSTEM = """You are a Senior Python Backend Developer specializing in FastAPI.
Your task is to generate production-quality code that directly implements the provided llm_prompt.

CRITICAL CONSTRAINTS:
- You ONLY read the llm_prompt — this is the explicit code generation instruction
- Do NOT invent features beyond what's specified in the llm_prompt
- Do NOT add unnecessary technical sophistication
- Follow the llm_prompt EXACTLY as written

PRODUCTION CODE STANDARDS:
- SQLAlchemy ORM with SQLite (no raw SQL)
- RESTful API design with proper HTTP methods and status codes
- Pydantic for request/response validation
- Type hints on all functions
- Comprehensive pytest test coverage (80%+ code coverage)
- Proper error handling and logging
- No hardcoded secrets or credentials
- CORS support for frontend integration

OUTPUT: Generate complete, runnable FastAPI code with:
1. SQLAlchemy ORM models (models.py)
2. FastAPI endpoint implementations
3. Pytest fixtures and test suite
4. Updated requirements.txt

Return valid JSON with these exact keys: models_py, main_py_endpoints, conftest_py, test_routes_py, requirements_txt"""

    EXECUTE_PROMPT_USER = """Implement this feature exactly as specified in the LLM Prompt below.

EXPLICIT CODE GENERATION PROMPT:
{llm_prompt}

TECHNOLOGY STACK:
{tech_stack}

IMPLEMENTATION REQUIREMENTS:
1. Follow the llm_prompt instructions EXACTLY
2. Use the specified tech stack (database, backend framework, etc.)
3. Generate complete, production-ready code
4. Include comprehensive test coverage
5. Provide all dependencies in requirements.txt

Generate FastAPI backend code with:
- models.py: SQLAlchemy ORM models
- endpoint implementations: FastAPI route handlers
- conftest.py: Pytest fixtures and configuration
- test_routes.py: Test suite with 80%+ coverage
- requirements.txt: All Python package dependencies

Return valid JSON with keys: models_py, main_py_endpoints, conftest_py, test_routes_py, requirements_txt"""

    def __init__(self, config: Optional[BackendGeneratorConfig] = None):
        """Initialize the backend generator."""
        self.config = config or BackendGeneratorConfig()
        self.client = instructor.from_litellm(litellm.completion)
        self.api_key = self.config.api_key

    def generate_code(
        self,
        backend_spec: BackendSpec,
        context_docs: Optional[Dict[str, str]] = None
    ) -> GeneratedBackendCode:
        """
        Generate backend code from a BackendSpec.
        Tries LLM first, falls back to deterministic generators if LLM fails.

        Args:
            backend_spec: The backend specification to generate code from
            context_docs: Optional PRD/TRD context for product-aware generation

        Returns:
            GeneratedBackendCode with all source files
        """
        context_docs = context_docs or {}
        try:
            # Try LLM-based generation first
            spec_json = json.dumps(backend_spec.to_dict(), indent=2)
            # Extract PRD/TRD summaries (truncated to avoid token bloat)
            prd_context = (context_docs.get("PRD", context_docs.get("prd", "")) or "Not available")[:800]
            trd_context = (context_docs.get("TRD", context_docs.get("trd", "")) or "Not available")[:800]
            user_prompt = self.USER_PROMPT_TEMPLATE.format(
                story_name=backend_spec.story_name,
                story_description=backend_spec.description,
                prd_context=prd_context,
                trd_context=trd_context,
                backend_spec=spec_json,
            )

            response = self.client.create(
                model=self.config.llm_model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_model=GeneratedBackendCode,
                api_key=self.api_key,
                max_retries=1,
            )
            return response
        except Exception as e:
            # Fallback to deterministic code generation
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"⚠ LLM generation failed ({type(e).__name__}: {str(e)[:100]}), using fallback generators")
            print(f"⚠ LLM generation failed ({type(e).__name__}), using fallback generators")

            # Generate conftest and test files
            test_code = self.generate_test_code(backend_spec)

            # Split into conftest and test_routes
            conftest_py = """import pytest
from httpx import AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from models import Base
from database import get_db

# Test database setup
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture
def test_client():
    return AsyncClient(app=app, base_url="http://test")

@pytest.fixture
def test_db():
    Base.metadata.create_all(bind=engine)
    yield TestingSessionLocal()
    Base.metadata.drop_all(bind=engine)
"""

            # Extract test functions
            test_routes_py = test_code

            return GeneratedBackendCode(
                models_py=self.generate_models_code(backend_spec),
                main_py_endpoints=self.generate_endpoint_code(backend_spec),
                conftest_py=conftest_py,
                test_routes_py=test_routes_py,
                requirements_txt=self.generate_requirements(backend_spec),
            )

    def execute_story_prompt(
        self,
        llm_prompt: str,
        tech_stack: Dict[str, str],
        max_retries: int = 3,
        timeout_seconds: int = 90
    ) -> GeneratedBackendCode:
        """
        Execute a story's embedded LLM prompt for code generation.
        TRACK 2: Per-story backend generation, llm_prompt-only context.

        Args:
            llm_prompt: Explicit code generation instruction from story
            tech_stack: Dict of technology choices (backend_tech, database, auth, etc.)
            max_retries: Maximum retry attempts for rate limits
            timeout_seconds: LLM request timeout

        Returns:
            GeneratedBackendCode with all backend files
        """
        import time
        import logging
        logger = logging.getLogger(__name__)

        for attempt in range(max_retries):
            try:
                # Format tech stack as readable string
                tech_str = "\n".join([f"- {k}: {v}" for k, v in tech_stack.items()])

                user_prompt = self.EXECUTE_PROMPT_USER.format(
                    llm_prompt=llm_prompt,
                    tech_stack=tech_str
                )

                completion_kwargs = {
                    "model": self.config.llm_model,
                    "messages": [
                        {"role": "system", "content": self.EXECUTE_PROMPT_SYSTEM},
                        {"role": "user", "content": user_prompt},
                    ],
                    "response_model": GeneratedBackendCode,
                    "api_key": self.api_key,
                    "timeout": timeout_seconds,
                    "max_retries": 0,  # Manual retries with exponential backoff
                }

                logger.info(f"Story prompt execution attempt {attempt + 1}/{max_retries}")
                response = self.client.create(**completion_kwargs)
                return response

            except Exception as e:
                error_str = str(e)
                is_rate_limit = "429" in error_str or "rate" in error_str.lower() or "quota" in error_str.lower()
                is_timeout = "timeout" in error_str.lower() or "deadline" in error_str.lower()

                if attempt < max_retries - 1:
                    if is_rate_limit:
                        wait_time = [20, 60][min(attempt, 1)]
                    elif is_timeout:
                        wait_time = [10, 30][min(attempt, 1)]
                    else:
                        wait_time = [15, 45][min(attempt, 1)]

                    logger.warning(f"⚠ Story prompt LLM attempt {attempt + 1} failed ({type(e).__name__}). "
                                 f"Retrying in {wait_time}s...")
                    print(f"⚠ Story prompt execution attempt {attempt + 1} failed. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.warning(f"⚠ Story prompt LLM failed after {max_retries} attempts, using fallback")
                    print(f"⚠ Story prompt execution failed after {max_retries} attempts, using fallback")

        # Fallback: Generate minimal code structure
        fallback_code = self.generate_test_code(
            type('MinimalSpec', (), {
                'endpoints': [],
                'models': [],
                'dependencies': []
            })()
        )

        return GeneratedBackendCode(
            models_py="# Fallback models\nfrom sqlalchemy.ext.declarative import declarative_base\nBase = declarative_base()",
            main_py_endpoints="# Fallback endpoints\nfrom fastapi import APIRouter\nrouter = APIRouter()",
            conftest_py=fallback_code,
            test_routes_py="# Fallback tests\nimport pytest",
            requirements_txt="fastapi>=0.100.0\nuvicorn>=0.23.0\nsqlalchemy>=2.0.0\npydantic>=2.0.0\npytest>=7.0.0\n",
        )

    @staticmethod
    def extract_tech_stack(trd: str) -> Dict[str, str]:
        """
        Extract technology stack from TRD content.
        Looks for "Tech Stack Summary" section and parses key=value or key: value pairs.

        Supports formats:
        - key: value (with optional bullet point "- " prefix)
        - key=value

        Args:
            trd: Complete TRD text

        Returns:
            Dictionary of technology choices (e.g., {"backend_tech": "FastAPI", ...})
        """
        tech_stack = {}

        # Find "Tech Stack Summary" section
        lines = trd.split('\n')
        in_tech_section = False

        for i, line in enumerate(lines):
            # Look for Tech Stack Summary header
            if 'Tech Stack Summary' in line or 'Technology Stack' in line:
                in_tech_section = True
                continue

            if in_tech_section:
                # Stop when we hit the next section header or blank line followed by header
                if line.strip() and line.startswith('#') and ('Tech Stack' not in line and 'Technology Stack' not in line):
                    break

                # Parse key: value or key=value pairs (with optional bullet point)
                if ':' in line or '=' in line:
                    try:
                        # Remove bullet point if present
                        clean_line = line.strip()
                        if clean_line.startswith('- '):
                            clean_line = clean_line[2:]

                        if '=' in clean_line:
                            key, value = clean_line.split('=', 1)
                        else:
                            key, value = clean_line.split(':', 1)

                        key = key.strip().lower().replace(' ', '_').replace('-', '_')
                        value = value.strip()

                        # Store key=value pair if both are non-empty
                        if key and value:
                            tech_stack[key] = value
                    except ValueError:
                        continue

        # Provide defaults if extraction failed
        if not tech_stack:
            tech_stack = {
                "backend_tech": "FastAPI",
                "database": "SQLite",
                "auth": "None",
                "caching": "None"
            }

        return tech_stack

    def generate_models_code(self, backend_spec: BackendSpec) -> str:
        """
        Generate SQLAlchemy models.py from BackendSpec.
        (Alternative approach without full LLM call)
        """
        imports = """from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()
"""

        models_code = imports

        for model in backend_spec.models:
            model_code = self._generate_model_class(model)
            models_code += "\n\n" + model_code

        return models_code

    def _generate_model_class(self, model: DatabaseModel) -> str:
        """Generate a single SQLAlchemy model class."""
        class_def = f"""
class {model.name}(Base):
    __tablename__ = '{model.plural}'

    # Fields
"""

        # Add fields
        for field_name, field_type in model.fields.items():
            if field_name == "id":
                class_def += f"    {field_name} = Column(Integer, primary_key=True, index=True)\n"
            elif "DateTime" in field_type:
                class_def += (
                    f"    {field_name} = Column(DateTime, "
                    f"default=datetime.utcnow, nullable=False)\n"
                )
            elif "String" in field_type:
                max_len = 255
                class_def += f"    {field_name} = Column(String({max_len}))\n"
            else:
                class_def += f"    {field_name} = Column(String(255))\n"

        # Add relationships
        for rel_name, rel_model in model.relationships.items():
            class_def += f"    {rel_name} = relationship('{rel_model}')\n"

        return class_def

    def generate_endpoint_code(self, backend_spec: BackendSpec) -> str:
        """
        Generate FastAPI endpoint code from BackendSpec.
        (Alternative approach without full LLM call)
        """
        code = """from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from . import models, schemas
from . import database

router = APIRouter()

# Database dependency
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()
"""

        for endpoint in backend_spec.endpoints:
            endpoint_code = self._generate_endpoint_function(endpoint)
            code += "\n\n" + endpoint_code

        return code

    def _generate_endpoint_function(self, endpoint: APIEndpoint) -> str:
        """Generate a single FastAPI endpoint function."""
        method_lower = endpoint.method.value.lower()
        func_name = endpoint.name

        func_code = f"""@router.{method_lower}(
    "{endpoint.path}",
    summary="{endpoint.description}",
    status_code={self._get_status_code(endpoint.method)},
)
async def {func_name}(db: Session = Depends(get_db)):
    \"\"\"
    {endpoint.description}
    \"\"\"
    try:
        # TODO: Implement endpoint logic
        # Use dependency injection pattern above
        # Validate inputs with Pydantic schemas
        # Handle database operations with error handling
        # Return appropriate response
        return {{"status": "todo", "message": "Implement this endpoint"}}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
"""
        return func_code

    @staticmethod
    def _get_status_code(method: HTTPMethod) -> int:
        """Get appropriate HTTP status code for method."""
        status_codes = {
            HTTPMethod.GET: 200,
            HTTPMethod.POST: 201,
            HTTPMethod.PUT: 200,
            HTTPMethod.DELETE: 204,
            HTTPMethod.PATCH: 200,
        }
        return status_codes.get(method, 200)

    def generate_test_code(self, backend_spec: BackendSpec) -> str:
        """
        Generate pytest test code from BackendSpec.
        (Alternative approach without full LLM call)
        """
        code = """import pytest
from httpx import AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from models import Base
from database import get_db

# Test database setup
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture
def test_client():
    return AsyncClient(app=app, base_url="http://test")

@pytest.fixture
def test_db():
    Base.metadata.create_all(bind=engine)
    yield TestingSessionLocal()
    Base.metadata.drop_all(bind=engine)
"""

        # Add test cases for each endpoint
        for endpoint in backend_spec.endpoints:
            test_func = self._generate_test_function(endpoint)
            code += "\n\n" + test_func

        return code

    def _generate_test_function(self, endpoint: APIEndpoint) -> str:
        """Generate a test function for an endpoint."""
        func_name = f"test_{endpoint.name}"
        method = endpoint.method.value.lower()

        test_code = f"""@pytest.mark.asyncio
async def {func_name}(test_client):
    \"\"\"Test {endpoint.description}\"\"\"
    response = await test_client.{method}(
        "{endpoint.path}"
    )
    assert response.status_code == {self._get_status_code(endpoint.method)}
    # Add assertions for response body
    # Example: assert response.json()["key"] == expected_value
"""
        return test_code

    def generate_requirements(self, backend_spec: BackendSpec) -> str:
        """Generate requirements.txt for the backend."""
        base_requirements = [
            "fastapi>=0.100.0",
            "uvicorn[standard]>=0.23.0",
            "sqlalchemy>=2.0.0",
            "pydantic>=2.0.0",
            "python-dotenv>=1.0.0",
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "httpx>=0.24.0",
        ]

        # Add custom dependencies from spec
        all_deps = list(set(base_requirements + backend_spec.dependencies))

        return "\n".join(sorted(all_deps)) + "\n"

    def integrate_with_product(
        self,
        backend_spec: BackendSpec,
        output_path: str,
        context_docs: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """
        Generate all backend code files ready for ProductAssemblyManager.

        Args:
            backend_spec: The backend specification
            output_path: Base path for generated files
            context_docs: Optional PRD/TRD context for product-aware generation

        Returns:
            Dictionary mapping file paths to content
        """
        generated_files = {}

        # Generate code
        code = self.generate_code(backend_spec, context_docs)

        # Map to file structure
        generated_files["app/models.py"] = code.models_py
        generated_files["app/routes.py"] = code.main_py_endpoints
        generated_files["tests/conftest.py"] = code.conftest_py
        generated_files["tests/test_routes.py"] = code.test_routes_py
        generated_files["requirements.txt"] = code.requirements_txt

        return generated_files
