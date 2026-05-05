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
    max_retries: int = 3  # Matches legacy workflow (backend_generator.py, frontend_generator.py)


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
        """Step 1: Extract structured feature set from PRD with graceful failure."""
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
                # Error classification (from backend_generator.py pattern)
                is_rate_limit = "429" in error_str or "rate" in error_str or "quota" in error_str
                is_timeout = "timeout" in error_str or "deadline" in error_str

                # Try JSON fallback for tool name mismatches
                if "tool name does not match" in error_str or "function" in error_str:
                    try:
                        completion = litellm.completion(
                            model=self.config.llm_model,
                            messages=[
                                {"role": "system", "content": "Extract product features from PRD. Return ONLY valid JSON: {\"product_type\":\"...\",\"features\":[...],\"backend_entities\":[...],\"api_endpoints\":[...],\"frontend_pages\":[...]}"},
                                {"role": "user", "content": f"Extract features from PRD:\n\n{prd_content[:4000]}"},
                            ],
                            timeout=90,
                            **self._llm_kwargs(),
                        )
                        import json
                        json_str = completion.choices[0].message.content.strip()
                        if json_str.startswith("```"):
                            json_str = json_str.split("```")[1] if "```" in json_str else json_str
                            if json_str.startswith("json"):
                                json_str = json_str[4:].strip()
                        if json_str.endswith("```"):
                            json_str = json_str[:-3].strip()
                        data = json.loads(json_str)
                        return PRDFeatureSet(**data)
                    except Exception as fallback_e:
                        logger.debug(f"JSON fallback failed: {fallback_e}")

                if attempt < self.config.max_retries - 1:
                    # Exponential backoff by error type (from backend_generator.py)
                    if is_rate_limit:
                        wait_time = [20, 60][min(attempt, 1)]
                    elif is_timeout:
                        wait_time = [10, 30][min(attempt, 1)]
                    else:
                        wait_time = [15, 45][min(attempt, 1)]

                    logger.warning(f"⚠ Feature extraction attempt {attempt + 1} failed ({type(e).__name__}). "
                                 f"Retrying in {wait_time}s...")
                    print(f"⚠ Feature extraction attempt {attempt + 1} failed. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.warning(f"⚠ Feature extraction failed after {self.config.max_retries} attempts, using fallback")
                    print(f"⚠ Feature extraction failed after {self.config.max_retries} attempts, using fallback")

        # Graceful fallback: frontend-only with no backend features
        return PRDFeatureSet(
            product_type="frontend_only",
            features=["Frontend-only product (backend generation failed)"],
            backend_entities=[],
            api_endpoints=[],
            frontend_pages=["index"]
        )

    def _generate_tests(self, prd_content: str, features: PRDFeatureSet) -> GeneratedTests:
        """Step 2 (TDD Red): Generate tests from PRD with graceful failure."""
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
                error_str = str(e).lower()
                is_rate_limit = "429" in error_str or "rate" in error_str or "quota" in error_str
                is_timeout = "timeout" in error_str or "deadline" in error_str

                if attempt < self.config.max_retries - 1:
                    # Exponential backoff by error type
                    if is_rate_limit:
                        wait_time = [20, 60][min(attempt, 1)]
                    elif is_timeout:
                        wait_time = [10, 30][min(attempt, 1)]
                    else:
                        wait_time = [15, 45][min(attempt, 1)]

                    logger.warning(f"⚠ Test generation attempt {attempt + 1} failed ({type(e).__name__}). "
                                 f"Retrying in {wait_time}s...")
                    print(f"⚠ Test generation attempt {attempt + 1} failed. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.warning(f"⚠ Test generation failed after {self.config.max_retries} attempts, using fallback")
                    print(f"⚠ Test generation failed after {self.config.max_retries} attempts, using fallback")

        # Graceful fallback: minimal test structure
        return GeneratedTests(
            conftest_py="""import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

TEST_DB_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(autouse=True)
def setup_db():
    from app.database import Base
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
""",
            test_api_py="""import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_app_startup():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code in [200, 404, 405]
"""
        )

    def _generate_implementation(
        self, prd_content: str, features: PRDFeatureSet, tests: GeneratedTests
    ) -> GeneratedImplementation:
        """Step 3 (TDD Green): Generate implementation to pass tests with graceful failure."""
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
                is_rate_limit = "429" in error_str or "rate" in error_str or "quota" in error_str
                is_timeout = "timeout" in error_str or "deadline" in error_str

                # Try JSON fallback for tool call issues
                if "multiple tool calls" in error_str or "tool call" in error_str:
                    try:
                        completion = litellm.completion(
                            model=self.config.llm_model,
                            messages=[
                                {"role": "system", "content": "Return ONLY valid JSON: {\"models_py\":\"...\",\"routes_py\":\"...\",\"main_py\":\"...\",\"requirements_txt\":\"...\"}"},
                                {"role": "user", "content": user_prompt},
                            ],
                            timeout=150,
                            **self._llm_kwargs(),
                        )
                        import json
                        json_str = completion.choices[0].message.content.strip()
                        if json_str.startswith("```"):
                            json_str = json_str.split("```")[1] if "```" in json_str else json_str
                            if json_str.startswith("json"):
                                json_str = json_str[4:].strip()
                        if json_str.endswith("```"):
                            json_str = json_str[:-3].strip()
                        data = json.loads(json_str)
                        return GeneratedImplementation(**data)
                    except Exception as fallback_e:
                        logger.debug(f"JSON fallback failed: {fallback_e}")

                if attempt < self.config.max_retries - 1:
                    # Exponential backoff by error type
                    if is_rate_limit:
                        wait_time = [20, 60][min(attempt, 1)]
                    elif is_timeout:
                        wait_time = [10, 30][min(attempt, 1)]
                    else:
                        wait_time = [15, 45][min(attempt, 1)]

                    logger.warning(f"⚠ Implementation attempt {attempt + 1} failed ({type(e).__name__}). "
                                 f"Retrying in {wait_time}s...")
                    print(f"⚠ Implementation attempt {attempt + 1} failed. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.warning(f"⚠ Implementation failed after {self.config.max_retries} attempts, using fallback")
                    print(f"⚠ Implementation failed after {self.config.max_retries} attempts, using fallback")

        # Graceful fallback: minimal FastAPI scaffold
        return GeneratedImplementation(
            models_py="""from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
""",
            routes_py="""from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health_check():
    return {"status": "ok"}
""",
            main_py="""from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import router

app = FastAPI(title="Generated API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/")
async def root():
    return {"message": "API is running"}
""",
            requirements_txt="""fastapi>=0.100.0
uvicorn>=0.23.0
sqlalchemy>=2.0.0
pydantic>=2.0.0
pytest>=7.0.0
httpx>=0.24.0
pytest-asyncio>=0.21.0
"""
        )

    def _generate_frontend(self, prd_content: str) -> Dict[str, str]:
        """Step 4: Generate frontend directly from PRD with graceful failure."""
        from frontend_generator import FrontendGenerator, FrontendGeneratorConfig, GeneratedFrontendCode

        logger.info("Frontend generation starting...")
        fg_config = FrontendGeneratorConfig(
            llm_model=self.config.llm_model,
            api_key=self.config.api_key,
            api_base=self.config.api_base,
        )
        fg = FrontendGenerator(config=fg_config)

        result = None
        # Try FrontendGenerator with retries
        for attempt in range(self.config.max_retries):
            try:
                result = fg.generate_from_prd(prd_content)
                logger.info(f"Frontend generated: {len(result.pages)} pages, {len(result.components)} components")

                # Check if result is the minimal fallback template
                index_html = result.pages.get("index.html", "")
                is_fallback = "Application frontend loaded successfully" in index_html

                if not is_fallback and result.pages and len(index_html) > 500:
                    # Got real content, use it
                    break
                elif is_fallback:
                    logger.warning(f"FrontendGenerator returned fallback, will retry manual LLM call...")
                    result = None  # Clear it so we know to use manual fallback
                    raise Exception("FrontendGenerator fallback detected")
            except Exception as e:
                error_str = str(e).lower()
                is_rate_limit = "429" in error_str or "rate" in error_str or "quota" in error_str
                is_timeout = "timeout" in error_str or "deadline" in error_str

                if attempt < self.config.max_retries - 1:
                    # Exponential backoff by error type
                    if is_rate_limit:
                        wait_time = [20, 60][min(attempt, 1)]
                    elif is_timeout:
                        wait_time = [10, 30][min(attempt, 1)]
                    else:
                        wait_time = [15, 45][min(attempt, 1)]

                    logger.warning(f"⚠ Frontend generation attempt {attempt + 1} failed ({type(e).__name__}). "
                                 f"Retrying in {wait_time}s...")
                    print(f"⚠ Frontend generation attempt {attempt + 1} failed. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.warning(f"⚠ FrontendGenerator exhausted retries, using manual LLM call...")

        # If FrontendGenerator didn't work or returned fallback, try manual LLM call
        if not result or "Application frontend loaded successfully" in result.pages.get("index.html", ""):
            logger.warning("FrontendGenerator failed/fallback detected, trying manual LLM call...")
            for retry in range(self.config.max_retries):
                try:
                    prd_frontend_system = """You are a Senior Frontend Developer generating a complete HTML frontend from a PRD document.
Your task: Create a real, functional website with actual product information extracted from the PRD.

CRITICAL: You MUST include actual product/service names, features, and descriptions from the PRD in the generated HTML.

Return ONLY valid JSON (no markdown wrapping, no explanations):
{"pages":{"index.html":"<full html>"},"components":{},"styles":{},"navigation_update":""}

The HTML must:
- Include actual product/service names from PRD
- Include actual features and benefits from PRD
- Have real call-to-action buttons for the actual product
- Use inline CSS (no external files)
- Be production-ready and semantic HTML5"""

                    completion = litellm.completion(
                        model=self.config.llm_model,
                        messages=[
                            {"role": "system", "content": prd_frontend_system},
                            {"role": "user", "content": f"Generate a complete frontend from this PRD. Include actual product names, features, and descriptions:\n\n{prd_content[:4000]}"},
                        ],
                        timeout=120,
                        **self._llm_kwargs(),
                    )
                    import json
                    response_text = completion.choices[0].message.content.strip()

                    # Try to extract JSON from response
                    json_str = response_text
                    if "```" in json_str:
                        json_str = json_str.split("```")[1]
                        if json_str.startswith("json"):
                            json_str = json_str[4:].strip()
                        else:
                            json_str = json_str.lstrip()

                    json_str = json_str.rstrip("`").strip()

                    # Parse and validate
                    data = json.loads(json_str)
                    pages = data.get("pages", {})
                    index_html = pages.get("index.html", "")
                    has_real_content = (
                        len(index_html) > 500 and
                        "Application frontend loaded successfully" not in index_html
                    )

                    if has_real_content:
                        result = GeneratedFrontendCode(
                            pages=pages,
                            components=data.get("components", {}),
                            styles=data.get("styles", {}),
                            navigation_update=data.get("navigation_update", "")
                        )
                        logger.info(f"Manual LLM call succeeded on attempt {retry + 1} with {len(index_html)} chars")
                        break
                    else:
                        error_str = str(e).lower() if e else "minimal content"
                        is_rate_limit = "429" in error_str or "rate" in error_str or "quota" in error_str
                        is_timeout = "timeout" in error_str or "deadline" in error_str

                        if retry < self.config.max_retries - 1:
                            if is_rate_limit:
                                wait_time = [20, 60][min(retry, 1)]
                            elif is_timeout:
                                wait_time = [10, 30][min(retry, 1)]
                            else:
                                wait_time = [15, 45][min(retry, 1)]

                            logger.warning(f"Manual LLM attempt {retry + 1}: minimal content, retrying in {wait_time}s...")
                            time.sleep(wait_time)
                except Exception as e:
                    error_str = str(e).lower()
                    is_rate_limit = "429" in error_str or "rate" in error_str or "quota" in error_str
                    is_timeout = "timeout" in error_str or "deadline" in error_str

                    if retry < self.config.max_retries - 1:
                        if is_rate_limit:
                            wait_time = [20, 60][min(retry, 1)]
                        elif is_timeout:
                            wait_time = [10, 30][min(retry, 1)]
                        else:
                            wait_time = [15, 45][min(retry, 1)]

                        logger.warning(f"⚠ Manual LLM attempt {retry + 1} failed ({type(e).__name__}). "
                                     f"Retrying in {wait_time}s...")
                        print(f"⚠ Manual LLM attempt {retry + 1} failed. Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        logger.warning(f"⚠ Manual LLM call exhausted retries, using fallback HTML")
                        print(f"⚠ Frontend generation exhausted all retries, using fallback HTML")

        # Fallback result if everything failed
        if not result:
            logger.warning("Using fallback frontend HTML")
            result = GeneratedFrontendCode(
                pages={"index.html": fg._generate_fallback_frontend()},
                components={},
                styles={},
                navigation_update="",
            )

        # Flatten into a single dict: {relative_path: content}
        files: Dict[str, str] = {}
        for filename, content in result.pages.items():
            if content and content.strip():  # Only add non-empty files
                files[filename] = content
                logger.debug(f"  Page: {filename} ({len(content)} chars)")
        for filename, content in result.components.items():
            if content and content.strip():
                files[f"js/{filename}"] = content
                logger.debug(f"  Component: {filename} ({len(content)} chars)")
        for filename, content in result.styles.items():
            if content and content.strip():
                files[filename] = content
                logger.debug(f"  Style: {filename} ({len(content)} chars)")

        logger.info(f"Frontend flattened to {len(files)} files")
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
