# Security & QA Validator Skill

## Description
Performs independent security and quality review of generated code before execution. Validates that code is secure, well-tested, and ready for execution in the sandbox.

## Capabilities

- **Security Review**: Scans for security vulnerabilities (injection, unvalidated inputs, secrets, etc.)
- **Test Quality Assessment**: Evaluates test comprehensiveness and meaningfulness
- **Error Handling Validation**: Checks that error paths are properly handled
- **Code Quality Check**: Assesses code cleanliness and maintainability
- **Dependency Validation**: Verifies that code uses approved/safe dependencies
- **Surface Area Analysis**: Identifies risky code patterns or potential failure modes

## Input Specification

- **Format**: Generated code tuple (app_code, test_code) + story context
- **Required Content**:
  - `app_code`: application code to review
  - `test_code`: test suite to review
  - Story description and success criteria for context

## Output Specification

- **Format**: ValidatorResponse (JSON)
- **Fields**:
  - `passed`: boolean, whether code passes validation
  - `feedback`: detailed comments on issues found or approval
- **Passing Criteria**:
  - No security vulnerabilities detected
  - Tests are meaningful (not trivial assertions)
  - Error handling is present and appropriate
  - Code quality is acceptable for production
- **Failure Triggers**:
  - SQL injection, unvalidated inputs, hardcoded secrets
  - Superficial tests (assert True, empty test bodies)
  - Missing error handling for stated risks
  - Code complexity or maintainability concerns

## Quality Metrics

- **Security Focus**: Prioritizes security issues; catches vulnerabilities that would block production
- **Test Rigor**: Rejects superficial tests; demands meaningful coverage
- **Specificity**: Feedback identifies exact problems, not vague concerns
- **Actionability**: Feedback guides code improvement

## Dependencies

- **Previous Phase**: Code generation completed by Engineer agent
- **Required State**: Generated app_code and test_code available
- **External Systems**: None

## Integration Notes

- **Trigger**: Automatically runs after code generation
- **Session Type**: Independent review (separate LLM session from engineer)
- **Output Consumer**: Feedback loops to Engineer if failed; passed code advances to sandbox execution
- **Retry Loop**: Engineer regenerates code if validation fails
- **Max Attempts**: 3 retries per story before marking as failed
- **Pass Requirement**: Must validate before any code execution

