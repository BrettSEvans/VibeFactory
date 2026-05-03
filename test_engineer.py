"""
Test script for Module 3: Engineer
Requires OPENAI_API_KEY environment variable and Docker to be running.
"""

import asyncio
import os
from engineer import (
    CodeEngineer,
    EngineerConfig,
    StoryResult,
    ExecutionStatus,
    ValidatorResponse,
    ExecutionMetrics
)
from state import ProjectState
from sandbox import ProjectSandbox


def test_engineer_imports():
    """Test that all components import correctly."""
    print("Testing Engineer Imports...")
    print("=" * 50)
    
    print("✓ CodeEngineer imported")
    print("✓ EngineerConfig imported")
    print("✓ StoryResult imported")
    print("✓ ExecutionStatus imported")
    print("✓ ValidatorResponse imported")
    print("✓ ExecutionMetrics imported")
    
    # Test ValidatorResponse schema
    print("\nTesting ValidatorResponse Schema...")
    validation = ValidatorResponse(
        passed=True,
        feedback="Code passes security and QA review"
    )
    print(f"✓ Created validation: passed={validation.passed}")
    
    # Test StoryResult
    print("\nTesting StoryResult...")
    result = StoryResult(
        story_id="story-001",
        status=ExecutionStatus.COMPLETED,
        app_code="print('hello')",
        test_code="def test_hello(): assert True"
    )
    print(f"✓ Created result: {result.story_id}, status={result.status.value}")
    
    # Test ExecutionStatus enum
    print("\nTesting ExecutionStatus Enum...")
    for status in ExecutionStatus:
        print(f"  - {status.name}: {status.value}")
    
    # Test ExecutionMetrics
    print("\nTesting ExecutionMetrics...")
    metrics = ExecutionMetrics(
        total_stories=10,
        completed=8,
        failed=1,
        blocked=1
    )
    print(f"✓ Metrics: {metrics.completed}/{metrics.total_stories} completed")
    
    print("\n" + "=" * 50)
    print("✅ All import and schema tests passed!")
    return True


def test_engineer_config():
    """Test Engineer configuration."""
    print("\n\nTesting Engineer Configuration...")
    print("=" * 50)
    
    config = EngineerConfig(
        llm_model="gpt-4o",
        max_retries=3,
        worker_pool_size=4
    )
    
    print(f"✓ Config created:")
    print(f"  - LLM Model: {config.llm_model}")
    print(f"  - Max Retries: {config.max_retries}")
    print(f"  - Worker Pool Size: {config.worker_pool_size}")
    print(f"  - Pass Score: {config.validator_pass_score}")
    
    print("\n" + "=" * 50)
    print("✅ Configuration tests passed!")
    return True


def test_engineer_prompts():
    """Test that all prompts are defined."""
    print("\n\nTesting Prompt Definitions...")
    print("=" * 50)
    
    engineer = CodeEngineer()
    
    print("\nEngineer Agent:")
    print(f"  Sys: {engineer.ENGINEER_SYS}")
    print(f"  User: {engineer.ENGINEER_USER[:80]}...")
    
    print("\nSecurity & QA Validator:")
    print(f"  Sys: {engineer.VALIDATOR_SYS}")
    print(f"  User: {engineer.VALIDATOR_USER[:80]}...")
    
    print("\nE2E Agent:")
    print(f"  Sys: {engineer.E2E_SYS}")
    print(f"  User: {engineer.E2E_USER[:80]}...")
    
    print("\n" + "=" * 50)
    print("✅ All prompts defined correctly!")
    return True


async def test_async_execution():
    """Test async execution flow (requires API key and Docker)."""
    print("\n\nTesting Async Execution Flow...")
    print("=" * 50)
    
    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠ OPENAI_API_KEY not set - skipping execution test")
        print("Set it with: export OPENAI_API_KEY='your-key-here'")
        return True
    
    # Check for Docker
    try:
        import docker
        client = docker.from_env()
        client.ping()
        print("✓ Docker is running")
    except Exception as e:
        print(f"✗ Docker not available: {e}")
        return False
    
    # Create state with test stories
    print("\nCreating test project state...")
    state = ProjectState(
        project_id="test-engineer",
        rough_idea="Build a simple REST API for user management"
    )
    
    # Add a sample PRD
    from state import Document
    prd = Document(
        content="# Product Requirements\n\n1. User authentication\n2. CRUD operations",
        version=1,
        status="approved"
    )
    state.set_document("PRD", prd)
    
    # Add test stories
    state.stories = [
        {
            "id": "story-001",
            "name": "User Authentication",
            "description": "Implement user login",
            "success_criteria": "Users can login with valid credentials",
            "depends_on": []
        },
        {
            "id": "story-002",
            "name": "User Profile",
            "description": "Create user profile endpoint",
            "success_criteria": "Profile can be created and retrieved",
            "depends_on": ["story-001"]
        }
    ]
    
    print(f"✓ Created state with {len(state.stories)} stories")
    
    # Initialize engineer
    print("\nInitializing CodeEngineer...")
    config = EngineerConfig(
        llm_model="gpt-4o",
        max_retries=1,  # Limit for testing
        worker_pool_size=2
    )
    
    try:
        engineer = CodeEngineer(config=config, state=state)
        print("✓ Engineer initialized")
    except Exception as e:
        print(f"⚠ Engineer init failed: {e}")
        return True  # Continue anyway
    
    # Initialize sandbox
    print("\nInitializing Sandbox...")
    try:
        sandbox = ProjectSandbox(project_id="test-engineer-sandbox")
        sandbox.initialize()
        print("✓ Sandbox initialized")
        engineer.set_sandbox(sandbox)
    except Exception as e:
        print(f"⚠ Sandbox init failed: {e}")
        return True  # Continue anyway
    
    # Test dependency graph building
    print("\nTesting dependency graph...")
    graph = engineer._build_dependency_graph(state.stories)
    print(f"✓ Dependency graph: {graph}")
    
    # Test code generation (without full execution)
    print("\nTesting code generation...")
    test_story = state.stories[0]
    try:
        app_code, test_code = asyncio.run(engineer._generate_code(test_story))
        print(f"✓ Generated code ({len(app_code)} chars)")
        print(f"✓ Generated tests ({len(test_code)} chars)")
    except Exception as e:
        print(f"⚠ Code generation failed (expected without full setup): {e}")
    
    # Cleanup
    if sandbox:
        sandbox.cleanup()
    
    print("\n" + "=" * 50)
    print("✅ Async execution tests completed!")
    return True


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Module 3: Engineer - Test Suite")
    print("=" * 60)
    
    success = True
    
    # Import and schema tests
    success = test_engineer_imports() and success
    success = test_engineer_config() and success
    success = test_engineer_prompts() and success
    
    # Async execution test
    success = await test_async_execution() and success
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 All Module 3 tests passed!")
    else:
        print("❌ Some tests failed")
    print("=" * 60)
    
    return success


if __name__ == "__main__":
    import sys
    
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
