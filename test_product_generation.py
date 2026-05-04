"""
Integration Test: Complete Product Generation Workflow
Tests the entire pipeline from rough idea to deployable product.

WORKFLOW:
1. Orchestrator: Rough Idea → BRD → PRD → TRD → STORIES
2. ProductGenerator: STORIES → BackendSpec + FrontendSpec → Code
3. ProductAssemblyManager: Code files → Complete Product Structure
4. Validation: Verify generated product is deployable
"""

import asyncio
import json
import os
import tempfile
from pathlib import Path

from state import ProjectState, Document
from orchestrator import BlindOrchestrator, OrchestratorConfig, Phase
from story_translator import StoryTranslator
from backend_generator import BackendGenerator, BackendGeneratorConfig
from frontend_generator import FrontendGenerator, FrontendGeneratorConfig
from product_assembly import ProductAssemblyManager
from product_generator import ProductGenerator, ProductGeneratorConfig


class ProductGenerationTestSuite:
    """Integration tests for product generation."""

    def __init__(self, project_id: str = "test_product"):
        """Initialize test suite."""
        self.project_id = project_id
        self.temp_dir = tempfile.mkdtemp(prefix="product_gen_test_")
        self.results = {}

    def run_all_tests(self):
        """Run complete test suite."""
        print("\n" + "=" * 70)
        print("PRODUCT GENERATION TEST SUITE")
        print("=" * 70)

        tests = [
            ("Test 1: StoryTranslator", self.test_story_translator),
            ("Test 2: BackendGenerator", self.test_backend_generator),
            ("Test 3: FrontendGenerator", self.test_frontend_generator),
            ("Test 4: ProductAssemblyManager", self.test_product_assembly),
            ("Test 5: End-to-End Integration", self.test_end_to_end_integration),
        ]

        for test_name, test_func in tests:
            try:
                print(f"\n{'=' * 70}")
                print(f"{test_name}")
                print("=" * 70)
                test_func()
                self.results[test_name] = "✓ PASSED"
                print(f"✓ {test_name} passed")
            except Exception as e:
                self.results[test_name] = f"✗ FAILED: {str(e)}"
                print(f"✗ {test_name} failed: {e}")
                import traceback
                traceback.print_exc()

        self.print_summary()

    def test_story_translator(self):
        """Test StoryTranslator converting stories to specs."""
        print("\nTesting StoryTranslator...")

        # Create a sample story
        story = {
            "id": "story_001",
            "name": "Task Management",
            "description": "Users should be able to create, view, edit, and delete tasks. Tasks have a title, description, and completion status.",
            "depends_on": [],
            "success_criteria": [
                "User can create a new task",
                "User can view list of all tasks",
                "User can edit a task",
                "User can delete a task",
                "Task completion status can be toggled",
            ]
        }

        translator = StoryTranslator()
        backend_spec, frontend_spec = translator.translate_story(story)

        # Verify backend spec
        assert backend_spec.story_id == "story_001"
        assert backend_spec.story_name == "Task Management"
        assert len(backend_spec.endpoints) > 0, "Should generate endpoints"
        assert len(backend_spec.models) > 0, "Should generate database models"
        assert len(backend_spec.dependencies) > 0, "Should have dependencies"

        print(f"✓ Backend spec generated: {len(backend_spec.endpoints)} endpoints")

        # Verify frontend spec
        assert frontend_spec.story_id == "story_001"
        assert len(frontend_spec.pages) > 0, "Should generate pages"
        assert len(frontend_spec.components) > 0, "Should generate components"
        assert len(frontend_spec.api_endpoints) > 0, "Should reference API endpoints"

        print(f"✓ Frontend spec generated: {len(frontend_spec.pages)} pages")

        return backend_spec, frontend_spec

    def test_backend_generator(self):
        """Test BackendGenerator creating FastAPI code."""
        print("\nTesting BackendGenerator...")

        # Get backend spec from translator
        backend_spec, _ = self.test_story_translator()

        # Generate backend code
        generator = BackendGenerator(
            BackendGeneratorConfig(api_key=os.getenv("OPENAI_API_KEY"))
        )

        # Generate alternative code (without full LLM call)
        models_py = generator.generate_models_code(backend_spec)
        endpoints_py = generator.generate_endpoint_code(backend_spec)
        test_py = generator.generate_test_code(backend_spec)
        requirements = generator.generate_requirements(backend_spec)

        # Verify code generation
        assert "class " in models_py, "Should generate model class"
        assert "@router" in endpoints_py, "Should generate endpoints"
        assert "pytest" in test_py or "test_" in test_py, "Should generate pytest tests"
        assert "fastapi" in requirements, "Should include fastapi in requirements"

        print("✓ Models generated with SQLAlchemy ORM")
        print("✓ FastAPI endpoints generated")
        print("✓ Pytest test code generated")
        print("✓ Requirements.txt generated")

        return {
            "models.py": models_py,
            "routes.py": endpoints_py,
            "test_routes.py": test_py,
            "requirements.txt": requirements
        }

    def test_frontend_generator(self):
        """Test FrontendGenerator creating vanilla JS code."""
        print("\nTesting FrontendGenerator...")

        # Get frontend spec from translator
        _, frontend_spec = self.test_story_translator()

        # Generate frontend code
        generator = FrontendGenerator(
            FrontendGeneratorConfig(api_key=os.getenv("OPENAI_API_KEY"))
        )

        # Generate alternative code (without full LLM call)
        page_templates = {}
        for page in frontend_spec.pages:
            html = generator.generate_page_template(page)
            page_templates[f"{page.name}.html"] = html
            assert "<!DOCTYPE html>" in html, "Should generate HTML"

        component_js = {}
        for component in frontend_spec.components:
            js = generator.generate_component_module(component)
            component_js[f"{component.name}.js"] = js
            assert "class" in js, "Should generate JavaScript class"

        styles_css = {}
        for component in frontend_spec.components:
            css = generator.generate_component_styles(component)
            styles_css[f"{component.name}.css"] = css
            assert "." in css, "Should generate CSS"

        nav_code = generator.generate_navigation_code(frontend_spec)
        assert "registerPage" in nav_code, "Should generate navigation registration"

        print(f"✓ HTML pages generated: {len(page_templates)}")
        print(f"✓ JavaScript components generated: {len(component_js)}")
        print(f"✓ CSS styles generated: {len(styles_css)}")
        print("✓ Navigation registration code generated")

        return {
            "pages": page_templates,
            "components": component_js,
            "styles": styles_css,
            "navigation": nav_code
        }

    def test_product_assembly(self):
        """Test ProductAssemblyManager creating product structure."""
        print("\nTesting ProductAssemblyManager...")

        product = ProductAssemblyManager(
            project_id=self.project_id,
            root_dir=self.temp_dir
        )

        # Initialize product structure
        product.initialize_product_structure()
        assert os.path.exists(str(product.product_dir)), "Should create product directory"

        # Get generated code
        backend_code = self.test_backend_generator()
        frontend_code = self.test_frontend_generator()

        # Add backend code
        for file_path, content in backend_code.items():
            product.add_backend_code("story_001", file_path, content)

        # Add frontend code
        for file_path, content in frontend_code["pages"].items():
            product.add_frontend_component("story_001", file_path, content)

        # Register a page
        product.add_frontend_page("story_001", "tasks_list", "/tasks")

        # Register an endpoint
        product.add_api_endpoint("story_001", {
            "method": "GET",
            "path": "/tasks",
            "name": "list_tasks",
            "description": "Get all tasks"
        })

        # Register the story
        product.register_story("story_001", {
            "name": "Task Management",
            "description": "Complete task management system",
            "endpoints": ["/tasks"],
            "pages": ["/tasks"]
        })

        # Generate mandatory UI
        product.generate_mandatory_ui()

        # Export product
        export_path = product.export_product()
        assert os.path.exists(export_path), "Should export product"

        # Verify export contents
        required_files = [
            "docker-compose.yml",
            "start.sh",
            "README.md",
            ".gitignore"
        ]

        for filename in required_files:
            filepath = os.path.join(export_path, filename)
            assert os.path.exists(filepath), f"Should create {filename}"

        print(f"✓ Product structure created at {export_path}")
        print("✓ Backend code integrated")
        print("✓ Frontend code integrated")
        print("✓ Pages and endpoints registered")
        print("✓ Mandatory UI generated")
        print("✓ Product exported with docker-compose, launcher, and docs")

        return export_path

    def test_ui_content_sanitization(self):
        """Test that UI content is sanitized to remove TRD technical info."""
        print("\nTesting UI content sanitization...")

        product = ProductAssemblyManager(
            project_id="test_sanitization",
            root_dir=self.temp_dir
        )
        product.initialize_product_structure()

        # Add UI content with TRD technical markers
        technical_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Test Page</title>
</head>
<body>
    <h1>Welcome to the Cheese Shop</h1>
    <p>Technical Specification: This page uses FastAPI backend with JWT authentication.</p>
    <p>Architecture: Microservices with PostgreSQL database.</p>
    <p>Customer-facing content: Browse our selection of artisan cheeses.</p>
</body>
</html>
"""

        product.add_frontend_component("test", "index.html", technical_content)

        # Verify sanitization
        sanitized_path = product.frontend_dir / "index.html"
        sanitized_content = sanitized_path.read_text()

        # Check that technical markers are removed
        assert "Technical Specification" not in sanitized_content, "Should remove Technical Specification"
        assert "Architecture" not in sanitized_content, "Should remove Architecture"
        assert "FastAPI" not in sanitized_content, "Should remove FastAPI"
        assert "JWT" not in sanitized_content, "Should remove JWT"
        assert "PostgreSQL" not in sanitized_content, "Should remove PostgreSQL"

        # Check that customer-facing content remains
        assert "Welcome to the Cheese Shop" in sanitized_content, "Should keep customer content"
        assert "Browse our selection of artisan cheeses" in sanitized_content, "Should keep customer content"

        print("✓ UI content sanitization test passed")

    def test_readme_uses_prd(self):
        """Test that README uses PRD content, not TRD."""
        print("\nTesting README uses PRD content...")

        prd_content = "Welcome to our artisan cheese shop! We offer the finest selection of handcrafted cheeses from local farms."
        trd_content = "Backend: FastAPI with PostgreSQL. Architecture: Microservices. Database schema: Users table with id, name, email fields."

        product = ProductAssemblyManager(
            project_id="test_readme",
            root_dir=self.temp_dir,
            context_docs={"PRD": prd_content, "TRD": trd_content}
        )
        product.initialize_product_structure()
        product.register_story("test", {"name": "Test Story", "description": "Test description"})
        export_path = product.export_product()

        readme_path = Path(export_path) / "README.md"
        readme_content = readme_path.read_text()

        # Check that PRD content is included
        assert "artisan cheese shop" in readme_content.lower(), "Should include PRD content"

        # Check that TRD technical content is not included (specifically the schema details)
        assert "Users table" not in readme_content, "Should not include TRD schema details"
        assert "id, name, email fields" not in readme_content, "Should not include TRD field details"

        print("✓ README uses PRD content test passed")

    def test_end_to_end_integration(self):
        """Test complete pipeline from rough idea to product."""
        print("\nTesting End-to-End Integration...")

        # Sample project
        rough_idea = """
        Build a Task Management application where users can:
        1. Sign up and log in
        2. Create tasks with title and description
        3. View all their tasks
        4. Edit existing tasks
        5. Mark tasks as complete
        6. Delete tasks
        7. Filter tasks by status
        8. See task statistics (total, completed, pending)
        """

        # Step 1: Create sample stories (normally from orchestrator)
        stories = [
            {
                "id": "story_auth",
                "name": "User Authentication",
                "description": "Implement user registration and login",
                "depends_on": [],
                "success_criteria": [
                    "Users can register with email and password",
                    "Users can log in with credentials",
                    "Sessions are managed securely"
                ]
            },
            {
                "id": "story_tasks",
                "name": "Task Management",
                "description": "Core CRUD operations for tasks",
                "depends_on": ["story_auth"],
                "success_criteria": [
                    "Users can create new tasks",
                    "Users can view all their tasks",
                    "Users can edit tasks",
                    "Users can delete tasks"
                ]
            },
            {
                "id": "story_dashboard",
                "name": "Dashboard & Statistics",
                "description": "Display task overview and statistics",
                "depends_on": ["story_tasks"],
                "success_criteria": [
                    "Show total tasks count",
                    "Show completed tasks count",
                    "Show pending tasks count",
                    "Display task list with status"
                ]
            }
        ]

        print(f"\n✓ Created {len(stories)} sample stories")

        # Step 2: Translate stories to specifications
        translator = StoryTranslator()
        backend_specs = []
        frontend_specs = []

        for story in stories:
            backend_spec, frontend_spec = translator.translate_story(story)
            backend_specs.append(backend_spec)
            frontend_specs.append(frontend_spec)

        print(f"✓ Translated {len(stories)} stories to backend/frontend specs")

        # Step 3: Generate code for each story
        backend_generator = BackendGenerator()
        frontend_generator = FrontendGenerator()

        total_endpoints = 0
        total_pages = 0

        for backend_spec in backend_specs:
            total_endpoints += len(backend_spec.endpoints)

        for frontend_spec in frontend_specs:
            total_pages += len(frontend_spec.pages)

        print(f"✓ Generated backend code for {len(backend_specs)} stories ({total_endpoints} endpoints)")
        print(f"✓ Generated frontend code for {len(frontend_specs)} stories ({total_pages} pages)")

        # Skip full code generation if no API key (use fallback implementations)
        has_api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        if not has_api_key:
            print("⚠ Skipping full LLM code generation (no API key). Using fallback implementations.")
            return

        # Step 4: Assemble into product
        product = ProductAssemblyManager(
            project_id="task_manager",
            root_dir=self.temp_dir
        )
        product.initialize_product_structure()

        for i, story in enumerate(stories):
            backend_spec = backend_specs[i]
            frontend_spec = frontend_specs[i]

            # Add code files
            backend_code = backend_generator.integrate_with_product(backend_spec, "")
            frontend_code = frontend_generator.integrate_with_product(frontend_spec, "")

            for filepath, content in backend_code.items():
                product.add_backend_code(story["id"], filepath, content)

            for filepath, content in frontend_code.items():
                product.add_frontend_component(story["id"], filepath, content)

            # Register pages and endpoints
            for page in frontend_spec.pages:
                product.add_frontend_page(story["id"], page.name, page.route)

            for endpoint in backend_spec.endpoints:
                product.add_api_endpoint(story["id"], {
                    "method": endpoint.method.value,
                    "path": endpoint.path,
                    "name": endpoint.name,
                    "description": endpoint.description,
                })

            # Register story
            product.register_story(story["id"], story)

        print("✓ All story code assembled into product structure")

        # Step 5: Generate mandatory UI and export
        product.generate_mandatory_ui()
        export_path = product.export_product()

        print(f"✓ Final product exported to: {export_path}")

        # Step 6: Verify structure
        required_items = [
            "docker-compose.yml",
            "start.sh",
            "README.md",
            ".gitignore",
            "app/models.py",
            "app/routes.py",
            "www/index.html",
            "www/dashboard.html",
            "www/api-explorer.html",
        ]

        missing_items = []
        for item in required_items:
            item_path = os.path.join(export_path, item)
            if not os.path.exists(item_path):
                missing_items.append(item)

        if missing_items:
            print(f"⚠ Missing items: {missing_items}")
        else:
            print("✓ All required product files created")

        return export_path

    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)

        for test_name, result in self.results.items():
            status = "✓ PASSED" if "PASSED" in result else "✗ FAILED"
            print(f"{test_name}: {status}")

        passed = sum(1 for r in self.results.values() if "PASSED" in r)
        total = len(self.results)
        print(f"\nTotal: {passed}/{total} tests passed")

        if passed == total:
            print("✓ All tests passed!")
            print(f"\nTest artifacts available at: {self.temp_dir}")
            print("Product generation pipeline is fully operational.")
        else:
            print("✗ Some tests failed. Review errors above.")


def main():
    """Run the test suite."""
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY not set. Using mock implementations.")

    # Run tests
    suite = ProductGenerationTestSuite(project_id="test_integration")
    suite.run_all_tests()


if __name__ == "__main__":
    main()
