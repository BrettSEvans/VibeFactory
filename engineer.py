"""
Module 3: Engineering & Execution
Handles Phase 5 (EXECUTION) and Phase 6 (E2E_TESTING).
Implements async worker pools for parallel story execution.
"""

import asyncio
import os
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pydantic import BaseModel, Field
import instructor
import litellm
from state import ProjectState, Document
from sandbox import ProjectSandbox, CommandResult


class ExecutionStatus(Enum):
    """Status of story execution."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class ValidatorResponse(BaseModel):
    """Response from security/QA validator."""
    passed: bool = Field(..., description="Whether code passes security and QA review")
    feedback: str = Field(..., description="Detailed feedback on issues found")


class E2EResponse(BaseModel):
    """Response from E2E test execution."""
    passed: bool = Field(..., description="Whether E2E tests passed")
    feedback: str = Field(..., description="Details about E2E test results")


@dataclass
class StoryResult:
    """Result of executing a single story."""
    story_id: str
    status: ExecutionStatus
    app_code: str = ""
    test_code: str = ""
    pytest_output: str = ""
    retry_count: int = 0
    error_message: str = ""


@dataclass
class ExecutionMetrics:
    """Metrics for execution phase."""
    total_stories: int = 0
    completed: int = 0
    failed: int = 0
    blocked: int = 0
    total_retries: int = 0


class EngineerConfig(BaseModel):
    """Configuration for the engineer."""
    llm_model: str = Field(default="meta-llama/llama-3.3-70b-instruct:free", description="LLM model to use")
    api_key: Optional[str] = Field(default=None, description="API key for LLM (OpenRouter API key)")
    max_retries: int = Field(default=3, ge=1, description="Maximum retry attempts per story")
    validator_pass_score: int = Field(default=7, ge=1, le=10, description="Minimum validator score")
    worker_pool_size: int = Field(default=4, ge=1, description="Number of parallel workers")


class CodeEngineer:
    """
    Handles code generation, execution, and E2E testing.
    Implements async worker pool for parallel story execution.
    """

    # Engineer Agent Prompts
    ENGINEER_SYS = """You are a Senior Python Developer.

**Available Skills:**
* **file_writer**: Write code directly to the /app directory, following the project's module structure.
* **test_generator**: Draft pytest files based on story success criteria — each test must verify a real, specific requirement.
* **dependency_installer**: Invoke pip install within the execution environment to add required packages.

**Rules of Conduct:**
* SHOULD write clean code following PEP 8 standards — consistent naming, type hints, and docstrings on all public functions.
* SHOULD ensure all code is modular and imports from other app/ modules correctly using relative imports.
* SHOULD NOT write "mock" tests that always pass (e.g., assert True). Every test must verify a real requirement from the success criteria.
* SHOULD assess the TRD before generating code — if the product is static HTML, generate only HTML/CSS/JS files with no backend."""

    ENGINEER_USER = "Implement story. Return code and pytest. Story: {description}. Success Criteria: {success_criteria}."

    # Security & QA Validator Prompts
    VALIDATOR_SYS = """You are a Security Auditor and QA Lead.

**Available Skills:**
* **static_analysis_tool**: Simulate a security scan checking for common vulnerabilities: eval(), os.system(), hardcoded passwords, raw SQL strings, and unvalidated user inputs.
* **log_analyzer**: Parse pytest output to identify specific line numbers and root causes of failures.

**Rules of Conduct:**
* SHOULD be adversarial — actively try to find ways the engineer's code might break or expose data.
* SHOULD reject any test file that uses assert True, assert 1 == 1, or similarly trivial assertions that lack meaningful coverage.
* SHOULD provide specific, actionable feedback on how to fix security flaws (e.g., "Use psycopg2 parameter binding instead of string interpolation to prevent SQL injection").
* SHOULD flag passed=False if any endpoint lacks input validation or if database queries use raw string formatting."""

    VALIDATOR_USER = "Review code. Reject if tests are superficial (assert True) or if there are security flaws. Code: {app_code}. Tests: {test_code}."

    # E2E Agent Prompts
    E2E_SYS = """You are a QA Automation Engineer.

**Available Skills:**
* **log_analyzer**: Parse application logs and test output to identify specific line numbers and failure patterns.

**Rules of Conduct:**
* SHOULD be adversarial — test boundary conditions, invalid inputs, and unauthorized access attempts, not just the happy path.
* SHOULD write E2E tests that verify actual business requirements from the PRD, not generic health checks.
* SHOULD NOT write tests that always pass regardless of application state (e.g., assert response is not None).
* SHOULD provide specific failure details including the endpoint, payload, expected vs. actual response."""

    E2E_USER = "Generate a complete End-to-End test script using requests that hits live application endpoints based on this PRD: {source_material}"

    def __init__(
        self,
        config: Optional[EngineerConfig] = None,
        state: Optional[ProjectState] = None,
        sandbox: Optional[ProjectSandbox] = None
    ):
        """
        Initialize the code engineer.

        Args:
            config: Configuration for LLM and execution
            state: Project state to work with
            sandbox: Sandbox for code execution
        """
        self.config = config or EngineerConfig()
        self.state = state
        self.sandbox = sandbox
        self._setup_client()
        self._results: Dict[str, StoryResult] = {}
        self._metrics = ExecutionMetrics()

    def _setup_client(self) -> None:
        """Initialize the instructor-enhanced LLM client."""
        api_key = self.config.api_key or os.getenv("OPENAI_API_KEY")
        self.api_key = api_key  # Store locally instead of global mutation

        self.client = instructor.from_litellm(
            litellm.completion,
            mode=instructor.Mode.TOOLS
        )

    def set_state(self, state: ProjectState) -> None:
        """Set the project state."""
        self.state = state

    def set_sandbox(self, sandbox: ProjectSandbox) -> None:
        """Set the sandbox for execution."""
        self.sandbox = sandbox

    async def execute_all_stories(self) -> Dict[str, StoryResult]:
        """
        Execute all stories from the project state using async worker pool.

        Returns:
            Dict mapping story IDs to results
        """
        if not self.state:
            raise ValueError("Project state not set")

        if not self.sandbox:
            raise ValueError("Sandbox not set")

        # Get stories from state
        stories = self.state.stories
        if not stories:
            print("No stories found in project state")
            return self._results

        self._metrics.total_stories = len(stories)
        print(f"Starting execution of {len(stories)} stories...")

        # Build dependency graph
        dependency_graph = self._build_dependency_graph(stories)

        # Track completed story IDs and remaining stories
        completed_ids: Set[str] = set()
        pending_stories = list(stories)

        # Execute with worker pool limit
        print(f"Using worker pool size: {self.config.worker_pool_size}")

        # Process tasks with semaphore for concurrency limit
        semaphore = asyncio.Semaphore(self.config.worker_pool_size)

        async def limited_execute(coro):
            async with semaphore:
                return await coro

        # Execute stories in waves as dependencies complete
        wave = 1
        while pending_stories:
            # Find stories ready to execute (all deps completed)
            ready_stories = [
                s for s in pending_stories
                if all(dep in completed_ids for dep in s.get("depends_on", []))
            ]

            if not ready_stories:
                # Circular dependency or all remaining blocked
                print(f"⚠ Circular dependency detected. {len(pending_stories)} stories remain blocked.")
                break

            print(f"\n--- Execution Wave {wave} ({len(ready_stories)} stories) ---")

            # Create tasks for this wave
            tasks = [self._execute_story(s, completed_ids) for s in ready_stories]

            # Execute this wave
            results = await asyncio.gather(*[limited_execute(t) for t in tasks], return_exceptions=True)

            # Process results
            for result in results:
                if isinstance(result, Exception):
                    print(f"Error executing story: {result}")
                    continue

                story_result = result
                self._results[story_result.story_id] = story_result

                if story_result.status == ExecutionStatus.COMPLETED:
                    completed_ids.add(story_result.story_id)
                    self._metrics.completed += 1
                elif story_result.status == ExecutionStatus.FAILED:
                    self._metrics.failed += 1
                elif story_result.status == ExecutionStatus.BLOCKED:
                    self._metrics.blocked += 1

            # Remove completed stories from pending
            pending_stories = [s for s in pending_stories if s.get("id", s.get("story_id", "")) not in completed_ids]
            wave += 1

        print(f"\nExecution complete:")
        print(f"  Completed: {self._metrics.completed}")
        print(f"  Failed: {self._metrics.failed}")
        print(f"  Blocked: {self._metrics.blocked}")
        print(f"  Total retries: {self._metrics.total_retries}")

        return self._results

    def _build_dependency_graph(self, stories: List[Dict]) -> Dict[str, List[str]]:
        """Build a dependency graph from stories."""
        graph = {}
        for story in stories:
            story_id = story.get("id", story.get("story_id", ""))
            depends_on = story.get("depends_on", [])
            graph[story_id] = depends_on
        return graph

    async def _execute_story(
        self,
        story: Dict,
        completed_ids: Set[str]
    ) -> StoryResult:
        """
        Execute a single story through the Engineer & Validator loop.

        Args:
            story: Story definition dict
            completed_ids: Set of already completed story IDs

        Returns:
            StoryResult with execution details
        """
        story_id = story.get("id", story.get("story_id", ""))
        description = story.get("description", story.get("name", ""))
        success_criteria = story.get("success_criteria", "")

        print(f"\nExecuting story: {story_id}")
        print(f"  Description: {description[:60]}...")

        result = StoryResult(
            story_id=story_id,
            status=ExecutionStatus.PENDING
        )

        # Engineer & Validator Loop
        for attempt in range(self.config.max_retries):
            result.retry_count = attempt
            
            # Step 1: Engineer Agent - Write code and tests
            print(f"  Attempt {attempt + 1}/{self.config.max_retries}: Generating code...")
            app_code, test_code = await self._generate_code(story)
            result.app_code = app_code
            result.test_code = test_code

            # Step 2: Security & QA Validator
            print(f"  Validating code...")
            validation = await self._validate_code(app_code, test_code)
            
            if not validation.passed:
                print(f"  Validation failed: {validation.feedback[:100]}...")
                # Feed feedback back to engineer for next attempt
                continue

            # Step 3: Execute in Sandbox
            print(f"  Running pytest...")
            pytest_result = await self._run_tests(app_code, test_code)
            result.pytest_output = pytest_result.stdout

            if pytest_result.returncode == 0:
                # Success!
                result.status = ExecutionStatus.COMPLETED
                print(f"  ✓ Story {story_id} completed successfully")
                break
            else:
                # Test failed, feed error back to engineer
                print(f"  Tests failed, retrying...")
                self._metrics.total_retries += 1
                
                if attempt >= self.config.max_retries - 1:
                    # Max retries exceeded
                    result.status = ExecutionStatus.FAILED
                    result.error_message = pytest_result.stderr
                    print(f"  ✗ Story {story_id} failed after {self.config.max_retries} attempts")
                else:
                    # Feed stderr back to engineer for next attempt
                    story["last_error"] = pytest_result.stderr

        return result

    async def _generate_code(self, story: Dict) -> Tuple[str, str]:
        """
        Generate application code and pytest using Engineer Agent.

        Returns:
            Tuple of (app_code, test_code)
        """
        description = story.get("description", story.get("name", ""))
        success_criteria = story.get("success_criteria", "")
        last_error = story.get("last_error", "")

        user_prompt = self.ENGINEER_USER.format(
            description=description,
            success_criteria=success_criteria
        )

        if last_error:
            user_prompt += f"\n\nPrevious attempt failed with: {last_error}"

        messages = [
            {"role": "system", "content": self.ENGINEER_SYS},
            {"role": "user", "content": user_prompt}
        ]

        response = self.client.chat.completions.create(
            model=self.config.llm_model,
            messages=messages,
            max_tokens=8000,
            temperature=0.7
        )

        content = response.choices[0].message.content
        
        # Parse the response to extract code and tests
        # Expected format:
        # ```python
        # # App code here
        # ```
        #
        # ```python
        # # Test code here
        # ```
        
        app_code = ""
        test_code = ""
        
        # Simple parsing - look for code blocks
        import re
        code_blocks = re.findall(r'```python\s*(.*?)\s*```', content, re.DOTALL)
        
        if len(code_blocks) >= 2:
            app_code = code_blocks[0].strip()
            test_code = code_blocks[1].strip()
        elif len(code_blocks) == 1:
            # Assume first block is app code, generate tests separately
            app_code = code_blocks[0].strip()
        
        if not app_code or not test_code:
            # Fallback: use entire response
            app_code = content
            test_code = "# Tests not generated"

        return app_code, test_code

    async def _validate_code(self, app_code: str, test_code: str) -> ValidatorResponse:
        """
        Validate code using Security & QA Validator.
        Uses instructor for structured JSON output.
        """
        user_prompt = self.VALIDATOR_USER.format(
            app_code=app_code,
            test_code=test_code
        )

        messages = [
            {"role": "system", "content": self.VALIDATOR_SYS},
            {"role": "user", "content": user_prompt}
        ]

        try:
            response = self.client.chat.completions.create(
                model=self.config.llm_model,
                messages=messages,
                response_model=ValidatorResponse,
                max_tokens=500,
                temperature=0.3
            )
            return response
        except Exception as e:
            print(f"Validation error: {e}")
            # Return failed validation on error
            return ValidatorResponse(
                passed=False,
                feedback=f"Validation error: {str(e)}"
            )

    async def _run_tests(self, app_code: str, test_code: str) -> CommandResult:
        """
        Run tests in the sandbox.

        Returns:
            CommandResult with test output
        """
        if not self.sandbox:
            raise ValueError("Sandbox not set")

        # Write app code
        self.sandbox.write_file("app/main.py", app_code)
        
        # Write test code
        self.sandbox.write_file("tests/test_main.py", test_code)
        
        # Run pytest
        result = self.sandbox.run_command("pytest tests/ -v")
        
        return result

    async def run_e2e_tests(self) -> Tuple[bool, str]:
        """
        Run End-to-End tests after all stories complete.

        Returns:
            Tuple of (passed, feedback)
        """
        if not self.state:
            raise ValueError("Project state not set")

        if not self.sandbox:
            raise ValueError("Sandbox not set")

        print("\n" + "=" * 50)
        print("Running End-to-End Tests...")
        print("=" * 50)

        # Get PRD for context
        prd_doc = self.state.get_document("PRD")
        if not prd_doc:
            print("⚠ No PRD found for E2E generation")
            return False, "No PRD document found"

        prd_content = prd_doc.content

        # Step 1: Generate E2E test script
        print("Generating E2E test script...")
        e2e_script = await self._generate_e2e_script(prd_content)

        if not e2e_script:
            return False, "Failed to generate E2E script"

        # Step 2: Write E2E script to sandbox
        self.sandbox.write_file("tests/e2e_test.py", e2e_script)

        # Step 3: Start app in background
        print("Starting application...")
        app_process = await self._start_app_in_sandbox()

        if not app_process:
            return False, "Failed to start application"

        # Step 4: Run E2E tests
        print("Running E2E tests...")
        e2e_result = self.sandbox.run_command("python tests/e2e_test.py")

        # Step 5: Tear down
        await self._tear_down_app(app_process)

        # Step 6: Validate results
        if e2e_result.returncode == 0:
            print("✓ E2E tests passed")
            return True, "All E2E tests passed"
        else:
            print(f"✗ E2E tests failed: {e2e_result.stderr[:200]}")
            return False, f"E2E tests failed: {e2e_result.stderr}"

    async def _generate_e2e_script(self, prd_content: str) -> Optional[str]:
        """
        Generate E2E test script using E2E Agent.
        """
        user_prompt = self.E2E_USER.format(source_material=prd_content)

        messages = [
            {"role": "system", "content": self.E2E_SYS},
            {"role": "user", "content": user_prompt}
        ]

        try:
            response = self.client.chat.completions.create(
                model=self.config.llm_model,
                messages=messages,
                max_tokens=4000,
                temperature=0.7
            )

            content = response.choices[0].message.content
            
            # Extract code block
            import re
            code_blocks = re.findall(r'```python\s*(.*?)\s*```', content, re.DOTALL)
            
            if code_blocks:
                return code_blocks[0].strip()
            return content

        except Exception as e:
            print(f"E2E generation error: {e}")
            return None

    async def _start_app_in_sandbox(self) -> Optional[str]:
        """
        Start the application in the sandbox.
        Returns the process ID or identifier.
        """
        if not self.sandbox:
            return None

        # TODO: Implement real app startup
        # This should look for start.sh, app.py, or other entry point
        # For now, attempt to find and run a startup script
        start_script = self.sandbox.get_file("start.sh")
        if start_script:
            result = self.sandbox.run_command(["bash", "start.sh"], workdir="/workspace")
        else:
            # Try to run app.py if it exists
            app_file = self.sandbox.get_file("app/main.py")
            if app_file:
                result = self.sandbox.run_command(["python", "app/main.py"], workdir="/workspace", timeout=5)
            else:
                print("⚠ No startup script or app/main.py found. E2E tests will fail.")
                return None

        if result.returncode == 0:
            return "app_process_1"
        return None

    async def _tear_down_app(self, app_process: str) -> None:
        """
        Tear down the application.
        """
        if not self.sandbox:
            return

        # Kill background processes more carefully (only the app, not all Python)
        try:
            # Try killing the specific process by name (less destructive)
            self.sandbox.run_command(["pkill", "-f", "app/main.py"], timeout=5)
        except Exception:
            pass

        try:
            # Fallback: kill any http.server
            self.sandbox.run_command(["pkill", "-f", "http.server"], timeout=5)
        except Exception:
            pass

    def get_metrics(self) -> ExecutionMetrics:
        """Get execution metrics."""
        return self._metrics

    def get_results(self) -> Dict[str, StoryResult]:
        """Get all execution results."""
        return self._results

    def demote_on_failure(self, target_phase: str, reason: str) -> None:
        """
        Demote project state on critical failure.
        """
        if self.state:
            self.state.demote(target_phase, reason)
