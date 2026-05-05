"""
Module 4: The LangGraph Runner
Top-level controller using LangGraph FSM to tie all modules together.
"""

import os
import asyncio
import json
import docker
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List, TypedDict
from pathlib import Path

# LangGraph imports
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.message import add_messages
from typing_extensions import Annotated, Sequence
import operator

# Import all previous modules
from state import ProjectState, Document, CritiqueEntry
from sandbox import ProjectSandbox
from orchestrator import BlindOrchestrator, Phase, OrchestratorConfig
from engineer import CodeEngineer, EngineerConfig
from product_generator import ProductGenerator, ProductGeneratorConfig


class SDLCState(TypedDict):
    """
    LangGraph state that wraps ProjectState.
    This is the shared state channel for the FSM.
    """
    # Core project state
    project_id: str
    rough_idea: str
    current_phase: str
    
    # Documents
    brd_content: str
    prd_content: str
    trd_content: str
    stories_content: str
    
    # Execution state
    stories: List[Dict]
    codebase: Dict[str, str]
    history: List[Dict]
    
    # Orchestration results
    brd_passed: bool
    prd_passed: bool
    trd_passed: bool
    stories_passed: bool
    
    # Engineering results
    engineering_completed: bool
    engineering_failed: bool
    engineering_retry_count: int
    
    # E2E results
    e2e_passed: bool
    e2e_feedback: str
    
    # Human approval
    human_approved: bool
    human_feedback: str
    
    # Errors
    error: Optional[str]
    needs_demotion: bool
    demotion_target: Optional[str]


class LangGraphRunner:
    """
    Main runner using LangGraph FSM to orchestrate the entire SDLC.
    """

    def __init__(self, state_dir: str = None, model_config: dict = None):
        """
        Initialize the LangGraph runner.

        Args:
            state_dir: Directory to save/load state (default: ./sdlc_state)
            model_config: Dictionary with 'provider' and 'model' keys
        """
        self.state_dir = state_dir or "./sdlc_state"
        self.graph = None
        self.checkpointer = MemorySaver()
        self.config = None

        # Store model configuration
        self.model_config = model_config or {
            'provider': 'OpenRouter',
            'model': 'meta-llama/llama-3.3-70b-instruct:free'
        }

        # Ensure state directory exists
        os.makedirs(self.state_dir, exist_ok=True)

    def _get_litellm_model(self) -> str:
        """
        Convert provider + model to LiteLLM format.
        LiteLLM infers the provider from the model prefix — it must be explicit.
        """
        provider = self.model_config.get('provider', 'OpenRouter')
        model = self.model_config.get('model', 'meta-llama/llama-3.3-70b-instruct:free')

        if provider == 'OpenRouter':
            # LiteLLM requires the openrouter/ prefix to route correctly
            if not model.startswith('openrouter/'):
                return f"openrouter/{model}"
            return model
        elif provider == 'Inception':
            # Inception is OpenAI-compatible — pass the raw model name (e.g. mercury-2)
            # and use api_base + api_key to route to Inception's endpoint
            return model
        elif provider == 'Local':
            # Ollama models use the ollama/ prefix
            if not model.startswith('ollama/'):
                return f"ollama/{model}"
            return model
        else:
            return model

    def _get_api_base(self) -> str:
        """Get the API base URL for the provider."""
        provider = self.model_config.get('provider', 'OpenRouter')

        if provider == 'Inception':
            # Inception Labs API endpoint
            return 'https://api.inceptionlabs.ai/v1'
        elif provider == 'Local':
            # Ollama endpoint
            return 'http://localhost:11434/v1'
        else:
            # OpenRouter doesn't need a custom api_base
            return None

    def _setup_provider_env(self) -> None:
        """
        Set environment variables for the selected provider.
        This ensures the correct API key is available to litellm.
        """
        provider = self.model_config.get('provider', 'OpenRouter')

        if provider == 'Inception':
            # Ensure INCEPTION_API_KEY is available
            if not os.getenv("INCEPTION_API_KEY"):
                print("⚠️  Warning: INCEPTION_API_KEY not set in environment")
        elif provider == 'OpenRouter':
            # Ensure OPENROUTER_API_KEY is available
            if not os.getenv("OPENROUTER_API_KEY"):
                print("⚠️  Warning: OPENROUTER_API_KEY not set in environment")
        elif provider == 'Local':
            # Local models via Ollama don't need API keys
            pass

    def _get_state_file(self, project_id: str) -> str:
        """Get the state file path for a project."""
        return os.path.join(self.state_dir, f"{project_id}.json")

    def _load_state(self, project_id: str) -> Optional[ProjectState]:
        """Load project state from disk."""
        state_file = self._get_state_file(project_id)
        if os.path.exists(state_file):
            with open(state_file, 'r') as f:
                json_str = f.read()
            return ProjectState.from_json(json_str)
        return None

    def _save_state(self, project_id: str, state) -> None:
        """Save project state to disk."""
        state_file = self._get_state_file(project_id)
        with open(state_file, 'w') as f:
            if isinstance(state, dict):
                json.dump(state, f)
            else:
                f.write(state.to_json())

    def _initialize_graph(self) -> None:
        """Initialize the LangGraph state machine."""
        # Create the graph with our custom state
        workflow = StateGraph(SDLCState)

        # Add nodes
        workflow.add_node("generate_brd", self.generate_brd_node)
        workflow.add_node("generate_prd", self.generate_prd_node)
        workflow.add_node("generate_trd", self.generate_trd_node)
        workflow.add_node("generate_stories", self.generate_stories_node)
        workflow.add_node("human_approval", self.human_approval_node)
        workflow.add_node("engineering_execution", self.engineering_execution_node)
        workflow.add_node("e2e_testing", self.e2e_testing_node)

        # Add entry and exit edges
        workflow.add_edge(START, "generate_brd")
        workflow.add_edge("human_approval", "engineering_execution")
        workflow.add_edge("e2e_testing", END)

        # Add conditional edges for all phases (allows back-propagation on failure)
        self._add_conditional_edges(workflow)

        # Compile the graph
        self.graph = workflow.compile(checkpointer=self.checkpointer)

    def _add_conditional_edges(self, workflow: StateGraph) -> None:
        """Add conditional edges for back-propagation."""
        # Conditional edge from BRD
        workflow.add_conditional_edges(
            "generate_brd",
            self._check_brd_result,
            {
                "continue": "generate_prd",
                "demote_to_idea": "generate_brd",  # Stay and regenerate
            }
        )

        # Conditional edge from PRD
        workflow.add_conditional_edges(
            "generate_prd",
            self._check_prd_result,
            {
                "continue": "generate_trd",
                "demote_to_brd": "generate_brd",
            }
        )

        # Conditional edge from TRD
        workflow.add_conditional_edges(
            "generate_trd",
            self._check_trd_result,
            {
                "continue": "generate_stories",
                "demote_to_prd": "generate_prd",
            }
        )

        # Conditional edge from Stories
        workflow.add_conditional_edges(
            "generate_stories",
            self._check_stories_result,
            {
                "continue": "human_approval",
                "demote_to_trd": "generate_trd",
            }
        )

        # Conditional edge from Engineering
        workflow.add_conditional_edges(
            "engineering_execution",
            self._check_engineering_result,
            {
                "continue": "e2e_testing",
                "retry_engineering": "engineering_execution",
                "demote_to_stories": "generate_stories",
            }
        )

        # Conditional edge from E2E
        workflow.add_conditional_edges(
            "e2e_testing",
            self._check_e2e_result,
            {
                "continue": END,
                "demote_to_execution": "engineering_execution",
            }
        )

    def generate_brd_node(self, state: SDLCState) -> SDLCState:
        """
        Node: Generate BRD (Business Requirements Document).
        """
        print("\n" + "=" * 60)
        print("NODE: Generate BRD")
        print("=" * 60)

        try:
            # Initialize orchestrator
            api_base = self._get_api_base()
            config = OrchestratorConfig(
                llm_model=self._get_litellm_model(),
                api_base=api_base,
                max_retries=3
            )
            orchestrator = BlindOrchestrator(config=config)

            # Create and set project state
            project_state = ProjectState(
                project_id=state["project_id"],
                rough_idea=state["rough_idea"],
                current_phase="IDEA"
            )
            orchestrator.set_state(project_state)

            # Run BRD generation
            success, document = orchestrator.orchestrate_phase(Phase.BRD)

            # Update state
            state["brd_content"] = document.content
            state["brd_passed"] = success
            state["current_phase"] = "DESIGN" if success else "IDEA"

            # Log to history
            state["history"].append({
                "phase": "BRD",
                "action": "generated",
                "success": success,
                "timestamp": datetime.now().isoformat()
            })

            print(f"BRD generated: {success}")
            print(f"Content length: {len(document.content)} chars")

        except Exception as e:
            print(f"Error in BRD generation: {e}")
            state["error"] = str(e)
            state["brd_passed"] = False

        return state

    def generate_prd_node(self, state: SDLCState) -> SDLCState:
        """
        Node: Generate PRD (Product Requirements Document).
        """
        print("\n" + "=" * 60)
        print("NODE: Generate PRD")
        print("=" * 60)

        try:
            # Initialize orchestrator
            api_base = self._get_api_base()
            config = OrchestratorConfig(
                llm_model=self._get_litellm_model(),
                api_base=api_base,
                max_retries=3
            )
            orchestrator = BlindOrchestrator(config=config)

            # Create project state for orchestrator
            project_state = ProjectState(
                project_id=state["project_id"],
                rough_idea=state["rough_idea"],
                current_phase="DESIGN",
                docs={"BRD": Document(
                    content=state["brd_content"],
                    version=1,
                    status="approved"
                )}
            )
            orchestrator.set_state(project_state)

            # Run PRD generation
            success, document = orchestrator.orchestrate_phase(Phase.PRD)

            # Update state
            state["prd_content"] = document.content
            state["prd_passed"] = success
            state["current_phase"] = "IMPLEMENTATION" if success else "DESIGN"

            print(f"PRD generated: {success}")
            print(f"Content length: {len(document.content)} chars")

        except Exception as e:
            print(f"Error in PRD generation: {e}")
            state["error"] = str(e)
            state["prd_passed"] = False

        return state

    def generate_trd_node(self, state: SDLCState) -> SDLCState:
        """
        Node: Generate TRD (Technical Requirements Document).
        """
        print("\n" + "=" * 60)
        print("NODE: Generate TRD")
        print("=" * 60)

        try:
            # Initialize orchestrator
            api_base = self._get_api_base()
            config = OrchestratorConfig(
                llm_model=self._get_litellm_model(),
                api_base=api_base,
                max_retries=3
            )
            orchestrator = BlindOrchestrator(config=config)

            # Create project state for orchestrator
            project_state = ProjectState(
                project_id=state["project_id"],
                rough_idea=state["rough_idea"],
                current_phase="IMPLEMENTATION",
                docs={
                    "BRD": Document(
                        content=state["brd_content"],
                        version=1,
                        status="approved"
                    ),
                    "PRD": Document(
                        content=state["prd_content"],
                        version=1,
                        status="approved"
                    )
                }
            )
            orchestrator.set_state(project_state)

            # Run TRD generation
            success, document = orchestrator.orchestrate_phase(Phase.TRD)

            # Update state
            state["trd_content"] = document.content
            state["trd_passed"] = success
            state["current_phase"] = "TESTING" if success else "IMPLEMENTATION"

            print(f"TRD generated: {success}")
            print(f"Content length: {len(document.content)} chars")

        except Exception as e:
            print(f"Error in TRD generation: {e}")
            state["error"] = str(e)
            state["trd_passed"] = False

        return state

    def generate_stories_node(self, state: SDLCState) -> SDLCState:
        """
        Node: Generate User Stories.
        """
        print("\n" + "=" * 60)
        print("NODE: Generate User Stories")
        print("=" * 60)

        try:
            # Initialize orchestrator
            api_base = self._get_api_base()
            config = OrchestratorConfig(
                llm_model=self._get_litellm_model(),
                api_base=api_base,
                max_retries=3
            )
            orchestrator = BlindOrchestrator(config=config)

            # Create project state for orchestrator
            project_state = ProjectState(
                project_id=state["project_id"],
                rough_idea=state["rough_idea"],
                current_phase="TESTING",
                docs={
                    "BRD": Document(
                        content=state["brd_content"],
                        version=1,
                        status="approved"
                    ),
                    "PRD": Document(
                        content=state["prd_content"],
                        version=1,
                        status="approved"
                    ),
                    "TRD": Document(
                        content=state["trd_content"],
                        version=1,
                        status="approved"
                    )
                }
            )
            orchestrator.set_state(project_state)

            # Run stories generation
            success, document = orchestrator.orchestrate_phase(Phase.STORIES)

            # Parse stories from document content
            stories = []
            if document.content:
                try:
                    # Try to parse as JSON first
                    stories = json.loads(document.content)
                except json.JSONDecodeError:
                    # If not JSON, store as text
                    stories = [{"raw_content": document.content}]

            # Update state
            state["stories"] = stories
            state["stories_content"] = document.content
            state["stories_passed"] = success
            state["current_phase"] = "DEPLOYMENT" if success else "TESTING"

            print(f"Stories generated: {success}")
            print(f"Number of stories: {len(stories)}")

        except Exception as e:
            print(f"Error in stories generation: {e}")
            state["error"] = str(e)
            state["stories_passed"] = False

        return state

    def human_approval_node(self, state: SDLCState) -> SDLCState:
        """
        Node: Human-in-the-loop approval pause.
        Waits for user input before proceeding to engineering.
        """
        print("\n" + "=" * 60)
        print("NODE: Human Approval (HITL Pause)")
        print("=" * 60)

        print("\n📋 PROJECT SUMMARY")
        print("-" * 40)
        print(f"Project ID: {state['project_id']}")
        print(f"Rough Idea: {state['rough_idea']}")
        print(f"\nBRD: {'✓' if state.get('brd_passed') else '✗'} ({len(state.get('brd_content', ''))} chars)")
        print(f"PRD: {'✓' if state.get('prd_passed') else '✗'} ({len(state.get('prd_content', ''))} chars)")
        print(f"TRD: {'✓' if state.get('trd_passed') else '✗'} ({len(state.get('trd_content', ''))} chars)")
        print(f"Stories: {'✓' if state.get('stories_passed') else '✗'} ({len(state.get('stories', []))} stories)")
        print("-" * 40)

        while True:
            print("\n👤 Human Approval Required")
            print("Type 'approve' to proceed to engineering")
            print("Type 'reject' to go back and improve")
            print("Type 'details' to see document content")
            print("Type 'quit' to exit")
            print()

            user_input = input("> ").strip().lower()

            if user_input == "approve":
                print("✅ Human approval granted. Proceeding to engineering...")
                state["human_approved"] = True
                state["human_feedback"] = "Approved by human"
                break
            elif user_input == "reject":
                print("❌ Human rejected. Returning to stories for improvement.")
                state["human_approved"] = False
                state["human_feedback"] = "Rejected by human"
                # Return to stories
                return {"needs_demotion": True, "demotion_target": "generate_stories"}
            elif user_input == "details":
                print("\n--- BRD Preview ---")
                print(state.get("brd_content", "")[:500])
                print("\n--- PRD Preview ---")
                print(state.get("prd_content", "")[:500])
                print("\n--- TRD Preview ---")
                print(state.get("trd_content", "")[:500])
                print("\n--- Stories Preview ---")
                print(state.get("stories_content", "")[:500])
            elif user_input == "quit":
                print("🚫 User cancelled. Exiting.")
                state["human_approved"] = False
                state["error"] = "User cancelled"
                return {"needs_demotion": True, "demotion_target": "generate_brd"}
            else:
                print("Invalid input. Please type 'approve', 'reject', 'details', or 'quit'.")

        return state

    def engineering_execution_node(self, state: SDLCState) -> SDLCState:
        """
        Node: Execute engineering with product generation.
        Generates complete product from stories with backend + frontend.
        """
        print("\n" + "=" * 60)
        print("NODE: Product Generation & Engineering")
        print("=" * 60)

        # Track node-visit count for retry limit
        state["engineering_retry_count"] = state.get("engineering_retry_count", 0) + 1
        print(f"Engineering attempt {state['engineering_retry_count']}/3")

        sandbox = None
        try:
            # Initialize sandbox (or reuse if this is a retry)
            if "sandbox_workspace" not in state or state["sandbox_workspace"] is None:
                sandbox = ProjectSandbox(project_id=f"exec-{state['project_id']}")
                sandbox.initialize()
                state["sandbox_workspace"] = sandbox.workspace_dir
            else:
                sandbox = ProjectSandbox(project_id=f"exec-{state['project_id']}")
                sandbox.workspace_dir = state["sandbox_workspace"]
                sandbox.client = docker.from_env()
                sandbox._initialized = True

            # Initialize product generator
            config = ProductGeneratorConfig(
                llm_model="gpt-4o",
                max_retries=3,
                run_tests=True,
                worker_pool_size=2
            )

            # Create project state for product generator
            project_state = ProjectState(
                project_id=state["project_id"],
                rough_idea=state["rough_idea"],
                stories=state.get("stories", [])
            )

            # Context documents for specifications
            context_docs = {
                "PRD": state.get("prd_content", ""),
                "TRD": state.get("trd_content", ""),
            }

            # Generate complete product
            generator = ProductGenerator(
                config=config,
                state=project_state,
                sandbox=sandbox,
                product_dir="./products"
            )

            # Run product generation
            product_path = asyncio.run(
                generator.generate_product(
                    project_id=state["project_id"],
                    stories=state.get("stories", []),
                    context_docs=context_docs
                )
            )

            # Update state with product path and results
            state["engineering_completed"] = True
            state["product_path"] = product_path
            state["engineering_failed"] = False

            print(f"\nProduct Generation Results:")
            print(f"  Product Path: {product_path}")
            print(f"  Completed: {state['engineering_completed']}")
            print(f"  Status: {'SUCCESS' if not state['engineering_failed'] else 'FAILED'}")

            # Log to history
            state["history"].append({
                "phase": "ENGINEERING",
                "action": "generated_product",
                "success": True,
                "product_path": product_path,
                "timestamp": datetime.now().isoformat()
            })

        except Exception as e:
            print(f"Error in product generation: {e}")
            state["engineering_completed"] = False
            state["engineering_failed"] = True
            state["error"] = str(e)

            state["history"].append({
                "phase": "ENGINEERING",
                "action": "product_generation_failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
        finally:
            # Cleanup sandbox only on final failure (not on retries)
            if sandbox and state.get("engineering_retry_count", 1) >= 3:
                sandbox.cleanup()

        return state

    def e2e_testing_node(self, state: SDLCState) -> SDLCState:
        """
        Node: Run End-to-End tests.
        """
        print("\n" + "=" * 60)
        print("NODE: E2E Testing")
        print("=" * 60)

        try:
            # Reuse sandbox from engineering node
            if not state.get("sandbox_workspace"):
                print("⚠ No sandbox workspace found. Skipping E2E tests.")
                state["e2e_passed"] = False
                state["e2e_feedback"] = "No sandbox workspace available from engineering phase"
                return state

            sandbox = ProjectSandbox(project_id=f"e2e-{state['project_id']}")
            sandbox.workspace_dir = state["sandbox_workspace"]
            sandbox.client = docker.from_env()
            sandbox._initialized = True

            # Initialize engineer for E2E
            config = EngineerConfig(llm_model=self._get_litellm_model())

            # Create project state for engineer
            project_state = ProjectState(
                project_id=state["project_id"],
                rough_idea=state["rough_idea"],
                docs={
                    "PRD": Document(
                        content=state.get("prd_content", ""),
                        version=1,
                        status="approved"
                    )
                }
            )

            engineer = CodeEngineer(
                config=config,
                state=project_state,
                sandbox=sandbox
            )

            # Run E2E tests
            passed, feedback = asyncio.run(engineer.run_e2e_tests())

            # Update state
            state["e2e_passed"] = passed
            state["e2e_feedback"] = feedback

            print(f"\nE2E Testing Results:")
            print(f"  Passed: {passed}")
            print(f"  Feedback: {feedback}")

        except Exception as e:
            print(f"Error in E2E testing: {e}")
            state["e2e_passed"] = False
            state["e2e_feedback"] = str(e)

        return state

    def _check_brd_result(self, state: SDLCState) -> str:
        """Check BRD result and route accordingly."""
        if state.get("brd_passed"):
            return "continue"
        else:
            return "demote_to_idea"

    def _check_prd_result(self, state: SDLCState) -> str:
        """Check PRD result and route accordingly."""
        if state.get("prd_passed"):
            return "continue"
        else:
            return "demote_to_brd"

    def _check_trd_result(self, state: SDLCState) -> str:
        """Check TRD result and route accordingly."""
        if state.get("trd_passed"):
            return "continue"
        else:
            return "demote_to_prd"

    def _check_stories_result(self, state: SDLCState) -> str:
        """Check stories result and route accordingly."""
        if state.get("stories_passed"):
            return "continue"
        else:
            return "demote_to_trd"

    def _check_engineering_result(self, state: SDLCState) -> str:
        """Check engineering result and route accordingly."""
        if state.get("engineering_failed"):
            retry_count = state.get("engineering_retry_count", 0)
            if retry_count < 3:
                return "retry_engineering"
            else:
                print(f"Engineering failed after {retry_count} attempts. Demoting to stories.")
                return "demote_to_stories"
        else:
            return "continue"

    def _check_e2e_result(self, state: SDLCState) -> str:
        """Check E2E result and route accordingly."""
        if state.get("e2e_passed"):
            return "continue"
        else:
            return "demote_to_execution"

    def resume_or_start(self, project_id: str = None) -> Dict[str, Any]:
        """
        Resume or start LangGraph execution.

        Args:
            project_id: Project ID to resume, or None for fresh start

        Returns:
            Final state after execution completes
        """
        # Initialize graph if not already done
        if self.graph is None:
            self._initialize_graph()

        if project_id:
            # Resume existing project
            print(f"\n🔄 Resuming project: {project_id}")
            project_state = self._load_state(project_id)

            if not project_state:
                print(f"⚠ No existing state found for {project_id}. Starting fresh.")
                project_state = ProjectState(
                    project_id=project_id,
                    rough_idea="New project"
                )

            rough_idea = project_state.rough_idea
            current_phase = project_state.current_phase

        else:
            # Create new project
            print("\n🆕 Creating new project")
            rough_idea = input("Enter project idea: ").strip()
            project_id = f"proj_{uuid.uuid4().hex[:8]}"

        # Initialize state
        initial_state: SDLCState = {
            "project_id": project_id,
            "rough_idea": rough_idea,
            "current_phase": "IDEA",
            "brd_content": "",
            "prd_content": "",
            "trd_content": "",
            "stories_content": "",
            "stories": [],
            "codebase": {},
            "history": [],
            "brd_passed": False,
            "prd_passed": False,
            "trd_passed": False,
            "stories_passed": False,
            "engineering_completed": False,
            "engineering_failed": False,
            "engineering_retry_count": 0,
            "e2e_passed": False,
            "e2e_feedback": "",
            "human_approved": False,
            "human_feedback": "",
            "error": None,
            "needs_demotion": False,
            "demotion_target": None
        }

        # Create config with thread ID for checkpointing and higher recursion limit
        self.config = {
            "configurable": {
                "thread_id": project_id
            },
            "recursion_limit": 50  # Increased from default 25 to handle retries
        }

        # Run the graph
        print("\n" + "=" * 60)
        print("Starting LangGraph SDLC Execution")
        print("=" * 60)

        try:
            # Stream the execution
            for event in self.graph.stream(initial_state, self.config):
                for node_name, node_state in event.items():
                    print(f"\n🔄 Executing node: {node_name}")

            # Get final state
            final_state = self.graph.get_state(self.config)

            # Save final state
            self._save_state(project_id, final_state.to_dict())

            print("\n" + "=" * 60)
            print("✅ Execution Complete!")
            print("=" * 60)
            print(f"Project ID: {project_id}")
            print(f"Final Phase: {final_state.values.get('current_phase', 'UNKNOWN')}")
            print(f"BRD: {'✓' if final_state.values.get('brd_passed') else '✗'}")
            print(f"PRD: {'✓' if final_state.values.get('prd_passed') else '✗'}")
            print(f"TRD: {'✓' if final_state.values.get('trd_passed') else '✗'}")
            print(f"Stories: {'✓' if final_state.values.get('stories_passed') else '✗'}")
            print(f"Engineering: {'✓' if final_state.values.get('engineering_completed') and not final_state.values.get('engineering_failed') else '✗'}")
            print(f"E2E: {'✓' if final_state.values.get('e2e_passed') else '✗'}")

            return final_state.to_dict()

        except Exception as e:
            print(f"\n❌ Execution failed: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}


def main():
    """Main entry point."""
    import sys

    runner = LangGraphRunner()

    if len(sys.argv) > 1:
        # Resume existing project
        project_id = sys.argv[1]
        runner.resume_or_start(project_id)
    else:
        # Start new project
        runner.resume_or_start()


if __name__ == "__main__":
    main()
