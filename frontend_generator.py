"""
Module 7: Frontend Generator
Generates vanilla JavaScript frontend code from FrontendSpec specifications.
"""

import json
from typing import Dict, Optional
import instructor
import litellm
from pydantic import BaseModel, Field
from story_translator import FrontendSpec, UIPage, UIComponent


class GeneratedFrontendCode(BaseModel):
    """Response from frontend code generation."""
    pages: Dict[str, str] = Field(..., description="HTML page files (filename -> content)")
    components: Dict[str, str] = Field(..., description="JavaScript component files (filename -> content)")
    styles: Dict[str, str] = Field(..., description="CSS style files (filename -> content)")
    navigation_update: str = Field(..., description="Navigation registration code")


class FrontendGeneratorConfig(BaseModel):
    """Configuration for the frontend generator."""
    llm_model: str = Field(
        default="meta-llama/llama-3.3-70b-instruct:free",
        description="LLM model to use"
    )
    api_key: Optional[str] = Field(default=None, description="API key for LLM")


class FrontendGenerator:
    """
    Generates vanilla JavaScript frontend code from FrontendSpec.
    Creates HTML pages, JavaScript components, and CSS styling.
    """

    SYSTEM_PROMPT = """You are a Senior Frontend Developer specializing in vanilla JavaScript, HTML, and CSS.
Your task is to generate production-quality frontend code that:
- Uses semantic HTML5
- Implements responsive CSS Grid/Flexbox layouts
- Uses vanilla JavaScript (no frameworks like React)
- Integrates with REST API using fetch()
- Has proper error handling and user feedback
- Supports dark/light mode theming
- Follows accessibility (WCAG 2.1) guidelines
- Uses CSS custom properties for theming

CRITICAL STANDARDS:
- No external dependencies (CSS frameworks, JS libraries)
- All JavaScript is vanilla ES6+
- Fetch API for all HTTP requests (no jQuery)
- Event delegation for dynamic content
- Local storage for persistence
- Proper form validation
- Error boundary patterns

FRONTEND ARCHITECTURE:
- Single page application with client-side routing
- API client helper (fetchAPI) provided by framework
- Navigation system manages page registration
- State stored in window object or localStorage
- Components use web components or plain HTML + JS

CODE QUALITY:
- Type hints as JSDoc comments
- Proper error handling (try/catch, response validation)
- Loading states and spinners
- Debouncing for search/input
- Proper tab order and focus management
- No console.log() in production code, use proper logging"""

    USER_PROMPT_TEMPLATE = """Generate vanilla JavaScript frontend code for this story:

STORY: {story_name}
DESCRIPTION: {story_description}

PRODUCT CONTEXT (use this to match the output type and complexity to the actual product):
PRD Summary: {prd_context}

FRONTEND SPECIFICATION:
{frontend_spec}

Generate the following:

1. HTML Pages (one file per page)
   - Semantic HTML5
   - Proper form structure
   - ARIA labels for accessibility
   - Responsive containers
   - Loading states (spinner divs)

2. JavaScript Components
   - Page initialization functions
   - Event handlers
   - API integration
   - Form validation
   - DOM manipulation utilities

3. CSS Styles
   - Responsive layouts
   - Dark/light mode support
   - Component-specific styling
   - Animations and transitions
   - Mobile-first approach

4. Navigation Registration
   - Code to register pages in the nav system
   - Route definitions
   - Access control (auth required)

Use the fetchAPI helper for all API calls.
Follow this pattern:
  const response = await fetchAPI('/endpoint', {{method: 'POST', body: data}});

Return valid JSON with keys: pages, components, styles, navigation_update"""

    def __init__(self, config: Optional[FrontendGeneratorConfig] = None):
        """Initialize the frontend generator."""
        self.config = config or FrontendGeneratorConfig()
        self.client = instructor.from_litellm(litellm.completion)
        self.api_key = self.config.api_key

    def generate_code(
        self,
        frontend_spec: FrontendSpec,
        context_docs: Optional[Dict[str, str]] = None
    ) -> GeneratedFrontendCode:
        """
        Generate frontend code from a FrontendSpec.
        Tries LLM first, falls back to deterministic generators if LLM fails.

        Args:
            frontend_spec: The frontend specification to generate code from
            context_docs: Optional PRD/TRD context for product-aware generation

        Returns:
            GeneratedFrontendCode with all HTML, JS, and CSS files
        """
        context_docs = context_docs or {}
        try:
            # Try LLM-based generation first
            spec_json = json.dumps(frontend_spec.to_dict(), indent=2)
            prd_context = (context_docs.get("PRD", context_docs.get("prd", "")) or "Not available")[:800]
            user_prompt = self.USER_PROMPT_TEMPLATE.format(
                story_name=frontend_spec.story_name,
                story_description=frontend_spec.description,
                prd_context=prd_context,
                frontend_spec=spec_json,
            )

            response = self.client.create(
                model=self.config.llm_model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_model=GeneratedFrontendCode,
                api_key=self.api_key,
                max_retries=1,
            )
            return response
        except Exception as e:
            # Fallback to deterministic code generation
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"⚠ LLM generation failed ({type(e).__name__}: {str(e)[:100]}), using fallback generators")
            print(f"⚠ LLM generation failed ({type(e).__name__}), using fallback generators")

            # Generate pages
            pages = {}
            for page in frontend_spec.pages:
                html_content = self.generate_page_template(page)
                pages[f"{page.name}.html"] = html_content

            # Generate components
            components = {}
            for component in frontend_spec.components:
                js_content = self.generate_component_module(component)
                components[f"{component.name}.js"] = js_content

            # Generate styles
            styles = {}
            for component in frontend_spec.components:
                css_content = self.generate_component_styles(component)
                styles[f"{component.name}.css"] = css_content

            # Generate navigation code
            navigation_code = self.generate_navigation_code(frontend_spec)

            return GeneratedFrontendCode(
                pages=pages,
                components=components,
                styles=styles,
                navigation_update=navigation_code,
            )

    def generate_page_template(self, page: UIPage) -> str:
        """
        Generate HTML template for a page.
        (Alternative approach without full LLM call)
        """
        route_param = page.route.replace("/", "_").replace(":", "").replace("-", "_")

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page.title}</title>
    <link rel="stylesheet" href="/styles.css">
    <link rel="stylesheet" href="/pages/{page.name}.css">
</head>
<body>
    <nav id="navbar"></nav>
    <main id="app-content">
        <div class="page-container">
            <h1>{page.title}</h1>
            <p class="page-description">{page.description}</p>

            <!-- Page content will be rendered here -->
            <div id="page-content" class="content"></div>

            <!-- Loading state -->
            <div id="loading-spinner" class="hidden">
                <div class="spinner"></div>
                <p>Loading...</p>
            </div>

            <!-- Error display -->
            <div id="error-message" class="error hidden"></div>
        </div>
    </main>

    <script src="/api.js"></script>
    <script src="/nav.js"></script>
    <script src="/pages/{page.name}.js"></script>
    <script>
        // Initialize page when DOM is ready
        document.addEventListener('DOMContentLoaded', init{page.name}Page);
    </script>
</body>
</html>
"""
        return html

    def generate_component_module(self, component: UIComponent) -> str:
        """
        Generate JavaScript module for a component.
        """
        component_name = component.name
        camel_case_name = self._to_camel_case(component_name)

        js_code = f"""/**
 * Component: {component_name}
 * Type: {component.type}
 * Description: {component.description}
 */

class {camel_case_name.capitalize().replace('_', '')} {{
    constructor(containerSelector) {{
        this.container = document.querySelector(containerSelector);
        this.data = {{}};
    }}

    /**
     * Render the component
     */
    async render(data) {{
        this.data = data;
        this.container.innerHTML = this._template();
        this._attachEventListeners();
    }}

    /**
     * Get component template
     */
    _template() {{
        return `
            <div class="{component_name}">
                <!-- Component content here -->
            </div>
        `;
    }}

    /**
     * Attach event listeners
     */
    _attachEventListeners() {{
        // Add event delegation here
    }}

    /**
     * Cleanup
     */
    destroy() {{
        if (this.container) {{
            this.container.innerHTML = '';
        }}
    }}
}}

// Export for use in pages
if (typeof module !== 'undefined' && module.exports) {{
    module.exports = {camel_case_name.capitalize().replace('_', '')};
}}
"""
        return js_code

    def generate_page_script(self, page: UIPage) -> str:
        """
        Generate JavaScript for a page.
        """
        page_func_name = f"init{self._to_camel_case(page.name).capitalize()}Page"

        js_code = f"""/**
 * Page: {page.name}
 * Route: {page.route}
 * Title: {page.title}
 * Description: {page.description}
 */

// Page state
const pageState = {{
    loading: false,
    error: null,
    data: null,
}};

/**
 * Initialize page
 */
async function {page_func_name}() {{
    try {{
        // Show loading state
        setLoading(true);

        // Fetch data from API endpoints
        // const data = await fetchAPI('{page.api_endpoints[0] if page.api_endpoints else '/data'}');

        // Render page content
        renderPage();

        // Attach event listeners
        attachEventListeners();

        setLoading(false);
    }} catch (error) {{
        showError(error.message);
        setLoading(false);
    }}
}}

/**
 * Render page content
 */
function renderPage() {{
    const contentDiv = document.getElementById('page-content');
    contentDiv.innerHTML = `
        <p>Page content for {page.name}</p>
        <!-- Add your page-specific content here -->
    `;
}}

/**
 * Attach event listeners
 */
function attachEventListeners() {{
    // Use event delegation for dynamic content
    const contentDiv = document.getElementById('page-content');

    // Add click handlers
    contentDiv.addEventListener('click', handlePageClick);
}}

/**
 * Handle page clicks
 */
function handlePageClick(event) {{
    const target = event.target;

    if (target.classList.contains('action-button')) {{
        // Handle action button clicks
        console.log('Action button clicked');
    }}
}}

/**
 * Set loading state
 */
function setLoading(isLoading) {{
    pageState.loading = isLoading;
    const spinner = document.getElementById('loading-spinner');

    if (isLoading) {{
        spinner.classList.remove('hidden');
    }} else {{
        spinner.classList.add('hidden');
    }}
}}

/**
 * Show error message
 */
function showError(message) {{
    pageState.error = message;
    const errorDiv = document.getElementById('error-message');

    if (message) {{
        errorDiv.textContent = message;
        errorDiv.classList.remove('hidden');
    }} else {{
        errorDiv.classList.add('hidden');
    }}
}}

/**
 * Cleanup on page unload
 */
window.addEventListener('beforeunload', () => {{
    // Cleanup resources
}});
"""
        return js_code

    def generate_component_styles(self, component: UIComponent) -> str:
        """
        Generate CSS for a component.
        """
        css_code = f"""/* Component: {component.name} */

.{component.name} {{
    /* Base styles */
    padding: var(--spacing-md);
    border-radius: var(--border-radius);
    background-color: var(--bg-secondary);
    color: var(--text-primary);
}}

.{component.name}__header {{
    margin-bottom: var(--spacing-md);
    font-size: var(--font-size-lg);
    font-weight: var(--font-weight-bold);
}}

.{component.name}__content {{
    margin: var(--spacing-md) 0;
}}

.{component.name}__footer {{
    margin-top: var(--spacing-md);
    padding-top: var(--spacing-md);
    border-top: 1px solid var(--border-color);
}}

/* Responsive */
@media (max-width: 768px) {{
    .{component.name} {{
        padding: var(--spacing-sm);
    }}
}}

/* Dark mode */
@media (prefers-color-scheme: dark) {{
    .{component.name} {{
        background-color: var(--bg-secondary-dark);
        color: var(--text-primary-dark);
    }}
}}
"""
        return css_code

    def generate_navigation_code(self, frontend_spec: FrontendSpec) -> str:
        """
        Generate navigation registration code.
        """
        registration_code = """// Auto-generated navigation registration\n\n"""

        for page in frontend_spec.pages:
            registration_code += f"""registerPage(
    '{page.name}',
    '{page.route}',
    {{
        title: '{page.title}',
        description: '{page.description}',
        requiresAuth: {str(page.requires_auth).lower()},
        icon: 'icon-{page.name.replace('_', '-')}',
    }}
);
"""

        return registration_code

    def integrate_with_product(
        self,
        frontend_spec: FrontendSpec,
        output_path: str,
        context_docs: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """
        Generate all frontend code files ready for ProductAssemblyManager.

        Args:
            frontend_spec: The frontend specification
            output_path: Base path for generated files
            context_docs: Optional PRD/TRD context for product-aware generation

        Returns:
            Dictionary mapping file paths to content
        """
        generated_files = {}

        # Generate code
        code = self.generate_code(frontend_spec, context_docs)

        # Pages
        for filename, content in code.pages.items():
            generated_files[f"pages/{filename}"] = content

        # Components
        for filename, content in code.components.items():
            generated_files[f"components/{filename}"] = content

        # Styles
        for filename, content in code.styles.items():
            generated_files[f"styles/{filename}"] = content

        # Navigation
        generated_files["js/nav-registration.js"] = code.navigation_update

        return generated_files

    @staticmethod
    def _to_camel_case(snake_str: str) -> str:
        """Convert snake_case to camelCase."""
        components = snake_str.split('_')
        return components[0] + ''.join(x.title() for x in components[1:])

    @staticmethod
    def _to_pascal_case(snake_str: str) -> str:
        """Convert snake_case to PascalCase."""
        components = snake_str.split('_')
        return ''.join(x.title() for x in components)
