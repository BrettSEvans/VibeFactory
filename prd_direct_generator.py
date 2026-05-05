"""
PRD-Direct TDD Generator
Generates a complete product directly from the PRD using Test-Driven Development.
Flow: PRD → feature extraction → tests (Red) → implementation (Green) → frontend → assembly
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional

import instructor
import litellm
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ── Configuration ─────────────────────────────────────────────────────────────

class PRDDirectConfig(BaseModel):
    llm_model: str = Field(default="meta-llama/llama-3.3-70b-instruct:free")
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    max_retries: int = 2


# ── Structured LLM response models ────────────────────────────────────────────

class APIEndpointSpec(BaseModel):
    method: str = Field(..., description="HTTP method: GET, POST, PUT, DELETE")
    path: str = Field(..., description="URL path, e.g. /items or /items/{item_id}")
    purpose: str = Field(..., description="Brief description of what this endpoint does")


class PRDFeatureSet(BaseModel):
    """Structured feature set extracted from PRD by LLM."""
    product_type: str = Field(
        ...,
        description="'fullstack' if an API/database is needed, 'frontend_only' if purely static UI"
    )
    features: List[str] = Field(..., description="Human-readable feature names from the PRD")
    backend_entities: List[str] = Field(
        default_factory=list,
        description="Database model names required (e.g. 'User', 'Item')"
    )
    api_endpoints: List[APIEndpointSpec] = Field(
        default_factory=list,
        description="REST API endpoints needed to support the PRD features"
    )
    frontend_pages: List[str] = Field(..., description="Names of frontend pages or views")

    class Config:
        # Allow LLM to use alternative names (e.g., PRDFFeatureSet, FeatureSet, etc.)
        populate_by_name = True


class GeneratedTests(BaseModel):
    conftest_py: str = Field(..., description="pytest conftest.py with fixtures")
    test_api_py: str = Field(..., description="test_api.py with all endpoint tests")


class GeneratedImplementation(BaseModel):
    models_py: str = Field(..., description="SQLAlchemy ORM models + Pydantic schemas")
    routes_py: str = Field(..., description="FastAPI route handlers for all endpoints")
    main_py: str = Field(..., description="FastAPI app entry point that includes all routes")
    requirements_txt: str = Field(..., description="Python package requirements")


# ── System prompts ─────────────────────────────────────────────────────────────

_FEATURE_EXTRACTION_SYSTEM = """You are a Senior Software Architect.
Read the PRD and extract structured product requirements into the exact JSON format specified below.
Be conservative — only extract what is explicitly required by the PRD.
Determine whether the product needs a backend (database + REST API) or is purely a frontend/static site.
Identify all data entities, API endpoints, and frontend pages needed.

Return a JSON object with these exact fields:
{
  "product_type": "fullstack" or "frontend_only",
  "features": ["list", "of", "feature", "names"],
  "backend_entities": ["entity", "names"],
  "api_endpoints": [
    {"method": "GET", "path": "/endpoint", "purpose": "description"},
    ...
  ],
  "frontend_pages": ["page", "names"]
}"""

_TEST_GENERATION_SYSTEM = """You are a Senior QA Engineer writing pytest tests in Test-Driven Development style.
You are given a PRD and a structured feature set. You must write tests BEFORE any implementation exists.

RULES:
- Tests import the FastAPI app as: from app.main import app
- Use httpx AsyncClient with ASGITransport for async tests
- conftest.py must set up an in-memory SQLite database and override the app's DB dependency
- test_api.py must test every endpoint: happy path, validation errors, 404s, and edge cases from the PRD
- Tests must be written to FAIL against an empty app — they drive the implementation
- Use pytest-asyncio with asyncio_mode = "auto" in conftest.py
- Pydantic models are in app.models, routes are in app.routes, DB config in app.database

CONFTEST PATTERN (follow exactly):
```python
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db

TEST_DB_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
```"""

_IMPLEMENTATION_SYSTEM = """You are a Senior FastAPI Developer implementing code to pass a given pytest test suite.

OUTPUT INSTRUCTION: Return ONLY valid JSON with these 4 keys: models_py, routes_py, main_py, requirements_txt.
Do NOT use multiple tool calls. Return a single JSON object.

RULES:
- Write real, working code — no stubs, no mocks, no pass statements
- Use SQLAlchemy ORM with SQLite (no raw SQL)
- Use Pydantic v2 for all request/response schemas
- Type hints on every function
- Match the module paths the tests expect exactly:
  - App entry: app/main.py  →  from app.main import app
  - ORM models + Pydantic schemas: app/models.py
  - Route handlers: app/routes.py
  - DB config: app/database.py (must export Base, engine, get_db)
- routes.py must define an APIRouter that main.py includes
- Do NOT add features not covered by the tests
- FastAPI CORS middleware must be included in main.py (allow_origins=["*"])
- Database URL: sqlite:///./app.db (overridden in tests)

DATABASE PATTERN (follow exactly in app/database.py):
```python
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

Return valid JSON only: {"models_py": "...", "routes_py": "...", "main_py": "...", "requirements_txt": "..."}"""

_IMPLEMENTATION_USER_TEMPLATE = """Implement a FastAPI application that makes ALL of the following tests pass.

PRD (for domain context):
{prd_summary}

FEATURES TO IMPLEMENT:
{features}

ENDPOINTS TO IMPLEMENT:
{endpoints}

TEST FILE (your implementation must pass every test):
```python
{test_api_py}
```

CONFTEST (the test fixtures your tests use):
```python
{conftest_py}
```

Generate:
1. models.py — SQLAlchemy ORM models + Pydantic request/response schemas
2. routes.py — FastAPI APIRouter with all route handlers
3. main.py — FastAPI app with CORS, includes router from routes.py, imports database
4. requirements.txt — all Python packages needed (fastapi, sqlalchemy, pydantic, httpx, pytest-asyncio, etc.)

Return valid JSON with keys: models_py, routes_py, main_py, requirements_txt"""


# ── Main generator class ───────────────────────────────────────────────────────

class PRDDirectGenerator:
    """Generates a complete product directly from PRD using TDD."""

    def __init__(self, config: Optional[PRDDirectConfig] = None):
        self.config = config or PRDDirectConfig()
        self.client = instructor.from_litellm(litellm.completion)

    def _llm_kwargs(self, extra: dict = None) -> dict:
        base = {
            "api_key": self.config.api_key,
        }
        if self.config.api_base:
            base["api_base"] = self.config.api_base
        if extra:
            base.update(extra)
        return base

    def _extract_features(self, prd_content: str) -> PRDFeatureSet:
        """Step 1: Extract structured feature set from PRD."""
        for attempt in range(self.config.max_retries):
            try:
                return self.client.create(
                    model=self.config.llm_model,
                    messages=[
                        {"role": "system", "content": _FEATURE_EXTRACTION_SYSTEM},
                        {"role": "user", "content": f"Extract the product feature set from this PRD:\n\n{prd_content[:4000]}"},
                    ],
                    response_model=PRDFeatureSet,
                    timeout=90,
                    max_retries=0,
                    **self._llm_kwargs(),
                )
            except Exception as e:
                error_str = str(e).lower()
                # If it's a tool name mismatch, try a simpler approach
                if "tool name does not match" in error_str or "function" in error_str:
                    logger.warning(f"Tool name mismatch in attempt {attempt + 1}. Retrying with fallback prompt...")
                    try:
                        # Try without structured output — parse the response manually
                        completion = litellm.completion(
                            model=self.config.llm_model,
                            messages=[
                                {"role": "system", "content": "Extract product features from the PRD and return ONLY valid JSON (no markdown, no explanation). Return the JSON object directly."},
                                {"role": "user", "content": f"Extract the product feature set from this PRD as JSON:\n\n{prd_content[:4000]}"},
                            ],
                            timeout=90,
                            **self._llm_kwargs(),
                        )
                        import json
                        json_str = completion.choices[0].message.content.strip()
                        # Remove markdown code block if present
                        if json_str.startswith("```json"):
                            json_str = json_str[7:]
                        if json_str.startswith("```"):
                            json_str = json_str[3:]
                        if json_str.endswith("```"):
                            json_str = json_str[:-3]
                        json_str = json_str.strip()
                        data = json.loads(json_str)
                        return PRDFeatureSet(**data)
                    except Exception as fallback_e:
                        logger.warning(f"Fallback parsing failed: {fallback_e}. Will retry main path...")

                if attempt < self.config.max_retries - 1:
                    time.sleep(15)
                    logger.warning(f"Feature extraction attempt {attempt + 1} failed: {e}")
                else:
                    logger.error(f"Feature extraction failed after {self.config.max_retries} attempts: {e}")
                    raise

    def _generate_tests(self, prd_content: str, features: PRDFeatureSet) -> GeneratedTests:
        """Step 2 (TDD Red): Generate tests from PRD before any implementation."""
        endpoint_list = "\n".join(
            f"  - {ep.method} {ep.path}: {ep.purpose}" for ep in features.api_endpoints
        )
        entity_list = ", ".join(features.backend_entities) or "none"
        user_prompt = (
            f"Write pytest tests for this product.\n\n"
            f"PRD Summary (first 2000 chars):\n{prd_content[:2000]}\n\n"
            f"Entities: {entity_list}\n"
            f"Endpoints to test:\n{endpoint_list}\n\n"
            f"Features: {', '.join(features.features)}\n\n"
            f"Return conftest_py and test_api_py as described in your instructions."
        )
        for attempt in range(self.config.max_retries):
            try:
                return self.client.create(
                    model=self.config.llm_model,
                    messages=[
                        {"role": "system", "content": _TEST_GENERATION_SYSTEM},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_model=GeneratedTests,
                    timeout=120,
                    max_retries=0,
                    **self._llm_kwargs(),
                )
            except Exception as e:
                if attempt < self.config.max_retries - 1:
                    time.sleep(20)
                    logger.warning(f"Test generation attempt {attempt + 1} failed: {e}")
                else:
                    logger.error(f"Test generation failed: {e}")
                    raise

    def _generate_implementation(
        self, prd_content: str, features: PRDFeatureSet, tests: GeneratedTests
    ) -> GeneratedImplementation:
        """Step 3 (TDD Green): Generate implementation to pass the tests."""
        endpoint_list = "\n".join(
            f"  - {ep.method} {ep.path}: {ep.purpose}" for ep in features.api_endpoints
        )
        user_prompt = _IMPLEMENTATION_USER_TEMPLATE.format(
            prd_summary=prd_content[:1500],
            features="\n".join(f"  - {f}" for f in features.features),
            endpoints=endpoint_list,
            test_api_py=tests.test_api_py,
            conftest_py=tests.conftest_py,
        )
        for attempt in range(self.config.max_retries):
            try:
                return self.client.create(
                    model=self.config.llm_model,
                    messages=[
                        {"role": "system", "content": _IMPLEMENTATION_SYSTEM},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_model=GeneratedImplementation,
                    timeout=150,
                    max_retries=0,
                    **self._llm_kwargs(),
                )
            except Exception as e:
                error_str = str(e).lower()
                # If it's a tool call issue, try fallback plain JSON approach
                if "multiple tool calls" in error_str or "tool call" in error_str:
                    logger.warning(f"Tool call error in attempt {attempt + 1}. Trying plain JSON fallback...")
                    try:
                        completion = litellm.completion(
                            model=self.config.llm_model,
                            messages=[
                                {"role": "system", "content": "Return ONLY valid JSON with keys: models_py, routes_py, main_py, requirements_txt. No markdown, no explanation."},
                                {"role": "user", "content": user_prompt},
                            ],
                            timeout=150,
                            **self._llm_kwargs(),
                        )
                        import json
                        json_str = completion.choices[0].message.content.strip()
                        if json_str.startswith("```json"):
                            json_str = json_str[7:]
                        if json_str.startswith("```"):
                            json_str = json_str[3:]
                        if json_str.endswith("```"):
                            json_str = json_str[:-3]
                        json_str = json_str.strip()
                        data = json.loads(json_str)
                        return GeneratedImplementation(**data)
                    except Exception as fallback_e:
                        logger.warning(f"Fallback parsing failed: {fallback_e}. Will retry main path...")

                if attempt < self.config.max_retries - 1:
                    time.sleep(20)
                    logger.warning(f"Implementation generation attempt {attempt + 1} failed: {e}")
                else:
                    logger.error(f"Implementation generation failed: {e}")
                    raise

    def _generate_frontend(self, prd_content: str) -> Dict[str, str]:
        """Step 4: Generate frontend directly from PRD (reuse FrontendGenerator)."""
        from frontend_generator import FrontendGenerator, FrontendGeneratorConfig
        fg_config = FrontendGeneratorConfig(
            llm_model=self.config.llm_model,
            api_key=self.config.api_key,
            api_base=self.config.api_base,
        )
        fg = FrontendGenerator(config=fg_config)
        result = fg.generate_from_prd(prd_content)

        # Flatten into a single dict: {relative_path: content}
        files: Dict[str, str] = {}
        for filename, content in result.pages.items():
            files[filename] = content
        for filename, content in result.components.items():
            files[f"js/{filename}"] = content
        for filename, content in result.styles.items():
            files[filename] = content
        return files

    async def generate(
        self,
        project_id: str,
        prd_content: str,
        context_docs: Dict[str, str],
        progress_cb: Optional[Callable] = None,
    ) -> str:
        """
        Generate a complete product from PRD using TDD.
        Returns the product directory path.
        """
        loop = asyncio.get_event_loop()

        async def _progress(step: str, pct: int, msg: str):
            if progress_cb:
                await progress_cb(step, pct, msg)

        # ── Step 1: Feature extraction ─────────────────────────────────────────
        await _progress("Analyzing PRD", 35, "🔍 Extracting features and API design from PRD...")
        features: PRDFeatureSet = await loop.run_in_executor(
            None, lambda: self._extract_features(prd_content)
        )
        is_frontend_only = (
            features.product_type == "frontend_only"
            or (not features.backend_entities and not features.api_endpoints)
        )
        logger.info(
            f"Feature extraction complete: {len(features.features)} features, "
            f"type={features.product_type}, frontend_only={is_frontend_only}"
        )

        tests: Optional[GeneratedTests] = None
        impl: Optional[GeneratedImplementation] = None

        if not is_frontend_only:
            # ── Step 2: TDD Red — generate tests ──────────────────────────────
            await _progress("TDD Tests", 42, "🧪 Writing tests from PRD (TDD Red phase)...")
            tests = await loop.run_in_executor(
                None, lambda: self._generate_tests(prd_content, features)
            )
            logger.info("TDD test generation complete")

            # ── Step 3: TDD Green — generate implementation ────────────────────
            await _progress("TDD Implement", 62, "⚙️ Generating implementation to pass tests (TDD Green phase)...")
            impl = await loop.run_in_executor(
                None, lambda: self._generate_implementation(prd_content, features, tests)
            )
            logger.info("TDD implementation generation complete")

        # ── Step 4: Frontend generation ────────────────────────────────────────
        await _progress("Frontend", 82, "🎨 Generating frontend from PRD...")
        frontend_files: Dict[str, str] = await loop.run_in_executor(
            None, lambda: self._generate_frontend(prd_content)
        )
        logger.info(f"Frontend generation complete: {len(frontend_files)} files")

        # ── Step 5: Assembly ───────────────────────────────────────────────────
        await _progress("Assembling", 90, "📦 Assembling product...")
        product_path = await loop.run_in_executor(
            None,
            lambda: self._assemble_product(
                project_id, features, tests, impl, frontend_files, context_docs
            ),
        )
        await _progress("Assembling", 98, "✅ Assembly complete")
        return product_path

    def _assemble_product(
        self,
        project_id: str,
        features: PRDFeatureSet,
        tests: Optional[GeneratedTests],
        impl: Optional[GeneratedImplementation],
        frontend_files: Dict[str, str],
        context_docs: Dict[str, str],
    ) -> str:
        from product_assembly import ProductAssemblyManager

        manager = ProductAssemblyManager(
            project_id=project_id,
            context_docs=context_docs,
        )
        manager.initialize_product_structure()

        # Write backend files (if fullstack)
        if impl and tests:
            # Implementation files go into app/
            manager.add_backend_code("prd_direct", "models.py", impl.models_py)
            manager.add_backend_code("prd_direct", "routes.py", impl.routes_py)
            manager.add_backend_code("prd_direct", "main.py", impl.main_py)

            # requirements.txt goes at backend root (one level up from app/)
            req_path = manager.backend_dir / "requirements.txt"
            req_path.write_text(impl.requirements_txt)

            # TDD test files go into tests/ (sibling of app/)
            tests_dir = manager.backend_dir / "tests"
            tests_dir.mkdir(parents=True, exist_ok=True)
            (tests_dir / "conftest.py").write_text(tests.conftest_py)
            (tests_dir / "test_api.py").write_text(tests.test_api_py)

            # database.py scaffold (app/ dir)
            db_py = _DATABASE_PY_SCAFFOLD
            manager.add_backend_code("prd_direct", "database.py", db_py)

        # Write frontend files
        for file_path, content in frontend_files.items():
            manager.add_frontend_component("prd_direct", file_path, content)

        # Save PRD to docs/
        docs_dir = manager.product_dir / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)
        prd = context_docs.get("PRD", "")
        if prd:
            (docs_dir / "PRD.md").write_text(prd)
        brd = context_docs.get("BRD", "")
        if brd:
            (docs_dir / "BRD.md").write_text(brd)

        # Export (docker-compose, README, start.sh)
        manager.export_product()

        return str(manager.product_dir)


_DATABASE_PY_SCAFFOLD = '''"""
Database configuration — auto-generated by VibeFactory PRD-Direct
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency: yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
'''
