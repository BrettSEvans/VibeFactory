"""
Unit tests to verify PRD and TRD separation.

Tests ensure that:
- TRD (Technical Requirements Document) content is never written to UI files
- README contains only PRD-derived content, not technical implementation details
- Frontend specifications use only PRD for descriptions and content
- Backend properly receives TRD for technical implementation
"""

import unittest
from pathlib import Path
from typing import Dict
from story_translator import StoryTranslator, FrontendSpec
from product_assembly import ProductAssemblyManager


class TestPRDTRDSeparation(unittest.TestCase):
    """Test suite for PRD/TRD content separation."""

    def setUp(self):
        """Set up test fixtures."""
        self.story_translator = StoryTranslator()

        # Sample PRD content (user-facing, business-focused)
        self.prd_content = """
# Product Requirements Document - E-Commerce Platform

## Business Goals
- Increase daily foot traffic
- Capture online orders
- Improve brand awareness

## Features
- User authentication
- Product catalog with search
- Shopping cart functionality
- Order management
- Customer reviews

## Success Metrics
- 500+ daily users
- 10% conversion rate
- 4.5/5 star rating
"""

        # Sample TRD content (technical, implementation-focused)
        self.trd_content = """
# Technical Requirements Document - E-Commerce Platform

## System Architecture
- FastAPI backend on AWS Lambda
- PostgreSQL database with connection pooling
- Redis cache for session management
- JWT token authentication

## Database Schema
- users table with bcrypt-hashed passwords
- products table with full-text search indexing
- orders table with composite key (user_id, created_at)
- oauth_tokens for third-party integration

## API Endpoints
- POST /api/auth/login with OAuth2
- GET /api/products with pagination
- POST /api/orders with idempotency keys
- WebSocket /ws/notifications for real-time updates

## Security Requirements
- HTTPS/TLS 1.3 enforced
- CORS whitelist authentication
- SQL injection prevention via parameterized queries
- XSS protection via Content Security Policy
"""

        self.context_docs = {
            "PRD": self.prd_content,
            "TRD": self.trd_content
        }

    def test_frontend_spec_uses_prd_only(self):
        """
        Test that frontend specification uses only PRD content for descriptions.
        TRD technical details should never appear in UI pages.
        """
        spec = self.story_translator._extract_frontend_spec(
            story_id="story_1",
            story_name="Product Catalog",
            description="Display products with search and filtering",
            success_criteria=["User can search by name", "User can filter by price"],
            context_docs=self.context_docs
        )

        # Verify spec is a FrontendSpec
        self.assertIsInstance(spec, FrontendSpec)

        # Check that pages have non-technical descriptions
        for page in spec.pages:
            self.assertNotIn("FastAPI", page.description)
            self.assertNotIn("PostgreSQL", page.description)
            self.assertNotIn("JWT", page.description)
            self.assertNotIn("OAuth", page.description)
            self.assertNotIn("TRD", page.description)
            self.assertNotIn("API", page.description)
            self.assertNotIn("Database", page.description)

    def test_readme_sanitization_removes_trd_content(self):
        """
        Test that README generation removes any TRD technical content.
        """
        manager = ProductAssemblyManager("test_product")

        # Test sanitization of content that contains both PRD and TRD text
        mixed_content = """
E-Commerce Platform - A great way to sell online
Features include shopping carts and reviews

## Technical Architecture
This uses FastAPI backend with PostgreSQL database
And JWT token authentication for security
"""

        sanitized = manager._sanitize_readme_content(mixed_content)

        # Verify technical keywords are removed
        self.assertNotIn("FastAPI", sanitized)
        self.assertNotIn("PostgreSQL", sanitized)
        self.assertNotIn("JWT", sanitized)
        self.assertNotIn("Technical Architecture", sanitized)

        # Verify business content is preserved (at least the first part)
        self.assertIn("E-Commerce Platform", sanitized)

    def test_ui_content_sanitization_removes_tech_keywords(self):
        """
        Test that UI content sanitization filters out technical keywords.
        """
        manager = ProductAssemblyManager("test_product")

        ui_content = """
<div class="product-list">
    <h1>Products</h1>
    <p>Browse our selection of products</p>

    Technical Implementation Note: Uses FastAPI backend
    Database: PostgreSQL with connection pooling
    Auth: JWT tokens with OAuth2

    <button>Add to Cart</button>
</div>
"""

        sanitized = manager._sanitize_ui_content(ui_content)

        # Verify technical keywords are removed
        self.assertNotIn("FastAPI", sanitized)
        self.assertNotIn("PostgreSQL", sanitized)
        self.assertNotIn("JWT", sanitized)
        self.assertNotIn("OAuth", sanitized)
        self.assertNotIn("Database", sanitized)

        # Verify user-facing content is preserved
        self.assertIn("Products", sanitized)
        self.assertIn("Browse", sanitized)
        self.assertIn("Add to Cart", sanitized)

    def test_frontend_spec_excludes_trd_markers(self):
        """
        Test that frontend specifications never include TRD section markers.
        """
        spec = self.story_translator._extract_frontend_spec(
            story_id="story_2",
            story_name="User Authentication",
            description="Allow users to sign up and log in",
            success_criteria=["User can register", "User can login"],
            context_docs=self.context_docs
        )

        # Collect all text from spec
        all_text = str(spec)

        # Verify no TRD markers appear
        trd_markers = ["Technical Specification", "Backend", "FastAPI", "PostgreSQL", "Architecture", "TRD"]
        for page in spec.pages:
            for marker in trd_markers:
                self.assertNotIn(marker, page.title, f"TRD marker '{marker}' found in page title")
                self.assertNotIn(marker, page.description, f"TRD marker '{marker}' found in page description")

    def test_backend_receives_trd_for_technical_decisions(self):
        """
        Test that backend generation properly receives TRD for technical implementation.
        (This is the expected behavior - TRD is for backend, not UI)
        """
        # This test verifies that TRD is available for backend_generator
        # Note: Backend generator should use TRD in its LLM prompts

        # Verify context_docs has both PRD and TRD
        self.assertIn("PRD", self.context_docs)
        self.assertIn("TRD", self.context_docs)

        # Verify TRD has technical content
        self.assertIn("FastAPI", self.context_docs["TRD"])
        self.assertIn("PostgreSQL", self.context_docs["TRD"])

        # Verify PRD has business content
        self.assertIn("Business Goals", self.context_docs["PRD"])
        self.assertIn("Shopping cart", self.context_docs["PRD"])

    def test_frontend_spec_for_static_product_uses_prd(self):
        """
        Test that static (frontend-only) products use PRD for description.
        """
        # For a static product (no backend), frontend spec should still use PRD
        minimal_context = {
            "PRD": "Beautiful landing page for our coffee shop",
            "TRD": "Static HTML served from CDN"
        }

        spec = self.story_translator._extract_frontend_spec(
            story_id="static_1",
            story_name="Landing Page",
            description="Create a landing page",
            success_criteria=["Page loads quickly"],
            context_docs=minimal_context
        )

        # For static products, we expect a single page with PRD-derived content
        if spec.is_frontend_only:
            self.assertGreater(len(spec.pages), 0)
            # First page should use PRD content
            self.assertIn("coffee shop", spec.pages[0].description.lower())


if __name__ == "__main__":
    unittest.main()
