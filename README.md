# Multi-Agent SDLC System - Complete Implementation

## Overview
A modular, multi-agent system for software development lifecycle management with state management, orchestration, and engineering execution.

## Module Structure

### Module 1: The Foundation (State & Sandbox)
**Files:** `state.py`, `sandbox.py`

#### `state.py` - Global State Management
- **Pydantic Models:**
  - `CritiqueEntry`: Agent feedback tracking
  - `Document`: Versioned documents with critiques
  - `ProjectState`: Central state with phases (IDEA → DESIGN → IMPLEMENTATION → TESTING → DEPLOYMENT)

- **Key Features:**
  - Phase demotion logic
  - JSON serialization/deserialization
  - Document versioning
  - Event logging

#### `sandbox.py` - Docker Execution Environment
- **Features:**
  - Isolated Docker container for code execution
  - Directory structure setup (`app/`, `tests/`, `requirements.txt`)
  - Dependency management (`pip install`)
  - Git integration (init, add, commit)
  - Command execution with output capture
  - File operations (write, read, list)

**Tested:** ✅ All features working with Docker

---

### Module 2: The Orchestrator
**File:** `orchestrator.py`

#### `BlindOrchestrator` - Document Creation & Validation
- **Phases:** BRD → PRD → TRD → STORIES

- **Blind Critique Loop:**
  1. **Generate Draft:** LLM creates document from source
  2. **Self-Critique:** Same session, identifies gaps
  3. **Blind Critique:** NEW session, unbiased review using `instructor`
  4. **Resolution:** Pass → approve, Blocker → demote, Fail → retry (max 3)

- **Structured Output:**
  ```python
  class CritiqueResponse(BaseModel):
      score: int      # 0-10
      passed: bool
      is_blocker: bool
      feedback: str
  ```

- **Exact Prompts Implemented:**
  - BRD: Lead Business Analyst → Executive Quality Auditor
  - PRD: Senior Product Manager → Product Quality Auditor
  - TRD: Lead Software Architect → Senior Systems Architect
  - STORIES: Agile Scrum Master → Agile QA Auditor

**Tested:** ✅ All imports and schemas validated

---

### Module 3: Engineering & Execution
**File:** `engineer.py`

#### `CodeEngineer` - Code Generation & Testing
- **Async Worker Pool:**
  - Parallel story execution with configurable worker count
  - Dependency graph tracking (`depends_on` arrays)
  - Semaphore-based concurrency control

- **Engineer & Validator Loop (per story):**
  1. **Engineer Agent:** Generates code + pytest
     - Sys: "You are a Senior Python Developer."
  2. **Security & QA Validator:** Independent LLM call with `instructor`
     - Sys: "You are a Security Auditor and QA Lead."
     - Returns: `{"passed": bool, "feedback": str}`
  3. **Execution:** Deploy to Sandbox, run pytest
     - 3 retries max, then demote to TRD

- **E2E Testing:**
  1. Generate E2E script from PRD
     - Sys: "You are a QA Automation Engineer."
  2. Start app in sandbox (background)
  3. Run E2E tests
  4. Tear down app
  5. Fail → demote back to EXECUTION

**Tested:** ✅ All imports and schemas validated

---

## Dependencies

### Core Packages
```
pydantic>=2.0.0
docker>=7.0.0
instructor>=1.0.0
litellm>=1.0.0
```

### Installation
```bash
pip install pydantic docker instructor litellm
```

### Environment Setup
```bash
# Activate virtual environment
source ~/venv/bin/activate

# Set API key
export OPENAI_API_KEY='your-key-here'

# Ensure Docker is running
# (Docker Desktop should be open)
```

---

## Usage Examples

### Example 1: Basic State Management
```python
from state import ProjectState, Document

# Create project state
state = ProjectState(
    project_id="proj-001",
    rough_idea="Build a task management API"
)

# Add BRD document
brd = Document(
    content="# Business Requirements\n\n1. User authentication",
    version=1,
    status="draft"
)
state.set_document("BRD", brd)

# Save to JSON
json_str = state.to_json()

# Load from JSON
state2 = ProjectState.from_json(json_str)
```

### Example 2: Sandbox Execution
```python
from sandbox import ProjectSandbox

# Create sandbox
with ProjectSandbox(project_id="test") as sandbox:
    # Write code
    sandbox.write_file("app/main.py", "print('Hello')")
    
    # Write tests
    sandbox.write_file("tests/test_main.py", "def test_hello(): assert True")
    
    # Run pytest
    result = sandbox.run_command("pytest tests/ -v")
    print(result.stdout)
```

### Example 3: Full Orchestration Flow
```python
from orchestrator import BlindOrchestrator, Phase
from state import ProjectState

# Initialize
state = ProjectState(
    project_id="my-project",
    rough_idea="Build a REST API"
)

orchestrator = BlindOrchestrator(state=state)

# Run full flow
results = orchestrator.orchestrate_full_flow()
# Returns: {"BRD": True, "PRD": True, "TRD": True, "STORIES": True}
```

### Example 4: Engineering Execution
```python
from engineer import CodeEngineer, EngineerConfig
from state import ProjectState
from sandbox import ProjectSandbox

# Setup
state = ProjectState(project_id="exec-test", rough_idea="API")
state.stories = [
    {
        "id": "story-001",
        "name": "User Login",
        "description": "Implement login endpoint",
        "success_criteria": "Returns JWT token",
        "depends_on": []
    }
]

sandbox = ProjectSandbox(project_id="exec-sandbox")
sandbox.initialize()

engineer = CodeEngineer(
    config=EngineerConfig(worker_pool_size=2),
    state=state,
    sandbox=sandbox
)

# Execute stories (async)
import asyncio
results = asyncio.run(engineer.execute_all_stories())

# Run E2E tests
passed, feedback = asyncio.run(engineer.run_e2e_tests())
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    ProjectState                             │
│  (state.py - Central State Management)                      │
│  - project_id, rough_idea                                   │
│  - current_phase (IDEA→DESIGN→IMPLEMENTATION→TESTING)       │
│  - docs: {BRD, PRD, TRD}                                    │
│  - stories: [User Stories]                                  │
│  - codebase: {file_path: content}                           │
│  - history: [Event Log]                                     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  BlindOrchestrator                          │
│                (orchestrator.py)                            │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ Phase 1: BRD                                          │ │
│  │   Generator: Lead Business Analyst                    │ │
│  │   Critic: Executive Quality Auditor (Blind)           │ │
│  └───────────────────────────────────────────────────────┘ │
│                            │                                │
│                            ▼                                │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ Phase 2: PRD                                          │ │
│  │   Generator: Senior Product Manager                   │ │
│  │   Critic: Product Quality Auditor (Blind)             │ │
│  └───────────────────────────────────────────────────────┘ │
│                            │                                │
│                            ▼                                │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ Phase 3: TRD                                          │ │
│  │   Generator: Lead Software Architect                  │ │
│  │   Critic: Senior Systems Architect (Blind)            │ │
│  └───────────────────────────────────────────────────────┘ │
│                            │                                │
│                            ▼                                │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ Phase 4: STORIES                                      │ │
│  │   Generator: Agile Scrum Master                       │ │
│  │   Critic: Agile QA Auditor (Blind)                    │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   CodeEngineer                              │
│                 (engineer.py)                               │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ Async Worker Pool (configurable concurrency)          │ │
│  │ - Processes stories with no dependencies first        │ │
│  │ - Tracks dependency graph                             │ │
│  └───────────────────────────────────────────────────────┘ │
│                            │                                │
│                            ▼                                │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ Engineer & Validator Loop (per story)                 │ │
│  │   1. Engineer: Generate code + pytest                 │ │
│  │   2. Validator: Security + QA review (instructor)     │ │
│  │   3. Execute: Run pytest in sandbox                   │ │
│  │   4. Retry up to 3 times, then demote                 │ │
│  └───────────────────────────────────────────────────────┘ │
│                            │                                │
│                            ▼                                │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ E2E Testing                                           │ │
│  │   1. Generate E2E script from PRD                     │ │
│  │   2. Start app in sandbox                             │ │
│  │   3. Run E2E tests                                    │ │
│  │   4. Tear down                                        │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    ProjectSandbox                           │
│                  (sandbox.py)                               │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ Docker Container (isolated execution)                 │ │
│  │ - app/ directory                                      │ │
│  │ - tests/ directory                                    │ │
│  │ - requirements.txt                                    │ │
│  │ - Git repository                                      │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## Testing

### Run All Tests
```bash
# Test Module 1: State
python test_state.py

# Test Module 1: Sandbox
python test_sandbox.py

# Test Module 2: Orchestrator
python test_orchestrator.py

# Test Module 3: Engineer
python test_engineer.py
```

### Test Requirements
- Python 3.11+
- Docker Desktop running
- OPENAI_API_KEY environment variable (for LLM calls)

---

## Next Steps

### Module 4: Agent Coordination
- Multi-agent communication protocol
- Task delegation and synchronization
- Conflict resolution

### Module 5: Deployment Pipeline
- CI/CD integration
- Environment management
- Rollback strategies

### Module 6: Monitoring & Analytics
- Execution metrics collection
- Performance tracking
- Cost optimization

---

## License
Internal use only - Multi-Agent SDLC System
