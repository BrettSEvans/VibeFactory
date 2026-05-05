"""
Module 7: Frontend Generator
Generates vanilla JavaScript frontend code from FrontendSpec specifications.
"""

import json
import time
import logging
from typing import Dict, Optional
import instructor
import litellm
from pydantic import BaseModel, Field
from story_translator import FrontendSpec, UIPage, UIComponent

logger = logging.getLogger(__name__)


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
    api_key: Optional[str] = Field(default=None, description="API key for LLM provider")
    api_base: Optional[str] = Field(default=None, description="Custom API base URL for OpenAI-compatible providers")


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

PRODUCT CONTEXT (read the PRD to understand what the user actually requested):
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
   - Page content should match the FrontendSpec and PRD requirements EXACTLY — no invented features

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

    STATIC_SYSTEM_PROMPT = """You are a Senior Frontend Developer specializing in beautiful, print-ready HTML advertisements and promotional materials.

Your task is to generate a SINGLE, COMPLETELY SELF-CONTAINED HTML file. All CSS must be inline in a <style> block. No external stylesheets. No JavaScript frameworks. No navigation bars. No login buttons. No SPA routing.

RULES — NEVER VIOLATE THESE:
- ONE file only. Everything (HTML structure, all CSS) lives inside a single .html file.
- NO <link rel="stylesheet"> tags pointing to external files.
- NO <script src="..."> tags.
- NO navigation bar, header nav, login/logout links, or page routing.
- NO references to /api.js, /nav.js, fetchAPI, registerPage, or any SPA infrastructure.
- The output should be printable and visually complete with zero dependencies.
- Design should match the product type: advertisement = bold colors, clear call-to-action, contact info.
- Use emoji, icons, and compelling copy appropriate to the business.

OUTPUT: Return valid JSON with keys:
  pages: {{ "index.html": "<full self-contained HTML string>" }}
  components: {{}}
  styles: {{}}
  navigation_update: ""
"""

    STATIC_USER_PROMPT_TEMPLATE = """Create a beautiful, self-contained HTML advertisement for:

PRODUCT: {story_name}
DESCRIPTION: {story_description}

Requirements:
- Single HTML file with ALL CSS inlined in a <style> tag
- Visually striking design appropriate for: {story_description}
- Include: headline, key services/features (3-5 items), a compelling tagline, and contact/CTA section
- Use attractive colors, spacing, and typography (web-safe fonts or Google Fonts via @import)
- Suitable for printing (A4) or viewing in a browser
- NO navigation bar, NO login links, NO API calls, NO JavaScript unless purely decorative

Return JSON: {{ "pages": {{ "index.html": "<complete html>" }}, "components": {{}}, "styles": {{}}, "navigation_update": "" }}"""

    PRD_FRONTEND_SYSTEM = """You are a Senior Frontend Developer generating a complete frontend application from PRD (Product Requirements Document).

CRITICAL CONSTRAINTS:
- You ONLY read the PRD — never read story names, story descriptions, or technical specs
- You ONLY generate frontend code (HTML, CSS, JavaScript) for user-facing features
- You MUST NOT include any backend integration, API calls, or technical infrastructure details
- You MUST NOT reference backend technologies (FastAPI, SQLAlchemy, database schemas, etc.)
- You MUST NOT include authentication UI elements unless explicitly mentioned in PRD vision/features

FILE STRUCTURE — follow exactly, all paths must match this layout:
  frontend/
    index.html          ← landing page (root level)
    styles.css          ← shared stylesheet
    api.js              ← shared API helper
    nav.js              ← shared navigation (auto-loaded, do NOT include in components)
    pages/
      catalog.html      ← each additional page lives here
      detail.html
      login.html
      ...

LINK AND PATH RULES — violations cause 404 errors, follow precisely:
- In index.html: link to other pages as   href="pages/pagename.html"
- In pages/*.html: link to other pages as href="pagename.html"  (same directory, NO pages/ prefix)
- In pages/*.html: link back to home as   href="../index.html"
- CTA buttons ("View Details", "Learn More", etc.) must use the SAME rules above
- NEVER use absolute paths starting with /
- NEVER use paths like /pages/foo.html or /foo.html
- CSS: pages use  href="../styles.css"   index uses  href="styles.css"
- JS:  pages use  src="../js/api.js"     index uses  src="js/api.js"

FRONTEND GENERATION RULES:
- Generate a complete multi-page application with working navigation
- Create semantic HTML5 with accessibility support (WCAG 2.1)
- Use responsive CSS Grid/Flexbox for all layouts
- Write vanilla JavaScript (no frameworks) with proper error handling
- Include proper form validation and user feedback
- Support dark/light mode with CSS custom properties
- All code must be production-ready with no TODOs or placeholders

OUTPUT FORMAT:
Return JSON with exactly these keys:
{
  "pages": {"page_name.html": "<complete HTML>"},
  "components": {"component_name.js": "<vanilla JavaScript>"},
  "styles": {"component_name.css": "<CSS>"},
  "navigation_update": "<registration code>"
}"""

    PRD_FRONTEND_USER = """Generate a complete frontend application from this PRD ONLY. Do NOT reference any story context, technical requirements, or backend details.

PRODUCT REQUIREMENTS DOCUMENT:
{prd_content}

GENERATION INSTRUCTIONS:
1. Extract the product vision and user-facing features from the PRD
2. Design a complete frontend experience with:
   - Multiple pages reflecting different user journeys mentioned in PRD
   - Forms for data entry/user interaction (if applicable)
   - Display components for content presentation
   - Proper navigation between pages
3. Generate production-ready code:
   - Semantic HTML5 with proper structure
   - Responsive CSS with mobile-first approach
   - Vanilla JavaScript with fetch() API for any external calls
   - Proper error handling and loading states
4. Ensure NO backend-specific details appear in the code:
   - No API endpoint hardcoding (use placeholder routes)
   - No database schema references
   - No authentication tokens or JWT references
   - No backend technology names

Return valid JSON with pages, components, styles, and navigation_update keys."""

    def __init__(self, config: Optional[FrontendGeneratorConfig] = None):
        """Initialize the frontend generator."""
        self.config = config or FrontendGeneratorConfig()
        self.client = instructor.from_litellm(litellm.completion)
        self.api_key = self.config.api_key

    def generate_code(
        self,
        frontend_spec: FrontendSpec,
        context_docs: Optional[Dict[str, str]] = None,
        max_retries: int = 3,
        timeout_seconds: int = 60
    ) -> GeneratedFrontendCode:
        """
        Generate frontend code from a FrontendSpec with rate-limit aware retry logic.
        Tries LLM first with exponential backoff, falls back to deterministic generators if LLM fails.

        Args:
            frontend_spec: The frontend specification to generate code from
            context_docs: Optional PRD/TRD context for product-aware generation
            max_retries: Maximum number of retry attempts (default 3)
            timeout_seconds: Timeout for each LLM call in seconds (default 60)

        Returns:
            GeneratedFrontendCode with all HTML, JS, and CSS files
        """
        context_docs = context_docs or {}

        # Static products (ads, flyers, promo pages) get a single self-contained HTML file
        if getattr(frontend_spec, 'is_frontend_only', False):
            return self._generate_static_html(frontend_spec)

        # Try LLM-based generation with exponential backoff for rate limits
        for attempt in range(max_retries):
            try:
                # Try LLM-based generation first
                spec_json = json.dumps(frontend_spec.to_dict(), indent=2)
                # Use shorter truncation (500 chars) to avoid timeouts on large docs
                prd_context = (context_docs.get("PRD", context_docs.get("prd", "")) or "Not available")[:500]
                user_prompt = self.USER_PROMPT_TEMPLATE.format(
                    story_name=frontend_spec.story_name,
                    story_description=frontend_spec.description,
                    prd_context=prd_context,
                    frontend_spec=spec_json,
                )

                completion_kwargs = {
                    "model": self.config.llm_model,
                    "messages": [
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    "response_model": GeneratedFrontendCode,
                    "api_key": self.api_key,
                    "timeout": timeout_seconds,
                    "max_retries": 0,  # Handle retries manually with exponential backoff
                }
                if self.config.api_base:
                    completion_kwargs["api_base"] = self.config.api_base

                logger.info(f"Frontend generation attempt {attempt + 1}/{max_retries}")
                response = self.client.create(**completion_kwargs)
                return response

            except Exception as e:
                error_str = str(e)
                is_rate_limit = "429" in error_str or "rate" in error_str.lower() or "quota" in error_str.lower()
                is_timeout = "timeout" in error_str.lower() or "deadline" in error_str.lower()

                if attempt < max_retries - 1:
                    # Backoff strategy based on error type:
                    # - Rate limit (429): need >= 60s to let the RPM window reset
                    #   Wait 20s → 60s across retries
                    # - Timeout/stall: API was unresponsive; short wait then retry
                    #   Wait 5s → 15s across retries
                    # - Other errors: moderate wait
                    #   Wait 10s → 30s across retries
                    if is_rate_limit:
                        wait_time = [20, 60][min(attempt, 1)]
                    elif is_timeout:
                        wait_time = [5, 15][min(attempt, 1)]
                    else:
                        wait_time = [10, 30][min(attempt, 1)]

                    logger.warning(f"⚠ Frontend LLM attempt {attempt + 1} failed ({type(e).__name__}). "
                                 f"Rate limit: {is_rate_limit}, Timeout: {is_timeout}. "
                                 f"Retrying in {wait_time}s...")
                    print(f"⚠ Frontend generation attempt {attempt + 1} failed ({type(e).__name__}). Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.warning(f"⚠ LLM generation failed after {max_retries} attempts ({type(e).__name__}: {str(e)[:100]}), using fallback generators")
                    print(f"⚠ LLM generation failed after {max_retries} attempts, using fallback generators")

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

    def generate_from_prd(
        self,
        prd_content: str,
        max_retries: int = 3,
        timeout_seconds: int = 120
    ) -> GeneratedFrontendCode:
        """
        Generate complete frontend from PRD in a single LLM call.
        TRACK 1: One-shot frontend generation, PRD-only context.

        Args:
            prd_content: Complete PRD text (no story data)
            max_retries: Maximum retry attempts for rate limits
            timeout_seconds: LLM request timeout

        Returns:
            GeneratedFrontendCode with all frontend files
        """
        for attempt in range(max_retries):
            try:
                user_prompt = self.PRD_FRONTEND_USER.format(prd_content=prd_content)

                completion_kwargs = {
                    "model": self.config.llm_model,
                    "messages": [
                        {"role": "system", "content": self.PRD_FRONTEND_SYSTEM},
                        {"role": "user", "content": user_prompt},
                    ],
                    "response_model": GeneratedFrontendCode,
                    "api_key": self.api_key,
                    "timeout": timeout_seconds,
                    "max_retries": 0,  # Manual retries with exponential backoff
                }
                if self.config.api_base:
                    completion_kwargs["api_base"] = self.config.api_base

                logger.info(f"PRD frontend generation attempt {attempt + 1}/{max_retries}")
                response = self.client.create(**completion_kwargs)
                return response

            except Exception as e:
                error_str = str(e)
                is_rate_limit = "429" in error_str or "rate" in error_str.lower() or "quota" in error_str.lower()
                is_timeout = "timeout" in error_str.lower() or "deadline" in error_str.lower()

                if attempt < max_retries - 1:
                    if is_rate_limit:
                        wait_time = [20, 60][min(attempt, 1)]
                    elif is_timeout:
                        wait_time = [10, 30][min(attempt, 1)]
                    else:
                        wait_time = [15, 45][min(attempt, 1)]

                    logger.warning(f"⚠ PRD frontend LLM attempt {attempt + 1} failed ({type(e).__name__}). "
                                 f"Retrying in {wait_time}s...")
                    print(f"⚠ PRD frontend generation attempt {attempt + 1} failed. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.warning(f"⚠ PRD frontend LLM failed after {max_retries} attempts, using fallback")
                    print(f"⚠ PRD frontend generation failed after {max_retries} attempts, using fallback")

        # Fallback: Generate minimal frontend structure
        fallback_html = self._generate_fallback_frontend()
        return GeneratedFrontendCode(
            pages={"index.html": fallback_html},
            components={},
            styles={},
            navigation_update="",
        )

    def write_prd_frontend(self, code: GeneratedFrontendCode) -> Dict[str, str]:
        """
        Write PRD-generated frontend code to files.
        Returns file mapping ready for ProductAssemblyManager.

        Args:
            code: GeneratedFrontendCode from generate_from_prd()

        Returns:
            Dictionary mapping file paths to content
        """
        files = {}

        # Main index page
        if "index.html" in code.pages:
            files["index.html"] = code.pages["index.html"]
        else:
            # Use first page as index
            files["index.html"] = next(iter(code.pages.values()), "")

        # Additional pages
        for filename, content in code.pages.items():
            if filename != "index.html":
                files[f"pages/{filename}"] = content

        # Components
        for filename, content in code.components.items():
            files[f"components/{filename}"] = content

        # Styles
        for filename, content in code.styles.items():
            files[f"styles/{filename}"] = content

        # Navigation registration
        if code.navigation_update:
            files["js/nav-registration.js"] = code.navigation_update

        return files

    def _generate_fallback_frontend(self) -> str:
        """Generate minimal fallback frontend when LLM fails."""
        html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Application</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            color: #333;
        }
        nav {
            background: white;
            padding: 1rem 2rem;
            border-bottom: 1px solid #ddd;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        nav a {
            margin-right: 2rem;
            text-decoration: none;
            color: #3498db;
        }
        nav a:hover { text-decoration: underline; }
        main {
            max-width: 1200px;
            margin: 2rem auto;
            padding: 0 2rem;
        }
        section {
            background: white;
            padding: 2rem;
            border-radius: 8px;
            margin-bottom: 2rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        h1 { color: #2c3e50; margin-bottom: 1rem; }
        p { line-height: 1.6; margin-bottom: 1rem; }
    </style>
</head>
<body>
    <nav>
        <a href="index.html">Home</a>
    </nav>
    <main>
        <section>
            <h1>Welcome</h1>
            <p>Application frontend loaded successfully.</p>
        </section>
    </main>
</body>
</html>"""
        return html

    def _generate_static_html(self, frontend_spec: FrontendSpec) -> 'GeneratedFrontendCode':
        """
        Generate a single self-contained HTML file for static products (ads, flyers, etc.).
        Uses the static-specific LLM prompt; falls back to a minimal inline template.
        """
        import logging
        logger = logging.getLogger(__name__)

        try:
            user_prompt = self.STATIC_USER_PROMPT_TEMPLATE.format(
                story_name=frontend_spec.story_name,
                story_description=frontend_spec.description,
            )
            completion_kwargs = {
                "model": self.config.llm_model,
                "messages": [
                    {"role": "system", "content": self.STATIC_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "response_model": GeneratedFrontendCode,
                "api_key": self.api_key,
                "max_retries": 1,
            }
            if self.config.api_base:
                completion_kwargs["api_base"] = self.config.api_base

            response = self.client.create(**completion_kwargs)
            # Ensure nav-SPA artefacts are stripped out of the LLM response
            response.components = {}
            response.styles = {}
            response.navigation_update = ""
            return response
        except Exception as e:
            logger.warning(f"⚠ Static LLM generation failed ({type(e).__name__}: {str(e)[:100]}), using fallback")
            description = frontend_spec.description
            title = frontend_spec.story_name
            html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 40px; background: #f9f9f9; color: #333; }}
        .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; margin-top: 0; }}
        p {{ line-height: 1.7; font-size: 16px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        <p>{description}</p>
    </div>
</body>
</html>"""
            return GeneratedFrontendCode(
                pages={"index.html": html},
                components={},
                styles={},
                navigation_update="",
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
    <link rel="stylesheet" href="../styles.css">
    <link rel="stylesheet" href="{page.name}.css">
</head>
<body>
    <nav id="navbar"></nav>
    <main id="app-content">
        <div class="page-container">
            <h1>{page.title}</h1>
            <p class="page-description">{page.description}</p>

            <!-- Page content -->
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

    <script src="../js/api.js"></script>
    <script src="../js/nav.js"></script>
    <script src="{page.name}.js"></script>
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

    def _generate_landing_page(self, frontend_spec: FrontendSpec, prd_context: str = "") -> str:
        """Generate a proper landing page (index.html) for multi-page applications using PRD context.

        CRITICAL: When PRD context is available, extract title and description from PRD only.
        Never use story_name or story description — these contain technical/TRD content.
        """
        # Extract title and description from PRD if available (NOT from story)
        title = frontend_spec.story_name  # fallback
        description = frontend_spec.description  # fallback

        if prd_context:
            lines = prd_context.split('\n')

            # Extract product name from **Project:** line
            for line in lines:
                if '**Project:**' in line:
                    # Extract text after "**Project:** " marker
                    project_text = line.split('**Project:**')[1].strip()
                    if project_text:
                        title = project_text
                        break

            # Extract business purpose from "Vision & Success Statement" or "Purpose & Scope" section
            purpose_lines = []
            in_purpose_section = False
            for i, line in enumerate(lines):
                # Look for Vision, Purpose, or Scope section headers
                if any(header in line for header in [
                    '### 1. Vision',
                    '## 1. Vision',
                    '### Vision & Success',
                    '## Vision & Success',
                    '### 1. Purpose & Scope',
                    '## 1. Purpose & Scope'
                ]):
                    in_purpose_section = True
                    continue

                if in_purpose_section:
                    # Stop when we hit the next section
                    if (line.startswith('###') or line.startswith('##')) and line.strip():
                        break

                    # Collect non-empty, non-separator lines
                    if line.strip() and not line.startswith('---') and not line.startswith('|'):
                        # Skip technical/implementation keywords
                        if not any(tech in line for tech in [
                            'Technical', 'TRD', 'Database', 'API', 'FastAPI', 'Backend',
                            'CI/CD', 'GitHub', 'Workflow', 'WSGI', 'Flask', 'Apache',
                            'Nginx', 'environment', 'caching', 'deployment', 'hosted',
                            'server', 'infrastructure'
                        ]):
                            purpose_lines.append(line.strip())

            # Use extracted purpose or fallback to frontend_spec description
            if purpose_lines:
                description = ' '.join(purpose_lines)[:300].strip()

        # Extract page links from frontend spec
        page_links = ""
        if frontend_spec.pages:
            for page in frontend_spec.pages:
                page_links += f'<li><a href="pages/{page.name}.html">{page.title}</a></li>\n                '

        # Use PRD context to create product-specific content snippet
        prd_snippet = ""
        if prd_context:
            # Extract business-focused content from PRD (skip headers and technical sections)
            lines = prd_context.split('\n')
            business_lines = []

            for line in lines:
                # Skip headers, technical markers, and empty lines
                if (line.strip() and
                    not line.startswith('#') and
                    not line.startswith('|') and
                    not line.startswith('**') and
                    'Technical' not in line and
                    'TRD' not in line and
                    'Database' not in line and
                    'API' not in line and
                    'FastAPI' not in line and
                    'Backend' not in line and
                    'CI/CD' not in line and
                    'GitHub' not in line and
                    'Workflow' not in line):
                    business_lines.append(line.strip())

            # Extract key business statements (usually vision, goals, or features)
            features_text = '\n'.join(business_lines[:10])[:300]
            if features_text:
                prd_snippet = f"<p>{features_text}</p>"

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Home</title>
    <link rel="stylesheet" href="styles.css">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            margin: 0;
            padding: 0;
            background: #f5f5f5;
        }}
        nav {{
            display: flex;
            gap: 1rem;
            align-items: center;
            padding: 1rem 2rem;
            background: #fff;
            border-bottom: 1px solid #ddd;
            margin-bottom: 2rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        nav a {{
            text-decoration: none;
            color: #333;
            padding: 0.5rem 1rem;
            border-radius: 4px;
            transition: background 0.2s;
        }}
        nav a:hover {{
            background: #e0e0e0;
        }}
        nav a:first-child {{
            font-weight: bold;
            font-size: 1.1rem;
        }}
        nav > div {{
            margin-left: auto;
        }}
        main {{
            max-width: 1000px;
            margin: 0 auto;
            padding: 0 2rem;
        }}
        section {{
            background: white;
            padding: 2rem;
            margin-bottom: 2rem;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            margin-top: 0;
        }}
        h2 {{
            color: #34495e;
            border-bottom: 2px solid #3498db;
            padding-bottom: 0.5rem;
        }}
        ul {{
            line-height: 1.8;
        }}
        a {{
            color: #3498db;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        code {{
            background: #f5f5f5;
            padding: 0.2rem 0.4rem;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }}
        footer {{
            text-align: center;
            padding: 2rem;
            color: #999;
            border-top: 1px solid #ddd;
            margin-top: 4rem;
        }}
    </style>
</head>
<body>
    <nav>
        <a href="index.html">{title}</a>
        <div>
            <a href="pages/login.html" style="display: none;">Admin Login</a>
        </div>
    </nav>

    <main>
        <section>
            <h1>Welcome to {title}</h1>
            <p>Explore the features and pages below to get started.</p>
        </section>

        <section>
            <h2>Pages</h2>
            <ul>
                {page_links}
            </ul>
        </section>
    </main>

    <footer>
        <p>&copy; 2026 {title}. All rights reserved.</p>
    </footer>

    <script src="js/nav.js"></script>
</body>
</html>"""
        return html

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

        # Static products: single index.html at the frontend root, nothing else
        if getattr(frontend_spec, 'is_frontend_only', False):
            html_content = code.pages.get("index.html", next(iter(code.pages.values()), ""))
            generated_files["index.html"] = html_content
            return generated_files

        # Dynamic multi-page products: pages in pages/ directory + proper index.html at root
        # Generate landing page (index.html) with PRD context
        prd_context = context_docs.get("PRD", "") if context_docs else ""
        generated_files["index.html"] = self._generate_landing_page(frontend_spec, prd_context)

        # Generate individual pages
        for filename, content in code.pages.items():
            generated_files[f"pages/{filename}"] = content

        for filename, content in code.components.items():
            generated_files[f"components/{filename}"] = content

        for filename, content in code.styles.items():
            generated_files[f"styles/{filename}"] = content

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
