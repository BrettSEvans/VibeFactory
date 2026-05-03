"""
Test script for Module 1: State and Sandbox
"""

from state import ProjectState, Document, CritiqueEntry
from datetime import datetime

print("Testing State Management...")

# Test 1: Create a ProjectState
state = ProjectState(
    project_id="test-001",
    rough_idea="Build a task management API"
)
print(f"✓ Created project: {state.project_id}")

# Test 2: Add a document
doc = Document(
    content="# Business Requirements\n\n1. User authentication",
    version=1,
    status="draft"
)
state.set_document(ProjectState.BRD, doc)
print(f"✓ Added BRD document (version {doc.version})")

# Test 3: Add a critique
doc.add_critique("reviewer-agent", "Consider adding password requirements")
print(f"✓ Added critique to BRD")

# Test 4: Test demote functionality
state.demote(ProjectState.IDEA, "Requirements need revision")
print(f"✓ Demoted to phase: {state.current_phase}")

# Test 5: JSON serialization
json_str = state.to_json()
print(f"✓ Serialized to JSON ({len(json_str)} chars)")

# Test 6: JSON deserialization
state2 = ProjectState.from_json(json_str)
print(f"✓ Deserialized from JSON: {state2.project_id}")

print("\n✅ All state tests passed!")
print("\nNote: Sandbox tests require Docker to be running.")
