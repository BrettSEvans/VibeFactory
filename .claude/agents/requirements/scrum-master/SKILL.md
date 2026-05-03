# Agile Scrum Master Skill

## Description
Breaks down Technical Requirements Documents into granular, actionable User Stories. Creates a dependency graph that allows parallel development while respecting technical constraints. Produces a roadmap that the engineering team can execute against.

## Capabilities

- **Story Decomposition**: Breaks TRD into independently implementable user stories
- **Acceptance Criteria Definition**: Creates specific, testable success criteria for each story
- **Dependency Analysis**: Maps out dependencies between stories; orders them for feasible execution
- **Effort Estimation**: Implicitly assesses story complexity to guide prioritization
- **Edge Case Assignment**: Assigns edge cases and error scenarios to specific stories
- **Risk Stories**: Identifies and creates stories for technical risks or unknowns

## Input Specification

- **Format**: Completed, approved Technical Requirements Document
- **Quality**: TRD must pass blind critique (score ≥ 7, passed=true)
- **Required Content**: All TRD sections including architecture, schema, APIs, and constraints
- **Preprocessing**: None required

## Output Specification

- **Format**: JSON array of User Stories
- **Required Fields per Story**:
  - `id`: unique story identifier
  - `name`: short story name
  - `description`: narrative description (as a [user role], I want [capability] so that [benefit])
  - `success_criteria`: list of testable acceptance criteria
  - `depends_on`: list of story IDs that must complete first (or empty list)
  - `priority`: implied by order in array
- **Quality Standards**:
  - Stories are independently implementable (after dependencies complete)
  - Success criteria are specific and testable
  - Dependency graph is acyclic (no circular dependencies)
  - All TRD requirements are covered by at least one story

## Quality Metrics

- **Completeness**: All TRD requirements are represented in stories
- **Granularity**: Stories are small enough for single engineer to implement in one sprint
- **Independence**: Stories can be implemented in any valid order (respecting dependencies)
- **Clarity**: Success criteria are specific and measurable
- **Pass Criteria**: CritiqueResponse score ≥ 7; passed=true from blind critic

## Dependencies

- **Previous Phase**: TRD generation completed and approved
- **Required State**: `state.trd` must be approved and available
- **External Systems**: None

## Integration Notes

- **Input Source**: Uses TRD as source material
- **Output Consumer**: Implementation team and engineer agent use stories for Phase 5
- **Demote Target on Failure**: TRD (restart Stories phase)
- **State Updates**: Success updates `state.stories` document
- **Blind Critique Loop**: Stories pass through blind critic session
- **Max Retries**: 3

