# PRD and TRD Separation Architecture

## Overview

VibeFactory maintains a strict separation between **Product Requirements Document (PRD)** and **Technical Requirements Document (TRD)** to ensure that user-facing content reflects business goals, not technical implementation details.

## Core Principle

**PRD drives UI content. TRD drives backend implementation.**

### What This Means

| Content Aspect | Driven By | Never Contains |
|---|---|---|
| **Frontend Pages** | PRD | Technical implementation details |
| **Page Descriptions** | PRD | API endpoints, database schema |
| **README.md** | PRD | Architecture, FastAPI, PostgreSQL |
| **User-Facing Text** | PRD | TRD details |
| **Backend Code** | TRD | Business requirements only |
| **API Design** | TRD | User-facing descriptions |

## Data Flow in VibeFactory

### Story Translator (`story_translator.py`)
```
Input: story_description + context_docs {PRD, TRD}
       ↓
_extract_frontend_spec():
  - Uses PRD to determine page titles and descriptions
  - Uses TRD only to decide if backend is needed
  - Never includes TRD details in FrontendSpec
       ↓
Output: FrontendSpec (PRD-derived, TRD-free)
```

### Frontend Generator (`frontend_generator.py`)
```
Input: FrontendSpec + PRD (from context_docs)
       ↓
generate_code():
  - LLM prompt includes only PRD context
  - Explicitly told to follow FrontendSpec (which is PRD-derived)
  - No TRD content in prompts
       ↓
Output: Frontend HTML/CSS/JS (PRD-focused content)
```

### Backend Generator (`backend_generator.py`)
```
Input: BackendSpec + PRD + TRD (both in context_docs)
       ↓
generate_code():
  - LLM prompt includes BOTH PRD and TRD
  - TRD informs API design, database schema, security
       ↓
Output: Backend Python code (TRD-informed implementation)
```

### Product Assembly (`product_assembly.py`)
```
Input: Generated frontend + backend + context_docs {PRD, TRD}
       ↓
export_product():
  - README extracted from PRD ONLY
  - UI content sanitized (TRD keywords removed)
  - Implements _sanitize_readme_content() for final safety check
       ↓
Output: Complete product (PRD in README & UI, TRD in backend)
```

## Sanitization Rules

### UI Content Sanitization
The `_sanitize_ui_content()` method removes technical keywords:
- Technical Specification, Architecture, Backend
- TRD, API, Database, SQL
- FastAPI, JWT, OAuth, Auth, CORS, Middleware

### README Sanitization
The `_sanitize_readme_content()` method:
- Extracts first paragraph of PRD (business description)
- Removes section headers with technical keywords
- Stops at "Technical Architecture" sections
- Preserves only user-facing value proposition

## Testing

Run the PRD/TRD separation tests:

```bash
cd /Users/brettevanssf/Code/Saasless/VibeFactory
python -m pytest test_prd_trd_separation.py -v
```

Tests verify:
1. ✅ Frontend specs never include TRD markers
2. ✅ README contains only PRD content
3. ✅ UI pages exclude technical keywords
4. ✅ Static products use PRD descriptions
5. ✅ Backend receives TRD for implementation

## Examples

### Correct PRD Usage (UI)
```
PRD: "User can browse products with search and filtering"
UI Result: Search box + product grid (no mention of database, queries, or APIs)
```

### Correct TRD Usage (Backend)
```
TRD: "PostgreSQL with full-text search indexing on product_name"
Backend Result: FastAPI endpoint with SQLAlchemy query using text search
```

### Incorrect (Would Be Sanitized)
```
README: "Our platform uses FastAPI backend with PostgreSQL database"
Sanitized: "Our platform provides product browsing with search"
```

## Implementation Details

### Key Files Modified
- `story_translator.py`: Updated `_extract_frontend_spec()` docstring to emphasize PRD-only usage
- `product_assembly.py`: Added `_sanitize_readme_content()` method for README safety
- `test_prd_trd_separation.py`: New comprehensive test suite (6 tests, all passing)

### Separation Points
1. **Context Doc Extraction**: PRD and TRD separated at the start of generation
2. **Story Translation**: Only PRD passed to `_extract_frontend_spec()`
3. **Frontend Generation**: LLM prompts use only PRD
4. **UI Content Writing**: `_sanitize_ui_content()` filters technical keywords
5. **README Generation**: `_sanitize_readme_content()` ensures PRD-only content

## Maintenance Guidelines

When adding new features to VibeFactory:

1. **New UI Page Templates?** → Use PRD descriptions only
2. **New README Sections?** → Pull from PRD, not TRD
3. **New Frontend Prompts?** → Include PRD context, exclude TRD
4. **New Backend Features?** → TRD is appropriate and expected

## Benefits

- ✅ **User-Focused Messaging**: README and UI reflect business value, not implementation
- ✅ **Technical Flexibility**: Backend can change (FastAPI → Flask) without affecting user-facing content
- ✅ **Clear Separation**: Developers know what drives what
- ✅ **Maintainability**: PRD updates don't require backend code changes
- ✅ **Consistency**: All products follow the same content model

---

*Last Updated: 2026-05-03*
*Status: Implemented with comprehensive test coverage*
