# QA Automation Engineer Skill

## Description
Generates comprehensive end-to-end test suites that verify the entire system works as specified from the user perspective. Creates tests that exercise real workflows and catch integration failures that unit tests miss.

## Capabilities

- **Scenario Design**: Creates realistic user journeys and workflows
- **Test Script Generation**: Generates executable E2E test scripts using requests library
- **Endpoint Validation**: Verifies APIs respond correctly to realistic requests
- **Data Flow Testing**: Tests complete workflows from input to output
- **Error Scenario Testing**: Validates error handling and edge cases
- **Test Execution**: Runs tests against the live application and reports results

## Input Specification

- **Format**: Product Requirements Document (for user journey context)
- **Required Content**:
  - User personas and their workflows
  - Feature descriptions
  - API specifications (if available)
  - Success metrics

## Output Specification

- **Format**: Python script using requests library
- **Requirements**:
  - Executable as standalone Python script
  - Uses requests library for HTTP calls
  - Includes multiple user journey scenarios
  - Validates response structure and status codes
  - Tests error cases and edge scenarios
  - Provides clear pass/fail reporting
- **Quality Standards**:
  - Tests are independent (no cross-test dependencies)
  - Tests include setup and teardown
  - Tests validate data returned, not just HTTP status
  - Clear logging of test progress and failures

## Quality Metrics

- **Coverage**: Key user journeys are tested end-to-end
- **Realism**: Tests simulate actual user workflows, not isolated API calls
- **Independence**: Tests can run in any order and produce consistent results
- **Clarity**: Test results clearly show what passed and what failed
- **Robustness**: Tests handle timing issues and async operations

## Dependencies

- **Previous Phase**: All user stories completed and integrated
- **Required State**: PRD available for context; running application in sandbox
- **External Systems**: Application must be running on specified endpoint

## Integration Notes

- **Trigger**: Automatically runs after all stories are completed and integrated
- **Test Environment**: Runs against application in Docker sandbox
- **Lifecycle**: Application is started before E2E tests, stopped after
- **Output Consumer**: E2E results determine whether project is ready for deployment
- **Pass Criteria**: E2E script execution returns 0 (all tests passed)
- **Report**: Returns E2EResponse (passed: bool, feedback: string with test output)

