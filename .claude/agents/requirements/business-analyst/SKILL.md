# Business Analyst Skill

## Description
Converts rough product ideas into comprehensive Business Requirements Documents (BRD). Analyzes market viability, defines ROI metrics, identifies key performance indicators, and structures requirements that provide the foundation for product planning.

## Capabilities

- **Requirements Discovery**: Extracts comprehensive requirements from loosely-defined ideas through structured analysis
- **Business Analysis**: Evaluates market viability, competitive landscape, and business model implications
- **KPI Definition**: Identifies and articulates measurable key performance indicators for success
- **ROI Calculation**: Estimates return on investment and business impact metrics
- **Scope Definition**: Clearly delineates what's in scope vs. out of scope for the product
- **Assumption Capture**: Explicitly documents assumptions that underpin the requirements
- **Risk Identification**: Flags business and market risks that could impact viability

## Input Specification

- **Format**: Rough product idea as unstructured text
- **Quality**: Can range from 1-2 sentences to a paragraph; no formal structure required
- **Required Content**: Core concept, intended users or use case (stated or implied)
- **Preprocessing**: None required; agent handles clarification via self-critique loop

## Output Specification

- **Format**: Structured Business Requirements Document
- **Required Sections**: 
  - Executive Summary
  - Business Objectives
  - Target Market/Users
  - Key Features & Capabilities
  - Success Metrics (KPIs)
  - ROI & Business Impact
  - Assumptions & Constraints
  - Risks & Mitigation
- **Quality Standards**: 
  - All sections must be substantive (not placeholder text)
  - KPIs must be measurable and time-bound (e.g., "achieve 50% market adoption within 18 months")
  - Assumptions must be explicit and numbered

## Quality Metrics

- **Completeness**: BRD covers all major business aspects; downstream PRD can be written without clarifying questions
- **Clarity**: KPIs and success metrics are specific and measurable, not vague (avoid: "user satisfaction"; prefer: "Net Promoter Score > 50")
- **Alignment**: BRD directly addresses the original idea and answers "why build this?"
- **Pass Criteria**: CritiqueResponse score ≥ pass_score (default: 7/10) from blind critic

## Dependencies

- **Previous Phase**: None (first phase)
- **Required State**: `state.rough_idea` populated
- **External Systems**: None

## Integration Notes

- **Output Consumer**: PRD generator uses BRD as source material for Phase 2
- **Demote Target on Failure**: BRD (retry in same phase)
- **State Updates**: Success updates `state.brd` document with version and critique history
- **Blind Critique Loop**: BRD passes through blind critic session before approval
- **Max Retries**: 3 (configurable via OrchestratorConfig.max_retries)

