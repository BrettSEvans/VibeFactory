# Product Manager Skill

## Description
Translates Business Requirements Documents into comprehensive Product Requirements Documents (PRD). Defines user personas, detailed feature specifications, edge cases, and product-level constraints that guide architecture and engineering.

## Capabilities

- **Persona Definition**: Creates detailed user personas with motivations, behaviors, and pain points
- **Feature Breakdown**: Translates business objectives into concrete product features and capabilities
- **Use Case Mapping**: Documents how personas will use features to achieve their goals
- **Edge Case Discovery**: Identifies and documents edge cases and error scenarios
- **User Journey Mapping**: Describes the workflows and interactions users will perform
- **Scope Management**: Clarifies product scope, boundaries, and constraints
- **Success Criteria Definition**: Specifies product-level acceptance criteria for features

## Input Specification

- **Format**: Completed, approved Business Requirements Document
- **Quality**: BRD must pass blind critique (score ≥ 7, passed=true)
- **Required Sections**: All BRD sections must be present
- **Preprocessing**: None required

## Output Specification

- **Format**: Structured Product Requirements Document
- **Required Sections**:
  - Executive Summary (from BRD context)
  - User Personas (detailed, 3-5 personas typical)
  - User Journeys (key workflows for each persona)
  - Features & Capabilities (detailed, with success criteria)
  - Edge Cases & Error Handling
  - Product Constraints & Assumptions
  - Success Metrics (translated from BRD KPIs)
- **Quality Standards**:
  - Personas must be specific (not generic)
  - Features must be traceable to BRD objectives
  - Edge cases must be realistic and actionable
  - No scope creep beyond BRD boundaries

## Quality Metrics

- **Completeness**: PRD covers all personas, journeys, and features needed for architecture phase
- **Traceability**: Each feature maps back to BRD business objective
- **Specificity**: Feature descriptions are detailed enough for architect to design against
- **Feasibility**: Edge cases and constraints are realistic, not exhaustive
- **Pass Criteria**: CritiqueResponse score ≥ 7 from blind critic; passed=true

## Dependencies

- **Previous Phase**: BRD generation completed and approved
- **Required State**: `state.brd` must be approved and available
- **External Systems**: None

## Integration Notes

- **Input Source**: Uses BRD as source material
- **Output Consumer**: TRD generator uses PRD for Phase 3
- **Demote Target on Failure**: BRD (restart PRD phase)
- **State Updates**: Success updates `state.prd` document
- **Blind Critique Loop**: PRD passes through blind critic session before approval
- **Max Retries**: 3

