"""
Module 5: Story Translator
Converts user stories from the STORIES phase into backend and frontend specifications.
"""

import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class HTTPMethod(Enum):
    """HTTP methods for API endpoints."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


@dataclass
class APIEndpoint:
    """Specification for a single API endpoint."""
    method: HTTPMethod
    path: str
    name: str  # Descriptive name (e.g., "create_user")
    description: str
    request_body: Optional[Dict[str, str]] = None  # JSON schema for request
    response_body: Optional[Dict[str, str]] = None  # JSON schema for response
    required_params: List[str] = field(default_factory=list)  # Path/query params


@dataclass
class DatabaseModel:
    """Specification for a database model."""
    name: str  # e.g., "User", "Task"
    plural: str  # e.g., "users", "tasks"
    description: str
    fields: Dict[str, str] = field(default_factory=dict)  # field_name: field_type
    relationships: Dict[str, str] = field(default_factory=dict)  # field_name: related_model
    indexes: List[str] = field(default_factory=list)  # Fields to index


@dataclass
class BackendSpec:
    """Complete backend specification for a story."""
    story_id: str
    story_name: str
    description: str
    endpoints: List[APIEndpoint] = field(default_factory=list)
    models: List[DatabaseModel] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)  # External packages
    middleware: List[str] = field(default_factory=list)  # Auth, logging, etc.
    environment_vars: Dict[str, str] = field(default_factory=dict)
    requires_backend: bool = True  # False for static/HTML-only products

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "story_id": self.story_id,
            "story_name": self.story_name,
            "description": self.description,
            "requires_backend": self.requires_backend,
            "endpoints": [
                {
                    "method": ep.method.value,
                    "path": ep.path,
                    "name": ep.name,
                    "description": ep.description,
                    "request_body": ep.request_body,
                    "response_body": ep.response_body,
                    "required_params": ep.required_params,
                }
                for ep in self.endpoints
            ],
            "models": [
                {
                    "name": m.name,
                    "plural": m.plural,
                    "description": m.description,
                    "fields": m.fields,
                    "relationships": m.relationships,
                    "indexes": m.indexes,
                }
                for m in self.models
            ],
            "dependencies": self.dependencies,
            "middleware": self.middleware,
            "environment_vars": self.environment_vars,
        }


@dataclass
class UIComponent:
    """Specification for a UI component."""
    name: str
    type: str  # "form", "table", "card", "modal", "navbar", etc.
    description: str
    inputs: Dict[str, str] = field(default_factory=dict)  # field_name: field_type
    outputs: List[str] = field(default_factory=list)  # Events or callbacks
    api_calls: List[str] = field(default_factory=list)  # Endpoint names used


@dataclass
class UIPage:
    """Specification for a UI page."""
    name: str
    route: str  # e.g., "/tasks", "/users/:id"
    title: str
    description: str
    components: List[UIComponent] = field(default_factory=list)
    api_endpoints: List[str] = field(default_factory=list)  # Endpoint names used
    requires_auth: bool = True


@dataclass
class FrontendSpec:
    """Complete frontend specification for a story."""
    story_id: str
    story_name: str
    description: str
    pages: List[UIPage] = field(default_factory=list)
    components: List[UIComponent] = field(default_factory=list)  # Reusable components
    api_endpoints: List[str] = field(default_factory=list)  # Backend endpoints used
    state_management: Dict[str, str] = field(default_factory=dict)  # Key: value type
    styles: Dict[str, str] = field(default_factory=dict)  # CSS classes/themes

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "story_id": self.story_id,
            "story_name": self.story_name,
            "description": self.description,
            "pages": [
                {
                    "name": p.name,
                    "route": p.route,
                    "title": p.title,
                    "description": p.description,
                    "components": [
                        {
                            "name": c.name,
                            "type": c.type,
                            "description": c.description,
                            "inputs": c.inputs,
                            "outputs": c.outputs,
                            "api_calls": c.api_calls,
                        }
                        for c in p.components
                    ],
                    "api_endpoints": p.api_endpoints,
                    "requires_auth": p.requires_auth,
                }
                for p in self.pages
            ],
            "components": [
                {
                    "name": c.name,
                    "type": c.type,
                    "description": c.description,
                    "inputs": c.inputs,
                    "outputs": c.outputs,
                    "api_calls": c.api_calls,
                }
                for c in self.components
            ],
            "api_endpoints": self.api_endpoints,
            "state_management": self.state_management,
            "styles": self.styles,
        }


class StoryTranslator:
    """
    Translates user stories into backend and frontend specifications.
    Takes a story from the STORIES phase and generates technical specifications
    that can be used by Backend and Frontend Generator agents.
    """

    def __init__(self, trd_content: Optional[str] = None):
        """
        Initialize the translator.

        Args:
            trd_content: Technical Requirements Document for context
        """
        self.trd_content = trd_content or ""

    def translate_story(
        self,
        story: Dict,
        context_docs: Optional[Dict[str, str]] = None
    ) -> Tuple[BackendSpec, FrontendSpec]:
        """
        Translate a single story into backend and frontend specifications.

        Args:
            story: Story dictionary with id, name, description, depends_on, success_criteria
            context_docs: Optional context documents (PRD, TRD) for additional context

        Returns:
            Tuple of (BackendSpec, FrontendSpec)
        """
        story_id = story.get("id", "unknown")
        story_name = story.get("name", "")
        description = story.get("description", "")
        success_criteria = story.get("success_criteria", [])

        # Extract backend and frontend requirements from description and criteria
        backend_spec = self._extract_backend_spec(
            story_id, story_name, description, success_criteria, context_docs
        )
        frontend_spec = self._extract_frontend_spec(
            story_id, story_name, description, success_criteria, context_docs
        )

        return backend_spec, frontend_spec

    def _needs_backend(
        self,
        description: str,
        success_criteria: List[str],
        context_docs: Dict[str, str]
    ) -> bool:
        """
        Determine if the product needs a backend server.
        Returns False for static/HTML-only products.
        """
        static_keywords = [
            "static", "html", "flyer", "promotional", "landing page",
            "one page", "one-page", "brochure", "informational",
            "display only", "no backend", "frontend only", "pure html",
            "single page html", "webpage", "presentation", "poster",
            "advertisement", "promo page", "marketing page",
        ]

        # Check PRD content for static product signals
        prd_content = context_docs.get("PRD", context_docs.get("prd", "")).lower()
        if prd_content and any(kw in prd_content for kw in static_keywords):
            return False

        # Check story description
        desc_lower = description.lower()
        if any(kw in desc_lower for kw in static_keywords):
            return False

        # Explicit backend signals in success criteria
        criteria_text = " ".join(success_criteria).lower() if isinstance(success_criteria, list) else str(success_criteria).lower()
        backend_signals = ["api", "database", "crud", "endpoint", "server",
                           "authenticate", "login", "register", "store data",
                           "save", "retrieve", "persist"]
        if any(kw in criteria_text for kw in backend_signals):
            return True

        # Check TRD for architecture decisions
        trd_content = context_docs.get("TRD", context_docs.get("trd", "")).lower()
        if trd_content:
            if any(kw in trd_content for kw in ["fastapi", "sqlalchemy", "api endpoint", "database schema"]):
                return True
            if any(kw in trd_content for kw in static_keywords):
                return False

        # If PRD exists but has no backend signals, lean toward static
        if prd_content:
            backend_prd_signals = ["user authentication", "data storage", "api", "crud", "database", "user account"]
            return any(kw in prd_content for kw in backend_prd_signals)

        # Default: needs backend when uncertain
        return True

    def _extract_entities_from_context(self, context_docs: Dict[str, str]) -> List[str]:
        """
        Extract entity/model names from TRD or PRD context documents.
        Parses for model definitions, table names, or resource classes.
        """
        entities = []
        trd_content = context_docs.get("TRD", context_docs.get("trd", ""))
        if not trd_content:
            return entities

        import re
        # Look for: "User model", "Task table", "Product entity", class names, etc.
        patterns = [
            r'\b([A-Z][a-z]+)\s+(?:model|table|entity|resource|schema)\b',
            r'(?:model|table|entity|resource|class)\s+([A-Z][a-z]+)\b',
            r'##\s*([A-Z][a-z]+)\s*(?:Model|Table|Entity)',
            r'`([A-Z][a-z]+)`\s+(?:model|table)',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, trd_content)
            for m in matches:
                if m not in entities and m not in {"The", "This", "Each", "When", "For"}:
                    entities.append(m)

        return entities[:5]  # Cap at 5 entities to prevent explosion

    def _extract_backend_spec(
        self,
        story_id: str,
        story_name: str,
        description: str,
        success_criteria: List[str],
        context_docs: Optional[Dict[str, str]] = None
    ) -> BackendSpec:
        """
        Extract backend specification from story.

        Strategy:
        1. Check if product needs a backend at all (static products skip this entirely)
        2. Use context docs (TRD/PRD) to identify actual entities and operations
        3. Fall back to story description parsing only when context is unavailable
        """
        context_docs = context_docs or {}

        # Early exit for static/HTML-only products
        if not self._needs_backend(description, success_criteria, context_docs):
            return BackendSpec(
                story_id=story_id,
                story_name=story_name,
                description=description,
                requires_backend=False,
            )

        spec = BackendSpec(
            story_id=story_id,
            story_name=story_name,
            description=description,
            requires_backend=True,
        )

        # Try to get entities from TRD context first, fall back to description parsing
        entities = self._extract_entities_from_context(context_docs)
        if not entities:
            entities = self._extract_entities(description)

        # Parse success criteria for CRUD operations
        crud_ops = self._parse_crud_operations(success_criteria)

        # Generate endpoints based on entities and operations
        for entity in entities:
            for op in crud_ops:
                endpoint = self._generate_endpoint(entity, op)
                spec.endpoints.append(endpoint)

        # Generate database models for each entity
        for entity in entities:
            model = self._generate_database_model(entity, description)
            spec.models.append(model)

        # Set standard dependencies
        spec.dependencies = [
            "fastapi>=0.100.0",
            "uvicorn>=0.23.0",
            "sqlalchemy>=2.0.0",
            "pydantic>=2.0.0",
            "pytest>=7.0.0",
            "httpx>=0.24.0",
        ]

        # Standard middleware
        spec.middleware = ["CORS", "error_handling", "request_logging"]

        return spec

    def _extract_frontend_spec(
        self,
        story_id: str,
        story_name: str,
        description: str,
        success_criteria: List[str],
        context_docs: Optional[Dict[str, str]] = None
    ) -> FrontendSpec:
        """
        Extract frontend specification from story.

        Strategy:
        1. For static/HTML-only products: return a single-page spec with no SPA complexity
        2. For dynamic apps: use context docs (PRD/TRD) to determine pages and components,
           parsing story description as a fallback only
        """
        context_docs = context_docs or {}
        spec = FrontendSpec(
            story_id=story_id,
            story_name=story_name,
            description=description,
        )

        # Static product: minimal single-page frontend, no SPA routing or auth
        if not self._needs_backend(description, success_criteria, context_docs):
            page = UIPage(
                name="index",
                route="/index.html",
                title=story_name,
                description=description,
                requires_auth=False,
            )
            spec.pages.append(page)
            spec.styles = {"responsive": "Mobile-first responsive design"}
            return spec

        # Dynamic app: extract entities from context docs first
        entities = self._extract_entities_from_context(context_docs)
        if not entities:
            entities = self._extract_entities(description)

        # Parse success criteria for user-facing operations
        ui_operations = self._parse_ui_operations(success_criteria)

        # Generate pages for each entity and operation
        for entity in entities:
            for op in ui_operations:
                page = self._generate_ui_page(entity, op, description)
                spec.pages.append(page)

        # Generate reusable components
        for entity in entities:
            form_component = self._generate_form_component(entity)
            table_component = self._generate_table_component(entity)
            spec.components.extend([form_component, table_component])

        # Extract API endpoints used
        entities_lower = [e.lower() for e in entities]
        spec.api_endpoints = [f"/{e}" for e in entities_lower]

        # State management needs
        spec.state_management = {
            "auth_token": "str",
            "current_user": "Optional[Dict]",
            "loading": "bool",
            "error": "Optional[str]",
        }

        # Standard CSS theme
        spec.styles = {
            "dark_mode": "CSS variables for dark theme",
            "light_mode": "CSS variables for light theme",
            "responsive": "Mobile-first responsive design",
        }

        return spec

    def _extract_entities(self, text: str) -> List[str]:
        """
        Extract likely entity/resource names from text.
        Simple heuristic: capitalized words (excluding common words).
        """
        common_words = {
            "User", "Task", "Project", "Item", "Post", "Comment",
            "Message", "Notification", "Account", "Profile",
        }
        # This is a simplified extraction; in production, use NLP
        words = text.split()
        entities = []
        for word in words:
            cleaned = word.replace(".", "").replace(",", "").replace("'", "")
            if cleaned and cleaned[0].isupper() and cleaned in common_words:
                if cleaned not in entities:
                    entities.append(cleaned)

        # Only use generic fallback when no context is available
        if not entities:
            entities = ["Item"]

        return entities

    def _parse_crud_operations(self, criteria: List[str]) -> List[str]:
        """
        Parse success criteria for CRUD operations.
        Returns list of operations: create, read, update, delete, list
        """
        operations = set()
        crud_keywords = {
            "create": ["create", "add", "new"],
            "read": ["view", "get", "retrieve", "fetch", "read"],
            "update": ["edit", "modify", "update", "change"],
            "delete": ["delete", "remove", "destroy"],
            "list": ["list", "all", "view all", "browse", "search"],
        }

        criteria_text = " ".join(criteria).lower()

        for operation, keywords in crud_keywords.items():
            if any(kw in criteria_text for kw in keywords):
                operations.add(operation)

        # Conservative default: read-only when no explicit CRUD signals found
        if not operations:
            operations = {"read", "list"}

        return sorted(list(operations))

    def _parse_ui_operations(self, criteria: List[str]) -> List[str]:
        """
        Parse success criteria for UI operations.
        Returns list of operations: list, detail, create, edit, delete, search
        """
        operations = set()
        ui_keywords = {
            "list": ["view all", "list", "browse", "display all"],
            "detail": ["view details", "detail", "individual"],
            "create": ["create new", "add new", "add"],
            "edit": ["edit", "modify", "update"],
            "delete": ["delete", "remove"],
            "search": ["search", "filter", "find"],
        }

        criteria_text = " ".join(criteria).lower()

        for operation, keywords in ui_keywords.items():
            if any(kw in criteria_text for kw in keywords):
                operations.add(operation)

        # Conservative default: view-only when no explicit UI signals found
        if not operations:
            operations = {"list", "detail"}

        return sorted(list(operations))

    def _generate_endpoint(self, entity: str, operation: str) -> APIEndpoint:
        """Generate an API endpoint specification from entity and operation."""
        entity_lower = entity.lower()
        entity_plural = entity_lower + "s"

        endpoint_specs = {
            "list": APIEndpoint(
                method=HTTPMethod.GET,
                path=f"/{entity_plural}",
                name=f"list_{entity_plural}",
                description=f"Get all {entity_plural}",
                response_body={"items": f"List[{entity}]", "total": "int"},
                required_params=["skip", "limit"],
            ),
            "create": APIEndpoint(
                method=HTTPMethod.POST,
                path=f"/{entity_plural}",
                name=f"create_{entity_lower}",
                description=f"Create a new {entity_lower}",
                request_body={f"{entity_lower}_data": entity},
                response_body={entity_lower: entity, "id": "int"},
            ),
            "read": APIEndpoint(
                method=HTTPMethod.GET,
                path=f"/{entity_plural}/{{id}}",
                name=f"get_{entity_lower}",
                description=f"Get a {entity_lower} by ID",
                response_body={entity_lower: entity},
                required_params=["id"],
            ),
            "update": APIEndpoint(
                method=HTTPMethod.PUT,
                path=f"/{entity_plural}/{{id}}",
                name=f"update_{entity_lower}",
                description=f"Update a {entity_lower}",
                request_body={f"{entity_lower}_data": entity},
                response_body={entity_lower: entity},
                required_params=["id"],
            ),
            "delete": APIEndpoint(
                method=HTTPMethod.DELETE,
                path=f"/{entity_plural}/{{id}}",
                name=f"delete_{entity_lower}",
                description=f"Delete a {entity_lower}",
                response_body={"deleted": "bool", "id": "int"},
                required_params=["id"],
            ),
        }

        return endpoint_specs.get(
            operation,
            APIEndpoint(
                method=HTTPMethod.GET,
                path=f"/{entity_lower}",
                name=f"{operation}_{entity_lower}",
                description=f"{operation.capitalize()} operation on {entity_lower}",
            ),
        )

    def _generate_database_model(self, entity: str, description: str) -> DatabaseModel:
        """Generate a database model specification."""
        entity_lower = entity.lower()
        return DatabaseModel(
            name=entity,
            plural=entity_lower + "s",
            description=f"Database model for {entity_lower}",
            fields={
                "id": "Integer (Primary Key)",
                "name": "String (max 255)",
                "description": "String",
                "created_at": "DateTime (auto)",
                "updated_at": "DateTime (auto)",
            },
            indexes=["id", "created_at"],
        )

    def _generate_ui_page(self, entity: str, operation: str, description: str) -> UIPage:
        """Generate a UI page specification."""
        entity_lower = entity.lower()
        entity_plural = entity_lower + "s"

        page_specs = {
            "list": UIPage(
                name=f"{entity_plural}_list",
                route=f"/{entity_plural}",
                title=f"{entity} List",
                description=f"Display all {entity_plural}",
                requires_auth=True,
            ),
            "detail": UIPage(
                name=f"{entity_lower}_detail",
                route=f"/{entity_plural}/:id",
                title=f"{entity} Details",
                description=f"Show details for a {entity_lower}",
                requires_auth=True,
            ),
            "create": UIPage(
                name=f"create_{entity_lower}",
                route=f"/{entity_plural}/new",
                title=f"Create {entity}",
                description=f"Form to create a new {entity_lower}",
                requires_auth=True,
            ),
            "edit": UIPage(
                name=f"edit_{entity_lower}",
                route=f"/{entity_plural}/:id/edit",
                title=f"Edit {entity}",
                description=f"Form to edit a {entity_lower}",
                requires_auth=True,
            ),
            "delete": UIPage(
                name=f"delete_{entity_lower}",
                route=f"/{entity_plural}/:id/delete",
                title=f"Delete {entity}",
                description=f"Confirm deletion of {entity_lower}",
                requires_auth=True,
            ),
            "search": UIPage(
                name=f"search_{entity_plural}",
                route=f"/{entity_plural}/search",
                title=f"Search {entity}",
                description=f"Search and filter {entity_plural}",
                requires_auth=True,
            ),
        }

        return page_specs.get(
            operation,
            UIPage(
                name=f"{entity_lower}_{operation}",
                route=f"/{entity_plural}/{operation}",
                title=f"{operation.capitalize()} {entity}",
                description=f"{operation.capitalize()} {entity_lower}",
                requires_auth=True,
            ),
        )

    def _generate_form_component(self, entity: str) -> UIComponent:
        """Generate a form component specification."""
        entity_lower = entity.lower()
        return UIComponent(
            name=f"{entity_lower}_form",
            type="form",
            description=f"Form for creating/editing {entity_lower}",
            inputs={
                "name": "text",
                "description": "textarea",
                "submit": "button",
            },
            outputs=["on_submit", "on_cancel"],
            api_calls=[f"create_{entity_lower}", f"update_{entity_lower}"],
        )

    def _generate_table_component(self, entity: str) -> UIComponent:
        """Generate a table component specification."""
        entity_lower = entity.lower()
        entity_plural = entity_lower + "s"
        return UIComponent(
            name=f"{entity_plural}_table",
            type="table",
            description=f"Table displaying {entity_plural}",
            inputs={"items": f"List[{entity}]", "page": "int"},
            outputs=["on_row_click", "on_delete", "on_edit"],
            api_calls=[f"list_{entity_plural}", f"delete_{entity_lower}"],
        )

    def translate_batch(
        self,
        stories: List[Dict],
        context_docs: Optional[Dict[str, str]] = None
    ) -> Tuple[List[BackendSpec], List[FrontendSpec]]:
        """
        Translate multiple stories into specifications.

        Args:
            stories: List of story dictionaries
            context_docs: Optional context documents

        Returns:
            Tuple of (backend_specs, frontend_specs)
        """
        backend_specs = []
        frontend_specs = []

        for story in stories:
            backend, frontend = self.translate_story(story, context_docs)
            backend_specs.append(backend)
            frontend_specs.append(frontend)

        return backend_specs, frontend_specs
