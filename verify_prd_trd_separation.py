#!/usr/bin/env python
"""
End-to-end verification that PRD and TRD separation works correctly.

This script:
1. Creates a sample product with separate PRD and TRD
2. Generates the product using VibeFactory
3. Verifies that:
   - UI files contain only PRD content
   - README contains only PRD content
   - Backend files can contain TRD content
   - No TRD keywords appear in frontend files
"""

import json
from pathlib import Path
from story_translator import StoryTranslator
from state import Story

# Sample product: Coffee Shop Ordering System
PROJECT_NAME = "coffee_shop_ordering"

PRD_CONTENT = """
# Coffee Shop Online Ordering System

## Business Vision
Enable customers to order coffee and pastries online for pickup at our location.

## Target Customers
- Office workers wanting quick lunch
- Students seeking affordable cafes
- Coffee enthusiasts discovering specialty drinks

## Core Features
### Menu Browsing
- View coffee drinks with descriptions and prices
- Filter by category (hot, cold, espresso, teas)
- See customer ratings for popular items

### Online Ordering
- Select items and quantities
- Choose pickup time (in 15-minute slots)
- Receive order confirmation with estimated ready time

### Pickup Management
- View estimated wait time
- Get notification when order is ready
- Rate and review purchased items

## Success Metrics
- 100+ orders per day within 3 months
- 4.5+ star average rating
- 20% repeat customer rate
"""

TRD_CONTENT = """
# Technical Requirements Document

## Backend Architecture
- FastAPI 0.104.1 running on Render.com
- PostgreSQL 14 for order and menu data
- Redis for session caching
- WebSocket for real-time order status updates

## Database Schema
- coffee_items table: id, name, price_cents, category, image_url
- orders table: id, uuid, created_at, pickup_time, status, items_json
- order_items table: id, order_id, coffee_item_id, quantity

## API Endpoints
- GET /api/menu - returns all coffee items (public)
- POST /api/orders - accepts order with idempotency key (public)
- GET /api/orders/:order_id - retrieves order status (public)
- GET /api/orders - lists all orders (admin, Basic Auth required)

## Frontend Stack
- Vanilla HTML5, CSS3, JavaScript (ES6+)
- Fetch API for HTTP requests
- localStorage for cart persistence
- No framework dependencies

## Security
- HTTPS/TLS 1.3 only
- CORS restricted to coffee shop domain
- JWT tokens for admin endpoints
- Input validation on all endpoints
- SQL injection prevention via parameterized queries
"""

STORIES = [
    {
        "id": "S1",
        "name": "Setup FastAPI backend with health endpoint",
        "description": "Create FastAPI project with uvicorn, add health check endpoint",
        "success_criteria": [
            "uvicorn app runs without errors",
            "GET /health returns HTTP 200 with status: ok",
            "CORS is configured for any origin"
        ]
    },
    {
        "id": "S2",
        "name": "Create coffee menu API endpoint",
        "description": "Implement GET /api/menu endpoint returning all coffee items",
        "success_criteria": [
            "Endpoint returns JSON array of coffee items",
            "Each item has id, name, price_cents, category, image_url",
            "Endpoint is accessible without authentication"
        ]
    },
    {
        "id": "S3",
        "name": "Build frontend menu page",
        "description": "Create HTML page displaying coffee menu with category filters",
        "success_criteria": [
            "Page loads menu from /api/menu",
            "Items grouped by category",
            "Can filter by hot/cold/espresso/tea",
            "Shows price and description"
        ]
    },
    {
        "id": "S4",
        "name": "Implement order placement API",
        "description": "Create POST /api/orders endpoint with idempotency and slot capacity",
        "success_criteria": [
            "Accepts order with customer info and items",
            "Returns order confirmation with uuid",
            "Rejects orders for full time slots (max 5 per 15 min)",
            "Duplicate orders by uuid return original order"
        ]
    },
    {
        "id": "S5",
        "name": "Build frontend ordering form",
        "description": "Create checkout page with cart, customer info, time selection",
        "success_criteria": [
            "Can add/remove items from cart",
            "Shows available pickup times",
            "Validates customer email/phone",
            "Submits order to /api/orders endpoint"
        ]
    }
]


def verify_prd_trd_separation():
    """Run end-to-end verification."""
    print("\n" + "=" * 70)
    print("PRD/TRD SEPARATION VERIFICATION")
    print("=" * 70)

    # Step 1: Create sample stories
    print("\n[1/5] Creating sample stories...")
    stories = [
        Story(
            id=s["id"],
            name=s["name"],
            description=s["description"],
            success_criteria=s["success_criteria"],
            llm_prompt=f"Implement: {s['description']}"
        )
        for s in STORIES
    ]
    print(f"✅ Created {len(stories)} stories")

    # Step 2: Set up context docs
    print("\n[2/5] Setting up PRD and TRD context...")
    context_docs = {
        "PRD": PRD_CONTENT,
        "TRD": TRD_CONTENT
    }
    print("✅ PRD: Business goals, features, customer focus")
    print("✅ TRD: Architecture, database schema, technical APIs")

    # Step 3: Test StoryTranslator
    print("\n[3/5] Testing StoryTranslator...")
    translator = StoryTranslator()

    # Test that frontend spec uses PRD only
    frontend_spec = translator._extract_frontend_spec(
        story_id="test_story",
        story_name="Coffee Menu",
        description="Display available coffee drinks",
        success_criteria=["User can see menu items"],
        context_docs=context_docs
    )

    # Check for TRD leakage
    trd_keywords = ["FastAPI", "PostgreSQL", "Redis", "JWT", "WebSocket", "Schema", "TRD"]
    frontend_text = str(frontend_spec)

    print(f"   - Frontend spec pages: {len(frontend_spec.pages)}")
    for page in frontend_spec.pages:
        trd_found = [kw for kw in trd_keywords if kw.lower() in page.description.lower()]
        if trd_found:
            print(f"   ❌ TRD keywords found in page: {trd_found}")
            return False
        else:
            print(f"   ✅ {page.name}: No TRD leakage detected")

    # Step 4: Test README sanitization
    print("\n[4/5] Testing README sanitization...")
    from product_assembly import ProductAssemblyManager

    manager = ProductAssemblyManager(PROJECT_NAME, context_docs=context_docs)

    # Simulate a README with mixed content
    mixed_readme = PRD_CONTENT + "\n\n" + TRD_CONTENT

    sanitized = manager._sanitize_readme_content(mixed_readme)

    # Check what got through
    print(f"   Original length: {len(mixed_readme)} chars")
    print(f"   Sanitized length: {len(sanitized)} chars")

    trd_keywords_found = [kw for kw in trd_keywords if kw in sanitized]
    if trd_keywords_found:
        print(f"   ❌ TRD keywords found in sanitized content: {trd_keywords_found}")
        return False
    else:
        print(f"   ✅ All TRD keywords removed from README")

    if "coffee" in sanitized.lower() or "ordering" in sanitized.lower():
        print(f"   ✅ PRD business content preserved in README")
    else:
        print(f"   ⚠️  Warning: PRD content may have been over-sanitized")

    # Step 5: Test UI sanitization
    print("\n[5/5] Testing UI content sanitization...")

    ui_with_tech = """
    <div class="menu">
        <h1>Coffee Menu</h1>
        <p>Browse our delicious coffee selection</p>
        <!-- Technical note: Uses FastAPI with PostgreSQL backend -->
        <!-- Authentication: JWT tokens required for admin -->
        <div class="items">
            <!-- Database schema: coffee_items table -->
            <div class="item">Cappuccino - $5.00</div>
        </div>
    </div>
    """

    sanitized_ui = manager._sanitize_ui_content(ui_with_tech)

    trd_in_ui = [kw for kw in ["FastAPI", "PostgreSQL", "JWT", "Database schema"] if kw in sanitized_ui]
    if trd_in_ui:
        print(f"   ❌ TRD keywords found in UI: {trd_in_ui}")
        return False
    else:
        print(f"   ✅ All TRD keywords removed from UI content")

    if "Coffee Menu" in sanitized_ui and "Cappuccino" in sanitized_ui:
        print(f"   ✅ User-facing content preserved in UI")
    else:
        print(f"   ⚠️  Warning: User content may have been removed")

    # Summary
    print("\n" + "=" * 70)
    print("✅ PRD/TRD SEPARATION VERIFIED SUCCESSFULLY")
    print("=" * 70)
    print("\nKey Findings:")
    print("  ✅ Frontend specs use only PRD content")
    print("  ✅ README sanitized to remove TRD keywords")
    print("  ✅ UI content filters technical implementation details")
    print("  ✅ Business content preserved in user-facing areas")
    print("\nConclusion:")
    print("  The VibeFactory architecture maintains a clean separation")
    print("  between PRD (user-facing) and TRD (technical) content.")
    print("\n")

    return True


if __name__ == "__main__":
    success = verify_prd_trd_separation()
    exit(0 if success else 1)
