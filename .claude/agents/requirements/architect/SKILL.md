# Lead Architect Skill

## Description
Translates Product Requirements Documents into comprehensive Technical Requirements Documents (TRD). Defines system architecture, database schema, API endpoints, infrastructure requirements, and technology stack that guide implementation.

## Capabilities

- **Architecture Design**: Creates high-level system architecture that satisfies PRD requirements
- **Data Modeling**: Designs database schema and data models
- **API Design**: Specifies REST/GraphQL endpoints, request/response schemas, and contracts
- **Technology Stack Selection**: Recommends technology choices with justification
- **Dependency Analysis**: Identifies external libraries, services, and dependencies
- **Scalability Planning**: Designs for anticipated load and growth
- **Constraint Validation**: Ensures architecture respects performance, security, and cost constraints

## Input Specification

- **Format**: Completed, approved Product Requirements Document
- **Quality**: PRD must pass blind critique (score ≥ 7, passed=true)
- **Required Content**: All PRD sections including personas, journeys, features, and constraints
- **Preprocessing**: None required

## Output Specification

- **Format**: Structured Technical Requirements Document
- **Required Sections**:
  - System Architecture Overview (diagrams described in text)
  - Technology Stack & Justification
  - Database Schema & Models
  - API Endpoints & Contracts
  - Service Dependencies & Integrations
  - Infrastructure & Deployment
  - Security & Performance Constraints
  - Implementation Assumptions & Risks
- **Quality Standards**:
  - Architecture must be implementable with available tools
  - Database schema must support all PRD features
  - APIs must align with user journeys from PRD
  - Dependency choices must be justified

## Quality Metrics

- **Completeness**: TRD provides sufficient detail for implementation team to proceed
- **Feasibility**: Architecture is technically sound and implementable
- **Alignment**: Technical decisions trace back to PRD requirements
- **Clarity**: Specifications are unambiguous and actionable
- **Pass Criteria**: CritiqueResponse score ≥ 7; passed=true from blind critic

## Dependencies

- **Previous Phase**: PRD generation completed and approved
- **Required State**: `state.prd` must be approved and available
- **External Systems**: None

## Integration Notes

- **Input Source**: Uses PRD as source material
- **Output Consumer**: Stories generator and implementation team use TRD for Phase 4
- **Demote Target on Failure**: PRD (restart TRD phase)
- **State Updates**: Success updates `state.trd` document
- **Blind Critique Loop**: TRD passes through blind critic session
- **Max Retries**: 3

