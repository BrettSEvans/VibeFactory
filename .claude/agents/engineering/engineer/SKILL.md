# Senior Python Developer Skill

## Description
Generates production-quality Python code and comprehensive pytest test suites based on user stories. Produces both application code and automated tests that verify story success criteria are met.

## Capabilities

- **Code Generation**: Writes clean, well-structured Python code that implements story requirements
- **Test Writing**: Creates comprehensive pytest test suites covering success criteria and edge cases
- **Error Handling**: Implements appropriate error handling and validation
- **Code Organization**: Structures code with appropriate modules, classes, and functions
- **Documentation**: Includes docstrings and comments where behavior is non-obvious
- **Feedback Integration**: Regenerates code based on validator feedback and test failures
- **Link Validation**: Verifies all generated links (href, src, navigation paths) are syntactically correct and point to valid files/routes. Checks relative paths use correct ../ prefixes, absolute paths don't start with /, and all referenced files exist

## Input Specification

- **Format**: User Story (JSON)
- **Required Fields**:
  - `description`: story narrative
  - `success_criteria`: list of acceptance criteria
  - `depends_on`: list of already-completed story IDs (for context)
- **Optional Fields**:
  - `last_error`: pytest failure output from previous attempt (for regeneration)

## Output Specification

- **Format**: Tuple of (app_code, test_code)
- **App Code**:
  - Python code that implements the story
  - Executable and importable
  - Includes error handling and validation
- **Test Code**:
  - pytest-compatible test file
  - Tests all success criteria
  - Tests edge cases and error scenarios
  - Tests are specific, not trivial (avoid: `assert True`)
- **Quality Standards**:
  - Code passes pylint/flake8 checks
  - All success criteria have corresponding tests
  - Tests achieve >80% code coverage of app code

## Quality Metrics

- **Correctness**: Code implements story requirements accurately
- **Completeness**: All success criteria are tested
- **Quality**: Code is clean, well-organized, and maintainable
- **Robustness**: Error handling is appropriate; edge cases considered
- **Testability**: Tests are meaningful and would catch regressions

## Dependencies

- **Previous Phase**: Approved user stories from Stories generation
- **Required State**: Story details available (description, success criteria, depends_on)
- **External Systems**: None directly; context includes prior story code if exists

## Integration Notes

- **Async Execution**: Runs in async worker pool with configurable concurrency
- **Retry Loop**: Regenerates code if validation fails or tests fail (max 3 attempts)
- **Validation**: Code passes through Security & QA Validator before execution
- **Execution**: Code runs in Docker sandbox with pytest
- **Pass Criteria**: Code passes validation and pytest execution returns 0
- **Demote on Failure**: Blocks story if max retries exceeded; marks as failed

