# Product QA Auditor Skill

## Description
Provides blind evaluation of Product Requirements Documents against Business Requirements. Verifies PRD translates BRD objectives faithfully, identifies scope creep, validates feature alignment, and ensures product specification is complete and internally consistent.

## Capabilities

- **Scope Creep Detection**: Identifies features not justified by BRD business objectives
- **Feature Traceability**: Verifies each feature maps to a BRD objective or identified user need
- **Persona Completeness**: Checks that all user personas are distinct, well-defined, and useful
- **Journey Validation**: Assesses whether user journeys are realistic and complete
- **Edge Case Adequacy**: Determines if edge cases are sufficiently covered without exhaustive over-specification
- **Consistency Checking**: Flags contradictions or ambiguities in feature specifications
- **Success Criteria**: Validates that product-level success metrics are measurable and tied to BRD KPIs

## Input Specification

- **Format**: Original BRD + generated PRD
- **Required Content**: Both documents must be provided for comparison
- **Context**: Auditor is "blind"—no knowledge of PRD generator identity
- **Scope**: Review PRD alignment with BRD; assume BRD is valid

## Output Specification

- **Format**: CritiqueResponse (JSON)
- **Fields**:
  - `score`: 0-10 rating of PRD quality
  - `passed`: boolean, whether PRD passes review
  - `is_blocker`: boolean, whether issues block progression
  - `feedback`: detailed critique with specific references
- **Passing Criteria**:
  - score ≥ pass_score (default: 7)
  - No unjustified scope creep
  - All personas connected to BRD objectives
  - Features are traceable and internally consistent

## Quality Metrics

- **Rigor**: Thoroughly compares PRD against BRD; flags deviations
- **Scope Awareness**: Sensitive to scope creep; distinguishes core from "nice-to-have"
- **Consistency**: Identifies contradictions and ambiguities
- **Constructiveness**: Feedback guides PRD improvement without being prescriptive

## Dependencies

- **Previous Phase**: PRD generation from approved BRD
- **Required State**: Both BRD (approved) and PRD (draft) available
- **External Systems**: None

## Integration Notes

- **Trigger**: Automatically runs after PRD generation
- **Session Requirement**: NEW LLM session (blind critique)
- **Output Consumer**: Feedback loops to Product Manager if failed; passed PRD advances to TRD phase
- **Retry Loop**: PRD regenerated with feedback if failed
- **Max Attempts**: 3 retries before demotion to BRD
- **Blocker Behavior**: If `is_blocker=true`, project demotes to PRD retry phase

