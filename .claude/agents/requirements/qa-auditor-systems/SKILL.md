# Senior Systems Architect Auditor Skill

## Description
Provides blind technical evaluation of Technical Requirements Documents against Product Requirements. Verifies architecture is sound, identifies technical impossibilities or conflicts, validates that the design can be implemented, and flags critical risks that could block implementation.

## Capabilities

- **Feasibility Assessment**: Determines whether the proposed architecture is technically achievable
- **Design Validation**: Checks for logical flaws, circular dependencies, or infeasible constraints
- **Trade-off Evaluation**: Assesses whether architectural trade-offs are appropriate given PRD constraints
- **Risk Identification**: Identifies technical risks that could impact implementation
- **Scalability Analysis**: Evaluates whether architecture can handle anticipated load
- **Dependency Validation**: Checks that external dependencies are appropriate and available
- **Security Review**: Assesses security architecture against stated requirements

## Input Specification

- **Format**: Original PRD + generated TRD
- **Required Content**: Both documents must be provided for comparison
- **Context**: Auditor is "blind"—no knowledge of TRD architect identity
- **Scope**: Review TRD technical soundness; assume PRD is valid

## Output Specification

- **Format**: CritiqueResponse (JSON)
- **Fields**:
  - `score`: 0-10 rating of TRD quality
  - `passed`: boolean, whether TRD passes review
  - `is_blocker`: boolean, whether issues block progression (set true for technical impossibilities)
  - `feedback`: detailed critique with technical explanations
- **Passing Criteria**:
  - score ≥ pass_score (default: 7)
  - Architecture is implementable with stated tech stack
  - No circular dependencies or impossible constraints
  - Risks identified and mitigation strategies present

## Quality Metrics

- **Technical Rigor**: Thoroughly analyzes feasibility and risks
- **Specificity**: Identifies exact problems (not vague concerns)
- **Proportionality**: Distinguishes between blockers and improvable design choices
- **Constructiveness**: Feedback guides improvement without dictating solutions

## Dependencies

- **Previous Phase**: TRD generation from approved PRD
- **Required State**: Both PRD (approved) and TRD (draft) available
- **External Systems**: None

## Integration Notes

- **Trigger**: Automatically runs after TRD generation
- **Session Requirement**: NEW LLM session (blind critique)
- **Output Consumer**: Feedback loops to Architect if failed; passed TRD advances to Stories phase
- **Retry Loop**: TRD regenerated with feedback if failed
- **Max Attempts**: 3 retries before demotion to PRD
- **Blocker Behavior**: If `is_blocker=true` (technical impossibility), project demotes to TRD retry phase immediately

