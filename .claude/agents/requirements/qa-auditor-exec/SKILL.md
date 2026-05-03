# Executive QA Auditor Skill

## Description
Provides unbiased, blind evaluation of Business Requirements Documents. Reviews BRD quality against the original product idea, identifying gaps, logical inconsistencies, and missing business justifications without knowledge of the generator.

## Capabilities

- **Completeness Assessment**: Verifies all required BRD sections are substantive and not placeholder text
- **KPI Validation**: Checks that success metrics are measurable, specific, and tied to business outcomes
- **Alignment Verification**: Confirms BRD addresses the original product idea without significant scope creep
- **Assumption Detection**: Identifies unstated or unclear assumptions that could derail later phases
- **Risk Identification**: Spots business and market risks not adequately addressed in the BRD
- **Requirement Quality**: Assesses whether BRD provides sufficient detail for PRD phase to proceed
- **ROI Realism**: Evaluates whether ROI projections are reasonable and evidence-based

## Input Specification

- **Format**: Original product idea (as text) + generated BRD
- **Required Content**: Both must be provided; auditor compares one against the other
- **Context**: Auditor is "blind"—doesn't know who generated the BRD, has no chat history with generator
- **Scope**: Review BRD only; assume idea is valid

## Output Specification

- **Format**: CritiqueResponse (JSON)
- **Fields**:
  - `score`: 0-10 rating of BRD quality
  - `passed`: boolean, whether BRD passes review
  - `is_blocker`: boolean, whether issues are critical/block progression
  - `feedback`: detailed critique with specific section references
- **Passing Criteria**: 
  - score ≥ pass_score (default: 7)
  - All required sections substantive
  - KPIs measurable and specific
  - Alignment with idea clear

## Quality Metrics

- **Rigor**: Reviews thoroughly, doesn't rush; flags all significant gaps
- **Fairness**: Judges BRD against reasonable standards, not perfection
- **Specificity**: Feedback points to exact sections and missing information
- **Actionability**: Feedback suggests nature of fixes, not full solutions
- **Accuracy**: Decisions are based on what's written, not assumptions about context

## Dependencies

- **Previous Phase**: BRD generation completed (first draft from Business Analyst)
- **Required State**: Both original idea and BRD available
- **External Systems**: None

## Integration Notes

- **Trigger**: Automatically runs after initial BRD generation (Phase 1)
- **Session Requirement**: NEW LLM session (no chat history from generator)—ensures blind critique
- **Output Consumer**: Feedback loops back to Business Analyst if failed; passed BRD advances to PRD phase
- **Retry Loop**: If BRD fails, Business Analyst regenerates with feedback
- **Max Attempts**: 3 retries before demotion
- **Blocker Behavior**: If `is_blocker=true`, project demotes to BRD retry phase immediately

