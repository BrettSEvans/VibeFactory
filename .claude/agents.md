# VibeFactory Agent Registry

Complete registry of all agents in the VibeFactory system, including their roles, dependencies, and integration points.

## Architecture Overview

VibeFactory implements a **multi-layer, feedback-driven SDLC system** with 11 specialized agents:
- **Layer 1 (Requirements)**: 4 document generators + 4 blind critics (Phases 1-4)
- **Layer 2 (Engineering)**: 1 engineer + 1 validator + 1 E2E tester (Phases 5-6)
- **Layer 3 (Orchestration)**: LangGraph FSM runner (coordinates all phases)

Each agent has:
- **SKILL.md**: Technical specification, input/output format, quality metrics
- **SOUL.md**: Personality, values, decision-making framework, blind spots

---

## Phase 1: Business Requirements (BRD)

### Generator: Business Analyst
- **Path**: `.claude/agents/requirements/business-analyst/`
- **Role**: Convert rough product ideas into comprehensive BRD
- **Input**: Rough product idea (text)
- **Output**: Business Requirements Document
- **Dependencies**: None (first phase)
- **Downstream**: Product Manager (PRD generator)
- **Files**: `SKILL.md`, `SOUL.md`

### Critic: Executive QA Auditor
- **Path**: `.claude/agents/requirements/qa-auditor-exec/`
- **Role**: Blind critique of BRD against original idea
- **Input**: Original idea + BRD
- **Output**: CritiqueResponse (score, passed, is_blocker, feedback)
- **Dependencies**: Business Analyst (completes first)
- **Type**: Blind session (NEW LLM session, no chat history)
- **Pass Criteria**: score ≥ 7, passed=true
- **Files**: `SKILL.md`, `SOUL.md`

**Flow**: BRD Generation → Self-Critique → Blind Critique → [Approved] or [Feedback Loop]

---

## Phase 2: Product Requirements (PRD)

### Generator: Senior Product Manager
- **Path**: `.claude/agents/requirements/product-manager/`
- **Role**: Translate BRD into comprehensive PRD with personas and features
- **Input**: Approved BRD
- **Output**: Product Requirements Document
- **Dependencies**: BRD (approved)
- **Downstream**: Lead Architect (TRD generator)
- **Files**: `SKILL.md`, `SOUL.md`

### Critic: Product QA Auditor
- **Path**: `.claude/agents/requirements/qa-auditor-product/`
- **Role**: Blind critique of PRD against BRD; check for scope creep
- **Input**: Original BRD + PRD
- **Output**: CritiqueResponse
- **Dependencies**: Product Manager (completes first)
- **Type**: Blind session
- **Pass Criteria**: score ≥ 7, passed=true, no unjustified scope creep
- **Files**: `SKILL.md`, `SOUL.md`

**Flow**: PRD Generation → Self-Critique → Blind Critique → [Approved] or [Feedback Loop]

---

## Phase 3: Technical Requirements (TRD)

### Generator: Lead Software Architect
- **Path**: `.claude/agents/requirements/architect/`
- **Role**: Design system architecture, database schema, APIs based on PRD
- **Input**: Approved PRD
- **Output**: Technical Requirements Document
- **Dependencies**: PRD (approved)
- **Downstream**: Agile Scrum Master (Stories generator)
- **Files**: `SKILL.md`, `SOUL.md`

### Critic: Senior Systems Architect Auditor
- **Path**: `.claude/agents/requirements/qa-auditor-systems/`
- **Role**: Blind critique of TRD; verify architecture is feasible and identifies technical risks
- **Input**: Original PRD + TRD
- **Output**: CritiqueResponse (with blocker for technical impossibilities)
- **Dependencies**: Lead Architect (completes first)
- **Type**: Blind session
- **Pass Criteria**: score ≥ 7, passed=true, no impossible constraints
- **Blocker Behavior**: If `is_blocker=true`, project demotes to TRD retry
- **Files**: `SKILL.md`, `SOUL.md`

**Flow**: TRD Generation → Self-Critique → Blind Critique → [Approved] or [Feedback Loop/Demotion]

---

## Phase 4: User Stories & Backlog

### Generator: Agile Scrum Master
- **Path**: `.claude/agents/requirements/scrum-master/`
- **Role**: Break TRD into granular, dependency-ordered user stories
- **Input**: Approved TRD
- **Output**: JSON array of User Stories (id, name, description, success_criteria, depends_on)
- **Dependencies**: TRD (approved)
- **Downstream**: Engineer (code generation)
- **Parallelism**: Stories enable parallel engineering execution (respecting dependency graph)
- **Files**: `SKILL.md`, `SOUL.md`

### Critic: Agile QA Auditor
- **Path**: `.claude/agents/requirements/qa-auditor-agile/`
- **Role**: Blind critique of stories; verify completeness, dependency accuracy, testability
- **Input**: Original TRD + User Stories
- **Output**: CritiqueResponse (with blocker for missing stories or circular deps)
- **Dependencies**: Agile Scrum Master (completes first)
- **Type**: Blind session
- **Pass Criteria**: score ≥ 7, passed=true, all TRD covered, no circular dependencies
- **Blocker Behavior**: If `is_blocker=true`, project demotes to Stories retry
- **Files**: `SKILL.md`, `SOUL.md`

**Flow**: Stories Generation → Self-Critique → Blind Critique → [Approved] or [Feedback Loop/Demotion]

---

## Phase 5: Engineering & Code Generation

### Generator: Senior Python Developer
- **Path**: `.claude/agents/engineering/engineer/`
- **Role**: Write Python code and pytest tests for each user story
- **Input**: Approved User Stories (from backlog)
- **Output**: Tuple of (app_code, test_code)
- **Dependencies**: User Story dependencies (via `depends_on` field)
- **Execution**: Async worker pool (configurable concurrency, default 4)
- **Downstream**: Security & QA Validator
- **Parallelism**: Multiple stories execute in parallel respecting dependencies
- **Max Retries**: 3 per story
- **Files**: `SKILL.md`, `SOUL.md`

### Validator: Security & QA Validator
- **Path**: `.claude/agents/engineering/security-validator/`
- **Role**: Independent code review; verify security, test quality, error handling
- **Input**: Generated (app_code, test_code)
- **Output**: ValidatorResponse (passed, feedback)
- **Dependencies**: Engineer (completes first)
- **Type**: Independent review session
- **Pass Criteria**: passed=true, no security issues, meaningful tests
- **Blocker Behavior**: Feedback loops to Engineer for regeneration; max 3 retries
- **Files**: `SKILL.md`, `SOUL.md`

### Executor: Execution in Docker Sandbox
- **Role**: Run code in isolated Docker container using pytest
- **Execution**: Sandbox.run_command("pytest tests/ -v")
- **Pass Criteria**: returncode == 0 (all tests pass)
- **Failure Handling**: stderr feeds back to Engineer for next attempt
- **Output**: StoryResult (story_id, status, app_code, test_code, pytest_output)

**Flow**: Story Generation → Validation → Sandbox Execution → [Complete] or [Feedback Loop]

---

## Phase 6: End-to-End Testing

### Executor: QA Automation Engineer
- **Path**: `.claude/agents/engineering/e2e-tester/`
- **Role**: Generate and run comprehensive E2E tests after all stories complete
- **Input**: Approved PRD (for user workflow context)
- **Output**: E2EResponse (passed, feedback with test results)
- **Dependencies**: All stories completed (via execute_all_stories)
- **Execution**: Python script using requests library
- **Pass Criteria**: passed=true, E2E script execution returns 0
- **Files**: `SKILL.md`, `SOUL.md`

**Flow**: Stories Complete → PRD Reviewed → E2E Script Generated → E2E Tests Execute → [Report Results]

---

## Agent Dependency Matrix

```
Idea → BRD → PRD → TRD → STORIES → ENGINEERING → E2E TESTING
│      ↑      ↑      ↑      ↑           ↑            ↑
└──────┴──────┴──────┴──────┴───────────┴────────────┘
   (Blind Critique Loop with Demotion on Failure)
```

### Requirements Phase (BRD → PRD → TRD → STORIES)

**Linear Flow with Demotion on Critical Failure:**
- BRD → [Blind Critique] → PRD (uses BRD as source)
- PRD → [Blind Critique] → TRD (uses PRD as source)
- TRD → [Blind Critique] → STORIES (uses TRD as source)

**On Blocker (is_blocker=true):**
- PRD fails → demote to BRD (restart PRD phase)
- TRD fails → demote to PRD (restart TRD phase)
- STORIES fails → demote to TRD (restart STORIES phase)

### Engineering Phase (Stories → Code → Tests)

**Parallel Execution with Dependency Graph:**
- Stories with `depends_on=[]` execute first
- Respects dependency ordering: a story with `depends_on=[S1, S2]` waits for S1 and S2 to complete
- Engineer generates code for each story
- Code validated by Security & QA Validator
- Validated code executed in Docker sandbox
- On max retries: story marked as FAILED

### Integration Points

1. **State Management**: Each phase updates `state` with completed documents
2. **Failure Handling**: Blocker failures trigger demotion; non-blockers trigger retry
3. **Human Approval Gate**: Before engineering phase, human review of stories (manual approval in runner)
4. **Checkpoint Recovery**: State persisted to disk; runner can resume from last checkpoint

---

## Shared Souls (Reusable Templates)

Agents extend these soul templates for domain-specific behavior:

- **[GENERATOR_SOUL.md](./agents/souls/GENERATOR_SOUL.md)**: Base for document generators (Business Analyst, PM, Architect, Scrum Master)
- **[CRITIC_SOUL.md](./agents/souls/CRITIC_SOUL.md)**: Base for blind critics (all QA Auditors)
- **[VALIDATOR_SOUL.md](./agents/souls/VALIDATOR_SOUL.md)**: Base for code validators (Security & QA Validator)
- **[EXECUTOR_SOUL.md](./agents/souls/EXECUTOR_SOUL.md)**: Base for test executors (E2E Tester)

---

## Configuration & Runtime

### Agent Configuration Files

- **OrchestratorConfig** (`orchestrator.py`): LLM model, max retries, pass score for critics
- **EngineerConfig** (`engineer.py`): LLM model, max retries, validator pass score, worker pool size
- **LLM Integration**: Uses LiteLLM + Instructor for structured outputs (CritiqueResponse, ValidatorResponse, E2EResponse)

### Pydantic Response Models

- **CritiqueResponse**: score (0-10), passed, is_blocker, feedback
- **ValidatorResponse**: passed, feedback
- **E2EResponse**: passed, feedback

---

## How to Use This Registry

1. **Find an Agent**: Locate the agent by phase and role (e.g., "I need the TRD critic" → Senior Systems Architect Auditor)
2. **Understand Its Job**: Read SKILL.md for technical specs, SOUL.md for decision-making framework
3. **Understand Dependencies**: Check what agents must run before this one (Phase 1 → Phase 2 → Phase 3, etc.)
4. **See the Flow**: Review Phase section or dependency matrix to understand orchestration
5. **Extend or Modify**: Each agent's SOUL extends a shared template; start there to understand personality layer

---

## Future Enhancement Opportunities

- [ ] **Prompt Versioning**: Store prompt versions in SKILL.md, enable A/B testing
- [ ] **Paperclip Integration**: Register agents with Paperclip governance system
- [ ] **Agent Aliasing**: Support multiple implementations of same role (e.g., TRD-GPT4 vs TRD-Claude)
- [ ] **Metrics Tracking**: Collect success rates, iteration counts, feedback patterns per agent
- [ ] **Skill Composition**: Enable agents to use other agents' skills (e.g., Architect uses PM's skills for context)
- [ ] **Human-in-the-Loop Callbacks**: Add manual approval gates at specific phases
- [ ] **Cost Tracking**: Monitor LLM token usage and cost per agent per phase

