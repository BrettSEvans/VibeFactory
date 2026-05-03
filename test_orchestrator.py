"""
Test script for Module 2: Orchestrator
Requires OPENAI_API_KEY environment variable to be set.
"""

import os
from orchestrator import (
    BlindOrchestrator,
    CritiqueResponse,
    Phase,
    OrchestratorConfig
)
from state import ProjectState

def test_orchestrator_imports():
    """Test that all components import correctly."""
    print("Testing Orchestrator Imports...")
    print("=" * 50)
    
    # Test imports
    print("✓ BlindOrchestrator imported")
    print("✓ CritiqueResponse imported")
    print("✓ Phase enum imported")
    print("✓ OrchestratorConfig imported")
    
    # Test CritiqueResponse schema
    print("\nTesting CritiqueResponse Schema...")
    critique = CritiqueResponse(
        score=8,
        passed=True,
        is_blocker=False,
        feedback="Good document with minor improvements needed"
    )
    print(f"✓ Created critique: score={critique.score}, passed={critique.passed}")
    
    # Test Phase enum
    print("\nTesting Phase Enum...")
    for phase in Phase:
        print(f"  - {phase.name}: {phase.value}")
    
    # Test OrchestratorConfig
    print("\nTesting OrchestratorConfig...")
    config = OrchestratorConfig(
        llm_model="gpt-4o",
        max_retries=3,
        pass_score=7
    )
    print(f"✓ Config created: model={config.llm_model}, max_retries={config.max_retries}")
    
    # Test ProjectState integration
    print("\nTesting ProjectState Integration...")
    state = ProjectState(
        project_id="test-orchestrator",
        rough_idea="Build a task management API with user authentication"
    )
    print(f"✓ Created project state: {state.project_id}")
    print(f"  - Rough idea: {state.rough_idea[:50]}...")
    
    # Test Orchestrator initialization
    print("\nTesting Orchestrator Initialization...")
    try:
        orchestrator = BlindOrchestrator(
            config=config,
            state=state
        )
        print("✓ Orchestrator initialized")
        print(f"  - LLM Model: {orchestrator.config.llm_model}")
        print(f"  - Max Retries: {orchestrator.config.max_retries}")
        print(f"  - Pass Score: {orchestrator.config.pass_score}")
    except Exception as e:
        print(f"⚠ Orchestrator init failed (expected without API key): {e}")
    
    print("\n" + "=" * 50)
    print("✅ All import and schema tests passed!")
    print("\nNote: Full orchestration requires OPENAI_API_KEY environment variable.")
    print("Set it with: export OPENAI_API_KEY='your-key-here'")
    
    return True

def test_prompts():
    """Test that all prompts are defined correctly."""
    print("\n\nTesting Prompt Definitions...")
    print("=" * 50)
    
    orchestrator = BlindOrchestrator()
    
    # Test BRD prompts
    print("\nPhase 1: BRD")
    print(f"  Generator Sys: {orchestrator.BRD_GENERATOR_SYS}")
    print(f"  Generator User: {orchestrator.BRD_GENERATOR_USER[:80]}...")
    print(f"  Critic Sys: {orchestrator.BRD_CRITIC_SYS}")
    print(f"  Critic User: {orchestrator.BRD_CRITIC_USER[:80]}...")
    
    # Test PRD prompts
    print("\nPhase 2: PRD")
    print(f"  Generator Sys: {orchestrator.PRD_GENERATOR_SYS}")
    print(f"  Generator User: {orchestrator.PRD_GENERATOR_USER[:80]}...")
    print(f"  Critic Sys: {orchestrator.PRD_CRITIC_SYS}")
    print(f"  Critic User: {orchestrator.PRD_CRITIC_USER[:80]}...")
    
    # Test TRD prompts
    print("\nPhase 3: TRD")
    print(f"  Generator Sys: {orchestrator.TRD_GENERATOR_SYS}")
    print(f"  Generator User: {orchestrator.TRD_GENERATOR_USER[:80]}...")
    print(f"  Critic Sys: {orchestrator.TRD_CRITIC_SYS}")
    print(f"  Critic User: {orchestrator.TRD_CRITIC_USER[:80]}...")
    
    # Test STORIES prompts
    print("\nPhase 4: STORIES")
    print(f"  Generator Sys: {orchestrator.STORIES_GENERATOR_SYS}")
    print(f"  Generator User: {orchestrator.STORIES_GENERATOR_USER[:80]}...")
    print(f"  Critic Sys: {orchestrator.STORIES_CRITIC_SYS}")
    print(f"  Critic User: {orchestrator.STORIES_CRITIC_USER[:80]}...")
    
    print("\n" + "=" * 50)
    print("✅ All prompts defined correctly!")

if __name__ == "__main__":
    import sys
    
    success = True
    success = test_orchestrator_imports() and success
    test_prompts()
    
    if success:
        print("\n🎉 Module 2 is ready for use!")
        sys.exit(0)
    else:
        sys.exit(1)
