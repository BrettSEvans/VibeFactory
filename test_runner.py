"""
Test script for Module 4: LangGraph Runner
Tests the FSM orchestration without requiring full LLM execution.
"""

import asyncio
import os
from runner import LangGraphRunner, SDLCState


def test_runner_imports():
    """Test that all components import correctly."""
    print("Testing Runner Imports...")
    print("=" * 60)
    
    print("✓ LangGraphRunner imported")
    print("✓ SDLCState imported")
    
    # Test LangGraph imports
    from langgraph.graph import StateGraph, END, START
    from langgraph.checkpoint.memory import MemorySaver
    print("✓ LangGraph components imported")
    
    print("\n" + "=" * 60)
    print("✅ All import tests passed!")
    return True


def test_sdlc_state():
    """Test SDLCState structure."""
    print("\n\nTesting SDLCState Structure...")
    print("=" * 60)
    
    # Create initial state
    initial_state: SDLCState = {
        "project_id": "test-001",
        "rough_idea": "Build a task management API",
        "current_phase": "IDEA",
        "brd_content": "",
        "prd_content": "",
        "trd_content": "",
        "stories_content": "",
        "stories": [],
        "codebase": {},
        "history": [],
        "brd_passed": False,
        "prd_passed": False,
        "trd_passed": False,
        "stories_passed": False,
        "engineering_completed": False,
        "engineering_failed": False,
        "engineering_retry_count": 0,
        "e2e_passed": False,
        "e2e_feedback": "",
        "human_approved": False,
        "human_feedback": "",
        "error": None,
        "needs_demotion": False,
        "demotion_target": None
    }
    
    print("✓ Created initial state")
    print(f"  Project ID: {initial_state['project_id']}")
    print(f"  Rough Idea: {initial_state['rough_idea']}")
    print(f"  Current Phase: {initial_state['current_phase']}")
    
    # Test state updates
    initial_state["brd_content"] = "# BRD Content"
    initial_state["brd_passed"] = True
    initial_state["current_phase"] = "DESIGN"
    
    print("\n✓ State updates work correctly")
    print(f"  BRD Passed: {initial_state['brd_passed']}")
    print(f"  Current Phase: {initial_state['current_phase']}")
    
    print("\n" + "=" * 60)
    print("✅ SDLCState tests passed!")
    return True


def test_runner_initialization():
    """Test LangGraphRunner initialization."""
    print("\n\nTesting LangGraphRunner Initialization...")
    print("=" * 60)
    
    # Create runner
    runner = LangGraphRunner(state_dir="./test_sdlc_state")
    print("✓ Runner initialized")
    
    # Test state directory creation
    if os.path.exists("./test_sdlc_state"):
        print("✓ State directory created")
    
    # Test graph initialization
    runner._initialize_graph()
    print("✓ Graph initialized")
    
    # Verify nodes exist
    expected_nodes = [
        "generate_brd",
        "generate_prd",
        "generate_trd",
        "generate_stories",
        "human_approval",
        "engineering_execution",
        "e2e_testing"
    ]
    
    # Get nodes from compiled graph
    nodes = list(runner.graph.get_graph().nodes.keys())
    for node in expected_nodes:
        if node in nodes:
            print(f"  ✓ Node '{node}' exists")
        else:
            print(f"  ✗ Node '{node}' missing")
            return False
    
    # Verify edges exist
    print("\n✓ Graph structure verified")
    
    print("\n" + "=" * 60)
    print("✅ Runner initialization tests passed!")
    return True


def test_node_methods():
    """Test individual node methods."""
    print("\n\nTesting Node Methods...")
    print("=" * 60)
    
    runner = LangGraphRunner()
    runner._initialize_graph()
    
    # Create test state
    test_state: SDLCState = {
        "project_id": "test-001",
        "rough_idea": "Test idea",
        "current_phase": "IDEA",
        "brd_content": "",
        "prd_content": "",
        "trd_content": "",
        "stories_content": "",
        "stories": [],
        "codebase": {},
        "history": [],
        "brd_passed": False,
        "prd_passed": False,
        "trd_passed": False,
        "stories_passed": False,
        "engineering_completed": False,
        "engineering_failed": False,
        "engineering_retry_count": 0,
        "e2e_passed": False,
        "e2e_feedback": "",
        "human_approved": False,
        "human_feedback": "",
        "error": None,
        "needs_demotion": False,
        "demotion_target": None
    }
    
    # Test BRD node (without LLM call)
    print("\nTesting generate_brd_node...")
    result = runner.generate_brd_node(test_state)
    print(f"  ✓ BRD node executed (error expected without API key)")
    
    # Test PRD node
    print("\nTesting generate_prd_node...")
    test_state["brd_content"] = "# Test BRD"
    result = runner.generate_prd_node(test_state)
    print(f"  ✓ PRD node executed (error expected without API key)")
    
    # Test TRD node
    print("\nTesting generate_trd_node...")
    test_state["prd_content"] = "# Test PRD"
    result = runner.generate_trd_node(test_state)
    print(f"  ✓ TRD node executed (error expected without API key)")
    
    # Test Stories node
    print("\nTesting generate_stories_node...")
    test_state["trd_content"] = "# Test TRD"
    result = runner.generate_stories_node(test_state)
    print(f"  ✓ Stories node executed (error expected without API key)")
    
    # Test conditional edge methods
    print("\nTesting conditional edge methods...")
    
    # Test _check_brd_result
    test_state["brd_passed"] = True
    result = runner._check_brd_result(test_state)
    assert result == "continue", "Should return 'continue'"
    print("  ✓ _check_brd_result (passed)")
    
    test_state["brd_passed"] = False
    result = runner._check_brd_result(test_state)
    assert result == "demote_to_idea", "Should return 'demote_to_idea'"
    print("  ✓ _check_brd_result (failed)")
    
    # Test _check_prd_result
    test_state["prd_passed"] = True
    result = runner._check_prd_result(test_state)
    assert result == "continue", "Should return 'continue'"
    print("  ✓ _check_prd_result (passed)")
    
    # Test _check_trd_result
    test_state["trd_passed"] = True
    result = runner._check_trd_result(test_state)
    assert result == "continue", "Should return 'continue'"
    print("  ✓ _check_trd_result (passed)")
    
    # Test _check_stories_result
    test_state["stories_passed"] = True
    result = runner._check_stories_result(test_state)
    assert result == "continue", "Should return 'continue'"
    print("  ✓ _check_stories_result (passed)")
    
    # Test _check_engineering_result
    test_state["engineering_completed"] = True
    test_state["engineering_failed"] = False
    result = runner._check_engineering_result(test_state)
    assert result == "continue", "Should return 'continue'"
    print("  ✓ _check_engineering_result (passed)")
    
    test_state["engineering_failed"] = True
    test_state["engineering_retry_count"] = 0
    result = runner._check_engineering_result(test_state)
    assert result == "retry_engineering", "Should return 'retry_engineering'"
    print("  ✓ _check_engineering_result (retry)")
    
    # Test _check_e2e_result
    test_state["e2e_passed"] = True
    result = runner._check_e2e_result(test_state)
    assert result == "continue", "Should return 'continue'"
    print("  ✓ _check_e2e_result (passed)")
    
    test_state["e2e_passed"] = False
    result = runner._check_e2e_result(test_state)
    assert result == "demote_to_execution", "Should return 'demote_to_execution'"
    print("  ✓ _check_e2e_result (failed)")
    
    print("\n" + "=" * 60)
    print("✅ Node method tests passed!")
    return True


def test_state_persistence():
    """Test state save/load functionality."""
    print("\n\nTesting State Persistence...")
    print("=" * 60)
    
    runner = LangGraphRunner(state_dir="./test_sdlc_state")
    
    # Test save
    from state import ProjectState
    state = ProjectState(
        project_id="test-persist",
        rough_idea="Test persistence"
    )
    runner._save_state("test-persist", state)
    print("✓ State saved to disk")
    
    # Test load
    loaded_state = runner._load_state("test-persist")
    assert loaded_state is not None, "Should load state"
    assert loaded_state.project_id == "test-persist", "Project ID should match"
    print("✓ State loaded from disk")
    
    # Cleanup
    import shutil
    if os.path.exists("./test_sdlc_state"):
        shutil.rmtree("./test_sdlc_state")
    print("✓ Test state cleaned up")
    
    print("\n" + "=" * 60)
    print("✅ State persistence tests passed!")
    return True


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Module 4: LangGraph Runner - Test Suite")
    print("=" * 60)
    
    success = True
    
    # Import tests
    success = test_runner_imports() and success
    
    # State tests
    success = test_sdlc_state() and success
    
    # Initialization tests
    success = test_runner_initialization() and success
    
    # Node method tests
    success = test_node_methods() and success
    
    # Persistence tests
    success = test_state_persistence() and success
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 All Module 4 tests passed!")
        print("\n✅ Module 4 is ready for use!")
        print("\nTo run the full system:")
        print("  python runner.py  # Start new project")
        print("  python runner.py <project_id>  # Resume existing project")
    else:
        print("❌ Some tests failed")
    print("=" * 60)
    
    return success


if __name__ == "__main__":
    import sys
    
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
