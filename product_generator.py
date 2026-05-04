"""
Module 8: Product Generator
Orchestrates the complete product generation workflow:
  Story → Specification → Code Generation → Product Assembly

This module integrates:
  - StoryTranslator: Converts stories to technical specs
  - BackendGenerator: Generates FastAPI code
  - FrontendGenerator: Generates vanilla JS code
  - ProductAssemblyManager: Assembles final product
"""

import asyncio
import os
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import json

from state import ProjectState
from sandbox import ProjectSandbox, CommandResult
from story_translator import StoryTranslator, BackendSpec, FrontendSpec
from state import Story
from backend_generator import BackendGenerator, BackendGeneratorConfig
from frontend_generator import FrontendGenerator, FrontendGeneratorConfig
from product_assembly import ProductAssemblyManager
import instructor
import litellm
from pydantic import BaseModel, Field


class ProductGenerationStatus(Enum):
    """Status of product generation for a story."""
    PENDING = "PENDING"
    TRANSLATING = "TRANSLATING"
    GENERATING_BACKEND = "GENERATING_BACKEND"
    GENERATING_FRONTEND = "GENERATING_FRONTEND"
    ASSEMBLING = "ASSEMBLING"
    TESTING = "TESTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class StoryGeneration:
    """Result of generating backend and frontend for a story."""
    story_id: str
    story_name: str
    status: ProductGenerationStatus
    backend_spec: Optional[BackendSpec] = None
    frontend_spec: Optional[FrontendSpec] = None
    backend_code: Optional[Dict[str, str]] = None
    frontend_code: Optional[Dict[str, str]] = None
    test_results: Optional[CommandResult] = None
    error_message: str = ""


class ProductValidatorResponse(BaseModel):
    """Response from product validator."""
    passed: bool = Field(..., description="Whether product passes validation")
    api_endpoints_tested: int = Field(..., description="Number of endpoints tested")
    pages_tested: int = Field(..., description="Number of pages tested")
    failures: List[str] = Field(default_factory=list, description="Test failures")
    feedback: str = Field(..., description="Detailed feedback")


class ProductGeneratorConfig(BaseModel):
    """Configuration for product generator."""
    llm_model: str = Field(
        default="meta-llama/llama-3.3-70b-instruct:free",
        description="LLM model for code generation"
    )
    api_key: Optional[str] = Field(default=None, description="API key for LLM provider")
    api_base: Optional[str] = Field(default=None, description="Custom API base URL for OpenAI-compatible providers")
    max_retries: int = Field(default=3, ge=1, description="Max generation retries")
    run_tests: bool = Field(default=True, description="Run tests after generation")
    worker_pool_size: int = Field(default=4, ge=1, description="Parallel execution workers")
    # Optional callback: (story_index: int, total_stories: int, story_name: str, status_msg: str) -> None
    # Called at key moments during story generation for real-time progress reporting.
    progress_callback: Optional[Any] = Field(default=None, exclude=True)

    model_config = {"arbitrary_types_allowed": True}


class ProductGenerator:
    """
    Orchestrates complete product generation from stories.

    WORKFLOW:
    1. For each story:
       a) StoryTranslator: Parse story + PRD/TRD context → BackendSpec + FrontendSpec
          (Static/simple products skip backend generation entirely)
       b) BackendGenerator: Generate FastAPI code from BackendSpec (skipped if static)
       c) FrontendGenerator: Generate frontend code from FrontendSpec
       d) ProductAssemblyManager: Integrate into product structure
       e) Testing: Run tests and validate (skipped for static frontends)

    2. After all stories:
       a) Update navigation with registered pages
       b) Create docker-compose.yml (skipped for static products)
       c) Export final product
    """

    # Product Validator Prompts
    PRODUCT_VALIDATOR_SYS = """You are a Senior QA Automation Engineer.
Your task is to review a generated product and validate that:
1. All API endpoints from the spec are implemented
2. All pages from the frontend spec exist
3. Frontend properly calls backend APIs
4. Database schema supports required operations
5. Tests cover critical paths
6. Code follows security best practices"""

    PRODUCT_VALIDATOR_USER = """Validate this generated product:

Backend Specification:
{backend_spec}

Frontend Specification:
{frontend_spec}

Generated Code Structure:
{code_structure}

Validation Focus:
- API endpoint implementations match spec
- Frontend pages match spec
- Database schema completeness
- Test coverage adequacy
- Security posture (SQL injection, XSS prevention)

Provide validation results."""

    def __init__(
        self,
        config: Optional[ProductGeneratorConfig] = None,
        state: Optional[ProjectState] = None,
        sandbox: Optional[ProjectSandbox] = None,
        product_dir: Optional[str] = None,
    ):
        """
        Initialize the product generator.

        Args:
            config: Generator configuration
            state: Project state
            sandbox: Execution sandbox
            product_dir: Directory to create products in
        """
        self.config = config or ProductGeneratorConfig()
        self.state = state
        self.sandbox = sandbox
        self.product_dir = product_dir or "./products"

        # Initialize components (TRD content can be set later via set_trd_content)
        self.story_translator = StoryTranslator()
        self.backend_generator = BackendGenerator(
            BackendGeneratorConfig(
                llm_model=self.config.llm_model,
                api_key=self.config.api_key,
                api_base=self.config.api_base
            )
        )
        self.frontend_generator = FrontendGenerator(
            FrontendGeneratorConfig(
                llm_model=self.config.llm_model,
                api_key=self.config.api_key,
                api_base=self.config.api_base
            )
        )

        self.results: Dict[str, StoryGeneration] = {}
        self.api_key = self.config.api_key
        self._setup_client()

    def _setup_client(self) -> None:
        """Initialize instructor-enhanced LLM client."""
        self.client = instructor.from_litellm(litellm.completion)

    async def generate_product(
        self,
        project_id: str,
        stories: Optional[List[Story]] = None,
        frontend_stories: Optional[List[Story]] = None,
        backend_stories: Optional[List[Story]] = None,
        context_docs: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Generate complete product from stories.

        TWO-TRACK GENERATION:
        - TRACK 1 (Frontend): One-shot generation from PRD only
        - TRACK 2 (Backend): Per-story generation from story.llm_prompt + TRD tech_stack

        Args:
            project_id: Unique project identifier
            stories: Legacy parameter - List of Story objects (backward compatibility)
            frontend_stories: Frontend stories generated from PRD only
            backend_stories: Backend stories generated from TRD only
            context_docs: Optional context documents (PRD, TRD)

        Returns:
            Path to generated product
        """
        print("\n" + "=" * 70)
        print(f"PRODUCT GENERATION: {project_id}")
        print("=" * 70)

        # Backward compatibility: if legacy stories parameter is provided, use it
        if stories and not frontend_stories and not backend_stories:
            frontend_stories = stories
            backend_stories = stories

        # Initialize product assembly manager with context docs for PRD-based README
        product = ProductAssemblyManager(
            project_id=project_id,
            root_dir=self.product_dir,
            context_docs=context_docs
        )

        # Feed TRD content to story translator so it can detect product type
        if context_docs:
            trd_content = context_docs.get("TRD", context_docs.get("trd", ""))
            if trd_content:
                self.story_translator.trd_content = trd_content

        # Determine if product needs backend (check backend_stories)
        product_needs_backend = backend_stories and len(backend_stories) > 0
        if product_needs_backend:
            product.initialize_product_structure()
        else:
            # Static products: only a bare frontend dir
            product.frontend_dir.mkdir(parents=True, exist_ok=True)

        # TRACK 1: One-shot frontend generation from PRD
        print("\n[1/4] Generating Frontend from PRD (one-shot)...")
        prd_content = context_docs.get("PRD", "") if context_docs else ""
        frontend_code = await self._generate_frontend_from_prd(prd_content)

        # Add frontend code to product
        for file_path, content in frontend_code.items():
            product.add_frontend_component("_frontend_track", file_path, content)

        # TRACK 2: Per-story backend generation from llm_prompt
        if product_needs_backend and backend_stories:
            print(f"\n[2/4] Generating Backend for {len(backend_stories)} stories (per-story)...")
            completed_ids = await self._execute_stories_sequential(
                backend_stories,
                product,
                context_docs
            )
        else:
            completed_ids = set()

        # Export final product
        print("\n[3/4] Exporting Product...")
        export_path = product.export_product()
        print(f"  ✓ Product exported to: {export_path}")

        return export_path

    async def _generate_frontend_from_prd(self, prd_content: str) -> Dict[str, str]:
        """
        Generate frontend code directly from PRD (TRACK 1).
        One-shot generation with zero story context.

        Args:
            prd_content: Complete PRD text

        Returns:
            Dictionary of frontend files (path -> content)
        """
        if not prd_content:
            print("  ⚠ No PRD available, using fallback frontend")
            return {"index.html": self.frontend_generator._generate_fallback_frontend()}

        try:
            # TRACK 1: One-shot frontend generation from PRD only
            frontend_code = self.frontend_generator.generate_from_prd(prd_content)
            frontend_files = self.frontend_generator.write_prd_frontend(frontend_code)
            print(f"  ✓ Frontend generated: {len(frontend_files)} files")
            return frontend_files
        except Exception as e:
            print(f"  ⚠ Frontend generation failed ({type(e).__name__}), using fallback")
            return {"index.html": self.frontend_generator._generate_fallback_frontend()}

    async def _execute_stories_sequential(
        self,
        stories: List[Story],
        product: ProductAssemblyManager,
        context_docs: Optional[Dict[str, str]] = None,
    ) -> set:
        """
        Execute stories sequentially respecting dependencies.

        Args:
            stories: List of Story objects (with embedded LLM prompts)
            product: ProductAssemblyManager instance
            context_docs: Optional context documents

        Returns:
            Set of completed story IDs
        """
        print("\n[1/5] Generating Backend & Frontend from Stories...")

        # Build dependency graph
        dependency_graph = {s.id: s.depends_on for s in stories}

        total_stories = len(stories)
        completed_ids = set()
        pending = list(stories)
        wave = 1
        # Track global story index (1-based) for progress reporting
        story_index_map = {s.id: i + 1 for i, s in enumerate(stories)}

        while pending:
            # Find stories ready to execute (all dependencies completed)
            ready = [
                s for s in pending
                if all(dep in completed_ids for dep in s.depends_on)
            ]

            if not ready:
                print(f"⚠ Circular dependency: {len(pending)} stories remain blocked")
                break

            print(f"\n  Wave {wave}: Executing {len(ready)} stories...")

            # Execute ready stories in parallel with limited concurrency
            semaphore = asyncio.Semaphore(self.config.worker_pool_size)

            async def limited_generate(story):
                async with semaphore:
                    idx = story_index_map[story.id]
                    return await self._generate_story(
                        story, product, context_docs,
                        story_index=idx, total_stories=total_stories
                    )

            results = await asyncio.gather(
                *[limited_generate(s) for s in ready],
                return_exceptions=True
            )

            # Process results
            for result in results:
                if isinstance(result, Exception):
                    print(f"  ✗ Error: {result}")
                    continue

                story_id = result.story_id
                self.results[story_id] = result

                if result.status == ProductGenerationStatus.COMPLETED:
                    completed_ids.add(story_id)
                    print(f"  ✓ {story_id}: Backend + Frontend generated")
                else:
                    print(f"  ✗ {story_id}: {result.error_message}")

            # Remove completed stories from pending list
            pending = [s for s in pending if s.id not in completed_ids]
            wave += 1

        return completed_ids

    async def _generate_story(
        self,
        story: Story,
        product: ProductAssemblyManager,
        context_docs: Optional[Dict[str, str]] = None,
        story_index: int = 0,
        total_stories: int = 0,
    ) -> StoryGeneration:
        """
        Generate backend code for a single story (TRACK 2 - Backend only).

        Uses the story's embedded llm_prompt directly for code generation,
        bypassing story_translator for pure LLM-prompt-based generation.

        Args:
            story: Story object with embedded LLM prompt for code generators
            product: ProductAssemblyManager instance
            context_docs: Optional context documents (PRD, TRD)
            story_index: 1-based position of this story in the full list
            total_stories: Total number of stories being generated

        Returns:
            StoryGeneration result
        """
        story_id = story.id
        story_name = story.name

        def _cb(msg: str):
            """Fire progress callback if configured."""
            cb = self.config.progress_callback
            if cb and story_index and total_stories:
                try:
                    cb(story_index, total_stories, story_name, msg)
                except Exception:
                    pass

        result = StoryGeneration(
            story_id=story_id,
            story_name=story_name,
            status=ProductGenerationStatus.TRANSLATING,
        )

        try:
            # TRACK 2: Backend-only generation from story.llm_prompt
            # Step 1: Extract tech stack from TRD
            result.status = ProductGenerationStatus.TRANSLATING
            _cb("🔄 Extracting tech stack from TRD")

            trd_content = context_docs.get("TRD", "") if context_docs else ""
            tech_stack = self.backend_generator.extract_tech_stack(trd_content)

            # Step 2: Generate backend code directly from llm_prompt + tech_stack
            result.status = ProductGenerationStatus.GENERATING_BACKEND
            _cb("⚙️ Executing story prompt")
            backend_code_obj = self.backend_generator.execute_story_prompt(
                story.llm_prompt,
                tech_stack
            )

            # Convert GeneratedBackendCode to file dictionary
            backend_code = {}
            backend_code["app/models.py"] = backend_code_obj.models_py
            backend_code["app/routes.py"] = backend_code_obj.main_py_endpoints
            backend_code["tests/conftest.py"] = backend_code_obj.conftest_py
            backend_code["tests/test_routes.py"] = backend_code_obj.test_routes_py
            backend_code["requirements.txt"] = backend_code_obj.requirements_txt
            result.backend_code = backend_code

            # Step 3: Assemble backend code into product
            result.status = ProductGenerationStatus.ASSEMBLING
            for file_path, content in backend_code.items():
                product.add_backend_code(story_id, file_path, content)

            # Register story with basic info
            product.register_story(
                story_id,
                {
                    "name": story_name,
                    "description": story.description,
                    "endpoints": [],  # Would need to parse from llm_prompt or code
                    "pages": [],  # Frontend is separate (TRACK 1)
                }
            )

            # Step 4: Run tests (if configured)
            if self.config.run_tests and self.sandbox and backend_code:
                result.status = ProductGenerationStatus.TESTING
                test_result = await self._run_story_tests(
                    story_id, backend_code
                )
                result.test_results = test_result

                if test_result.returncode != 0:
                    result.status = ProductGenerationStatus.FAILED
                    result.error_message = f"Tests failed: {test_result.stderr}"
                    return result

            result.status = ProductGenerationStatus.COMPLETED
            _cb("✅ Done")

        except Exception as e:
            result.status = ProductGenerationStatus.FAILED
            result.error_message = str(e)
            _cb(f"❌ Failed: {str(e)[:80]}")

        return result

    async def _run_story_tests(
        self,
        story_id: str,
        backend_code: Dict[str, str]
    ) -> CommandResult:
        """
        Run tests for generated backend code.

        Args:
            story_id: Story identifier
            backend_code: Generated backend code files

        Returns:
            CommandResult with test output
        """
        if not self.sandbox:
            raise ValueError("Sandbox not set")

        # Write files to sandbox
        for file_path, content in backend_code.items():
            self.sandbox.write_file(file_path, content)

        # Run tests
        test_result = self.sandbox.run_command("pytest tests/ -v")

        return test_result

    def _product_needs_backend(
        self,
        stories: List[Story],
        context_docs: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Quick check: does ANY story in this product require a backend?
        Uses story translator's detection logic based on PRD/TRD context.
        """
        for story in stories:
            description = story.description or story.name
            success_criteria = story.success_criteria or []
            if self.story_translator._needs_backend(description, success_criteria, context_docs or {}):
                return True
        return False

    def _generate_mandatory_ui(self, product: ProductAssemblyManager) -> None:
        """
        Update navigation based on registered pages.
        - Always: update nav.js with registered pages
        - API explorer only generated for backend products
        """
        try:
            # Generate navigation with registered pages
            product.generate_mandatory_ui()
            print("  ✓ Navigation updated")
        except Exception as e:
            print(f"  ⚠ Navigation generation skipped: {e}")

        try:
            # Generate API explorer
            api_explorer_html = self._generate_api_explorer(product)
            product.add_frontend_component("_mandatory", "api-explorer.html", api_explorer_html)
            print("  ✓ API explorer generated")
        except Exception as e:
            print(f"  ⚠ API explorer generation skipped: {e}")

    def _generate_api_explorer(self, product: ProductAssemblyManager) -> str:
        """
        Generate an interactive API explorer page.
        """
        html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>API Explorer</title>
    <link rel="stylesheet" href="/styles.css">
    <style>
        .endpoint-card {
            padding: 1rem;
            margin: 1rem 0;
            border: 1px solid var(--border-color);
            border-radius: var(--border-radius);
            background: var(--bg-secondary);
        }
        .method {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 4px;
            font-size: 0.875rem;
            font-weight: bold;
        }
        .method-get { background: #4CAF50; color: white; }
        .method-post { background: #2196F3; color: white; }
        .method-put { background: #FF9800; color: white; }
        .method-delete { background: #f44336; color: white; }
        .request-body {
            background: var(--bg-tertiary);
            padding: 1rem;
            border-radius: 4px;
            margin-top: 0.5rem;
            font-family: monospace;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
    </style>
</head>
<body>
    <nav id="navbar"></nav>
    <main id="app-content">
        <div class="page-container">
            <h1>API Explorer</h1>
            <p>Browse and test all generated API endpoints.</p>

            <div id="endpoints-container"></div>
        </div>
    </main>

    <script src="/api.js"></script>
    <script src="/nav.js"></script>
    <script>
        /**
         * API Explorer Page
         * Lists all available endpoints and allows testing them
         */

        async function initApiExplorerPage() {
            const container = document.getElementById('endpoints-container');

            try {
                // Get list of all endpoints
                const response = await fetchAPI('/health');

                // Display endpoints
                displayEndpoints(response);
            } catch (error) {
                container.innerHTML = `<div class="error">Failed to load endpoints: ${error.message}</div>`;
            }
        }

        function displayEndpoints(data) {
            const container = document.getElementById('endpoints-container');
            const endpoints = data.endpoints || [];

            if (endpoints.length === 0) {
                container.innerHTML = '<p>No endpoints found.</p>';
                return;
            }

            container.innerHTML = endpoints.map(endpoint => `
                <div class="endpoint-card">
                    <span class="method method-${endpoint.method.toLowerCase()}">
                        ${endpoint.method}
                    </span>
                    <code>${endpoint.path}</code>
                    <p>${endpoint.description}</p>
                    <button onclick="testEndpoint('${endpoint.path}', '${endpoint.method}')">
                        Test Endpoint
                    </button>
                </div>
            `).join('');
        }

        async function testEndpoint(path, method) {
            try {
                const options = { method };
                if (method !== 'GET') {
                    options.body = JSON.stringify({ test: true });
                }

                const response = await fetchAPI(path, options);
                alert(`Response: ${JSON.stringify(response, null, 2)}`);
            } catch (error) {
                alert(`Error: ${error.message}`);
            }
        }

        // Initialize when DOM is ready
        document.addEventListener('DOMContentLoaded', initApiExplorerPage);
    </script>
</body>
</html>
"""
        return html

    async def validate_product(self, product_path: str) -> ProductValidatorResponse:
        """
        Validate a generated product.

        Args:
            product_path: Path to the generated product

        Returns:
            ProductValidatorResponse with validation results
        """
        # This would implement comprehensive product validation
        # Including API endpoint testing, frontend rendering, etc.
        pass
