# Agile QA Auditor Skill

## Description
Provides blind evaluation of User Stories against Technical Requirements. Verifies story breakdown is complete, dependencies are accurate, success criteria are testable, and the story list actually guides implementation without gaps or contradictions.

## Capabilities

- **Completeness Verification**: Ensures all TRD requirements are represented in stories
- **Dependency Validation**: Checks that dependency graphs are accurate and acyclic
- **Success Criteria Review**: Validates that criteria are specific, testable, and completeness-signaling
- **Story Granularity**: Assesses whether stories are appropriately sized for implementation
- **Ambiguity Detection**: Flags vague or contradictory story descriptions
- **Coverage Analysis**: Ensures edge cases and error scenarios are assigned to specific stories

## Input Specification

- **Format**: Original TRD + generated User Stories (JSON array)
- **Required Content**: Both documents must be provided
- **Context**: Auditor is "blind"—no knowledge of story writer identity
- **Scope**: Review stories against TRD; assume TRD is valid

## Output Specification

- **Format**: CritiqueResponse (JSON)
- **Fields**:
  - `score`: 0-10 rating of stories quality
  - `passed`: boolean, whether stories pass review
  - `is_blocker`: boolean, whether issues block implementation (set true for missing stories or circular dependencies)
  - `feedback`: detailed critique identifying gaps or issues
- **Passing Criteria**:
  - score ≥ pass_score (default: 7)
  - All TRD requirements covered by at least one story
  - No circular dependencies
  - Success criteria are specific and testable
  - Story granularity is appropriate for execution

## Quality Metrics

- **Coverage**: Every TRD requirement is addressed in at least one story
- **Correctness**: Dependency graph is acyclic and accurate
- **Clarity**: Stories and criteria are unambiguous
- **Completeness**: Edge cases are explicitly assigned, not glossed over

## Dependencies

- **Previous Phase**: Stories generation from approved TRD
- **Required State**: Both TRD (approved) and Stories (draft) available
- **External Systems**: None

## Integration Notes

- **Trigger**: Automatically runs after Stories generation
- **Session Requirement**: NEW LLM session (blind critique)
- **Output Consumer**: Feedback loops to Scrum Master if failed; passed stories advance to engineering phase
- **Retry Loop**: Stories regenerated with feedback if failed
- **Max Attempts**: 3 retries before demotion to TRD
- **Blocker Behavior**: If `is_blocker=true` (missing stories or circular deps), project demotes to Stories retry phase

