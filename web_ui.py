"""
Web UI for VibeFactory Product Generator
Simple FastAPI server with HTML/JS frontend for interactive product generation.
"""

import asyncio
import json
import os
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()  # Load OPENROUTER_API_KEY (and others) from .env

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from pydantic import BaseModel
import uvicorn

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('vibefactory.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

from state import ProjectState, Document
from orchestrator import BlindOrchestrator, OrchestratorConfig, Phase
from product_generator import ProductGenerator, ProductGeneratorConfig


class GenerationRequest(BaseModel):
    """Request to generate a product."""
    project_id: Optional[str] = None  # User-provided project ID (optional, will generate if not provided)
    rough_idea: str
    skip_documents: bool = False  # Skip BRD/PRD/TRD if True


class GenerationProgress(BaseModel):
    """Progress update during generation."""
    step: str
    status: str  # "started", "in_progress", "completed", "failed"
    progress: int  # 0-100
    message: str
    error: Optional[str] = None


# Create FastAPI app
app = FastAPI(title="VibeFactory UI", version="1.0")

# Store generation status
generation_status = {}
progress_queues = {}  # {project_id: asyncio.Queue of progress updates}


# Define generation stages
GENERATION_STAGES = [
    ("Initializing", 5),
    ("Translating Story to Specs", 15),
    ("Generating Backend Code", 40),
    ("Generating Frontend Code", 70),
    ("Assembling Product", 85),
    ("Finalizing", 95),
    ("Complete", 100),
]


@app.get("/api/progress/{project_id}")
async def stream_progress(project_id: str):
    """Stream progress updates for a generation as Server-Sent Events."""
    async def progress_generator():
        # Create a new queue for this project if it doesn't exist
        if project_id not in progress_queues:
            progress_queues[project_id] = asyncio.Queue()

        queue = progress_queues[project_id]

        try:
            while True:
                # Wait for progress update with timeout
                try:
                    update = await asyncio.wait_for(queue.get(), timeout=120)
                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    yield "data: {\"heartbeat\": true}\n\n"
                    continue

                # Send the progress update as SSE
                yield f"data: {json.dumps(update)}\n\n"

                # Stop streaming if generation is complete
                if update.get("status") in ["completed", "failed"]:
                    break
        except Exception as e:
            logger.error(f"Error streaming progress: {e}")

    return StreamingResponse(
        progress_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )


@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    """Serve the main UI."""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>VibeFactory - Product Generator</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }

            .container {
                background: white;
                border-radius: 16px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                max-width: 800px;
                width: 100%;
                padding: 40px;
            }

            .header {
                text-align: center;
                margin-bottom: 40px;
            }

            .header h1 {
                font-size: 32px;
                color: #333;
                margin-bottom: 10px;
            }

            .header p {
                color: #666;
                font-size: 16px;
            }

            .form-group {
                margin-bottom: 24px;
            }

            label {
                display: block;
                font-weight: 600;
                color: #333;
                margin-bottom: 8px;
                font-size: 14px;
            }

            input[type="text"],
            textarea {
                width: 100%;
                padding: 12px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                font-size: 14px;
                font-family: inherit;
                transition: border-color 0.3s;
            }

            input[type="text"]:focus,
            textarea:focus {
                outline: none;
                border-color: #667eea;
            }

            textarea {
                resize: vertical;
                min-height: 150px;
                font-family: inherit;
            }

            .button-group {
                display: flex;
                gap: 12px;
                margin-top: 32px;
            }

            button {
                flex: 1;
                padding: 12px 24px;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s;
            }

            .btn-generate {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }

            .btn-generate:hover:not(:disabled) {
                transform: translateY(-2px);
                box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
            }

            .btn-generate:disabled {
                opacity: 0.6;
                cursor: not-allowed;
            }

            .btn-secondary {
                background: #f0f0f0;
                color: #333;
            }

            .btn-secondary:hover {
                background: #e0e0e0;
            }

            .status-section {
                margin-top: 32px;
                padding-top: 32px;
                border-top: 2px solid #f0f0f0;
                display: none;
            }

            .status-section.active {
                display: block;
            }

            .status-header {
                font-size: 18px;
                font-weight: 600;
                color: #333;
                margin-bottom: 16px;
            }

            .progress-bar {
                width: 100%;
                height: 8px;
                background: #e0e0e0;
                border-radius: 4px;
                overflow: hidden;
                margin-bottom: 16px;
            }

            .progress-fill {
                height: 100%;
                background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
                width: 0%;
                transition: width 0.3s;
            }

            .stages-container {
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                margin-bottom: 24px;
                position: relative;
            }

            .stages-container::before {
                content: '';
                position: absolute;
                top: 20px;
                left: 0;
                right: 0;
                height: 2px;
                background: #e0e0e0;
                z-index: 0;
            }

            .stage {
                display: flex;
                flex-direction: column;
                align-items: center;
                position: relative;
                z-index: 1;
                flex: 1;
            }

            .stage-dot {
                width: 40px;
                height: 40px;
                border-radius: 50%;
                background: white;
                border: 3px solid #e0e0e0;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: 600;
                font-size: 14px;
                color: #999;
                margin-bottom: 8px;
                transition: all 0.3s;
            }

            .stage.active .stage-dot {
                background: #667eea;
                border-color: #667eea;
                color: white;
                transform: scale(1.1);
                box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
            }

            .stage.completed .stage-dot {
                background: #4caf50;
                border-color: #4caf50;
                color: white;
            }

            .stage-label {
                font-size: 12px;
                color: #999;
                text-align: center;
                font-weight: 500;
                transition: color 0.3s;
            }

            .stage.active .stage-label {
                color: #667eea;
                font-weight: 600;
            }

            .stage.completed .stage-label {
                color: #4caf50;
            }

            .status-message {
                padding: 12px;
                background: #f9f9f9;
                border-left: 4px solid #667eea;
                border-radius: 4px;
                margin-bottom: 12px;
                color: #333;
                font-size: 14px;
            }

            .status-message.error {
                background: #fff3cd;
                border-left-color: #f44336;
                color: #856404;
            }

            .status-message.success {
                background: #d4edda;
                border-left-color: #4caf50;
                color: #155724;
            }

            .result-section {
                margin-top: 24px;
                padding: 20px;
                background: #f0f8ff;
                border-radius: 8px;
                display: none;
            }

            .result-section.active {
                display: block;
            }

            .result-section h3 {
                color: #333;
                margin-bottom: 12px;
            }

            .result-path {
                background: white;
                padding: 12px;
                border-radius: 4px;
                font-family: monospace;
                font-size: 13px;
                color: #667eea;
                word-break: break-all;
                margin-bottom: 16px;
            }

            .result-links {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 12px;
            }

            .result-links a {
                display: block;
                padding: 12px;
                background: white;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                text-decoration: none;
                color: #667eea;
                font-weight: 600;
                text-align: center;
                transition: all 0.3s;
            }

            .result-links a:hover {
                border-color: #667eea;
                background: #f9f9f9;
            }

            .checkbox-group {
                display: flex;
                align-items: center;
                gap: 8px;
            }

            .checkbox-group input[type="checkbox"] {
                width: 18px;
                height: 18px;
                cursor: pointer;
            }

            .checkbox-group label {
                margin: 0;
                cursor: pointer;
                font-weight: 400;
            }

            .examples {
                background: #f9f9f9;
                padding: 16px;
                border-radius: 8px;
                margin-bottom: 24px;
                border-left: 4px solid #667eea;
            }

            .examples h4 {
                color: #333;
                margin-bottom: 12px;
                font-size: 14px;
            }

            .examples p {
                color: #666;
                font-size: 13px;
                margin-bottom: 8px;
                cursor: pointer;
                padding: 6px;
                border-radius: 4px;
                transition: background 0.2s;
            }

            .examples p:hover {
                background: #e0e0e0;
            }

            @media (max-width: 600px) {
                .container {
                    padding: 24px;
                }

                .header h1 {
                    font-size: 24px;
                }

                .button-group {
                    flex-direction: column;
                }

                .result-links {
                    grid-template-columns: 1fr;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 VibeFactory</h1>
                <p>Transform your ideas into complete, deployable products</p>
            </div>

            <form id="generationForm">
                <div class="form-group">
                    <label for="projectId">Project ID</label>
                    <input
                        type="text"
                        id="projectId"
                        name="projectId"
                        placeholder="Enter a unique project ID (e.g., my_todo_app)"
                        required
                    >
                </div>

                <div class="form-group">
                    <label for="roughIdea">Your Idea</label>
                    <textarea
                        id="roughIdea"
                        name="roughIdea"
                        placeholder="Describe what you want to build..."
                        required
                    ></textarea>

                    <div class="examples">
                        <h4>💡 Example ideas:</h4>
                        <p onclick="fillExample('A simple task management system where users can create, update, and delete tasks.')">📋 Task management system</p>
                        <p onclick="fillExample('A blog platform with post creation, commenting, and user authentication.')">📝 Blog platform</p>
                        <p onclick="fillExample('An expense tracking app with categories, reports, and budget alerts.')">💰 Expense tracker</p>
                        <p onclick="fillExample('A customer relationship management (CRM) system for tracking contacts and interactions.')">👥 CRM system</p>
                    </div>
                </div>

                <div class="form-group checkbox-group">
                    <input
                        type="checkbox"
                        id="skipDocs"
                        name="skipDocs"
                        checked
                        disabled
                    >
                    <label for="skipDocs" style="opacity: 0.6;">Skip document generation (BRD/PRD/TRD) and go directly to product <em>(enabled by default)</em></label>
                </div>

                <div class="button-group">
                    <button type="submit" class="btn-generate" id="generateBtn">
                        Generate Product
                    </button>
                    <button type="reset" class="btn-secondary">
                        Clear
                    </button>
                </div>
            </form>

            <div class="status-section" id="statusSection">
                <div class="status-header">Generation Progress</div>

                <!-- Stage indicators -->
                <div class="stages-container">
                    <div class="stage" data-progress="5">
                        <div class="stage-dot">1</div>
                        <div class="stage-label">Initializing</div>
                    </div>
                    <div class="stage" data-progress="40">
                        <div class="stage-dot">2</div>
                        <div class="stage-label">Backend</div>
                    </div>
                    <div class="stage" data-progress="70">
                        <div class="stage-dot">3</div>
                        <div class="stage-label">Frontend</div>
                    </div>
                    <div class="stage" data-progress="85">
                        <div class="stage-dot">4</div>
                        <div class="stage-label">Assembly</div>
                    </div>
                    <div class="stage" data-progress="100">
                        <div class="stage-dot">✓</div>
                        <div class="stage-label">Complete</div>
                    </div>
                </div>

                <!-- Progress bar -->
                <div class="progress-bar">
                    <div class="progress-fill" id="progressFill"></div>
                </div>

                <!-- Status messages -->
                <div id="statusMessages"></div>
            </div>

            <div class="result-section" id="resultSection">
                <h3>✅ Product Generated Successfully!</h3>
                <div class="result-path" id="resultPath"></div>
                <div class="result-links">
                    <a href="#" id="localLink" target="_blank">🌐 Open Frontend</a>
                    <a href="#" id="docsLink" target="_blank">📁 View Files</a>
                </div>
            </div>
        </div>

        <script>
            const projectIdInput = document.getElementById('projectId');
            const form = document.getElementById('generationForm');
            const generateBtn = document.getElementById('generateBtn');
            const statusSection = document.getElementById('statusSection');
            const statusMessages = document.getElementById('statusMessages');
            const resultSection = document.getElementById('resultSection');
            const progressFill = document.getElementById('progressFill');
            const resultPath = document.getElementById('resultPath');

            function fillExample(text) {
                document.getElementById('roughIdea').value = text;
            }

            form.addEventListener('submit', async (e) => {
                e.preventDefault();

                const projectId = document.getElementById('projectId').value;
                const roughIdea = document.getElementById('roughIdea').value;
                const skipDocs = document.getElementById('skipDocs').checked;

                if (!projectId || !roughIdea) {
                    alert('Please fill in all fields');
                    return;
                }

                generateBtn.disabled = true;
                statusSection.classList.add('active');
                resultSection.classList.remove('active');
                statusMessages.innerHTML = '';
                progressFill.style.width = '0%';

                // Start listening for progress updates via SSE
                const eventSource = new EventSource(`/api/progress/${projectId}`);

                let generationComplete = false;

                eventSource.onmessage = (event) => {
                    try {
                        const data = JSON.parse(event.data);

                        // Ignore heartbeat messages
                        if (data.heartbeat) return;

                        // Update progress bar
                        progressFill.style.width = `${data.progress}%`;

                        // Update stage indicators
                        updateStages(data.progress);

                        // Add status message
                        addStatusMessage(`🔄 ${data.step}: ${data.message}`, 'info');

                        // Check if generation is complete
                        if (data.status === 'completed') {
                            generationComplete = true;
                            eventSource.close();
                            addStatusMessage('✅ Product generated successfully!', 'success');
                        } else if (data.status === 'failed') {
                            generationComplete = true;
                            eventSource.close();
                            addStatusMessage(`❌ Generation failed: ${data.message}`, 'error');
                        }
                    } catch (e) {
                        console.error('Error parsing progress:', e);
                    }
                };

                eventSource.onerror = (error) => {
                    console.error('SSE error:', error);
                    eventSource.close();
                    if (!generationComplete) {
                        addStatusMessage('⚠️ Connection lost. Checking status...', 'error');
                    }
                };

                try {
                    const response = await fetch('/api/generate', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            project_id: projectId,
                            rough_idea: roughIdea,
                            skip_documents: skipDocs
                        })
                    });

                    if (!response.ok) {
                        throw new Error(`Generation failed: ${response.statusText}`);
                    }

                    const data = await response.json();

                    // Show result
                    resultPath.textContent = data.product_path;
                    // Open the generated frontend index.html
                    const indexPath = `${data.product_path}/frontend/index.html`;
                    document.getElementById('localLink').href = `file://${indexPath}`;

                    // Open the product directory for viewing code
                    document.getElementById('docsLink').href = `file://${data.product_path}`;
                    resultSection.classList.add('active');

                } catch (error) {
                    console.error('Error:', error);
                    if (!generationComplete) {
                        addStatusMessage(`❌ ${error.message}`, 'error');
                    }
                } finally {
                    generateBtn.disabled = false;
                    eventSource.close();
                }
            });

            function addStatusMessage(message, type = 'info') {
                const div = document.createElement('div');
                div.className = `status-message ${type}`;
                div.textContent = message;
                statusMessages.appendChild(div);
                statusMessages.scrollTop = statusMessages.scrollHeight;
            }

            function updateStages(currentProgress) {
                const stages = document.querySelectorAll('.stage');
                stages.forEach(stage => {
                    const stageProgress = parseInt(stage.dataset.progress);
                    stage.classList.remove('active', 'completed');

                    if (currentProgress >= stageProgress) {
                        stage.classList.add('completed');
                    } else if (currentProgress >= stageProgress - 30) {
                        stage.classList.add('active');
                    }
                });
            }

            // Poll for status updates
            async function pollStatus(projectId) {
                const response = await fetch(`/api/status/${projectId}`);
                if (response.ok) {
                    const data = await response.json();
                    addStatusMessage(`${data.step}: ${data.message}`);
                    progressFill.style.width = `${data.progress}%`;

                    if (data.status !== 'completed' && data.status !== 'failed') {
                        setTimeout(() => pollStatus(projectId), 500);
                    }
                }
            }
        </script>
    </body>
    </html>
    """


async def update_progress(project_id: str, step: str, progress: int, message: str, status: str = "in_progress"):
    """Update generation progress and broadcast to SSE clients."""
    update = {
        "step": step,
        "progress": progress,
        "message": message,
        "status": status
    }

    # Update status dictionary
    generation_status[project_id] = update

    # Broadcast to SSE clients
    if project_id in progress_queues:
        try:
            await progress_queues[project_id].put(update)
        except Exception as e:
            logger.error(f"Failed to broadcast progress: {e}")


@app.post("/api/generate")
async def generate_product(request: GenerationRequest):
    """Generate a product from a rough idea."""
    try:
        # Validate that rough idea is provided
        if not request.rough_idea or not request.rough_idea.strip():
            raise HTTPException(status_code=400, detail="Rough idea is required")
        
        # Generate project ID if not provided by user
        if not request.project_id or not request.project_id.strip():
            project_id = f"project_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            logger.info(f"No project ID provided, generated: {project_id}")
        else:
            project_id = request.project_id.strip().lower().replace(" ", "_").replace("-", "_")
            logger.info(f"Starting product generation for project: {project_id}")
        
        rough_idea = request.rough_idea

        # Initialize progress queue if it doesn't exist
        if project_id not in progress_queues:
            progress_queues[project_id] = asyncio.Queue()

        # Update status
        await update_progress(
            project_id,
            "Initializing",
            5,
            "Starting product generation...",
            "in_progress"
        )

        # Step 1: Generate documents (BRD, PRD, TRD, STORIES)
        # Note: Skipping document generation for now due to instructor library issue
        # This will be fixed in the next update
        if False and not request.skip_documents:
            generation_status[project_id].update({
                "step": "Document Generation",
                "progress": 10,
                "message": "Generating BRD, PRD, TRD, and Stories..."
            })

            orchestrator_config = OrchestratorConfig(
                llm_model="openrouter/meta-llama/llama-3.3-70b-instruct:free",  # OpenRouter Llama
                max_retries=2,
                pass_score=6
            )
            orchestrator = BlindOrchestrator(config=orchestrator_config)

            # Create project state
            project_state = ProjectState(
                project_id=project_id,
                rough_idea=rough_idea,
                current_phase="IDEA"
            )
            orchestrator.set_state(project_state)

            # Run orchestration phases
            phases_to_run = [Phase.BRD, Phase.PRD, Phase.TRD, Phase.STORIES]
            for i, phase in enumerate(phases_to_run):
                progress = 10 + (i * 15)
                generation_status[project_id].update({
                    "progress": progress,
                    "message": f"Generating {phase.value}..."
                })

                success, document = orchestrator.orchestrate_phase(phase)
                if not success:
                    raise Exception(f"{phase.value} generation failed")

                project_state.set_document(phase.value, document)

            # Get stories from project state
            stories = project_state.stories
        else:
            # Skip to product generation with sample story
            stories = [{
                "id": "story_001",
                "name": "Core Feature",
                "description": rough_idea,
                "depends_on": [],
                "success_criteria": ["Implementation complete"]
            }]

        # Step 2: Generate product
        await update_progress(
            project_id,
            "Generating Backend Code",
            40,
            "Generating backend code with FastAPI...",
            "in_progress"
        )

        # Use OpenRouter model (Llama 3.3)
        product_generator_config = ProductGeneratorConfig(
            llm_model="openrouter/meta-llama/llama-3.3-70b-instruct:free",  # OpenRouter Llama
            api_key=os.getenv("OPENROUTER_API_KEY"),
            max_retries=2,
            run_tests=False,  # Skip tests for faster generation
            worker_pool_size=2
        )

        generator = ProductGenerator(config=product_generator_config)

        # Generate product
        await update_progress(
            project_id,
            "Generating Frontend Code",
            70,
            "Generating frontend code with vanilla JavaScript...",
            "in_progress"
        )

        product_path = await generator.generate_product(
            project_id=project_id,
            stories=stories,
            context_docs={}
        )

        await update_progress(
            project_id,
            "Assembling Product",
            85,
            "Assembling product files...",
            "in_progress"
        )

        await update_progress(
            project_id,
            "Complete",
            100,
            "Product generation complete! ✅",
            "completed"
        )

        return {
            "project_id": project_id,
            "product_path": product_path,
            "status": "success"
        }

    except Exception as e:
        logger.error(f"Error generating product: {str(e)}", exc_info=True)
        await update_progress(
            project_id,
            "Failed",
            0,
            f"Error: {str(e)}",
            "failed"
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status/{project_id}")
async def get_status(project_id: str):
    """Get generation status for a project."""
    if project_id not in generation_status:
        raise HTTPException(status_code=404, detail="Project not found")
    return generation_status[project_id]


def main():
    """Run the web UI."""
    print("\n" + "=" * 70)
    print("VibeFactory Web UI")
    print("=" * 70)
    print("\n🌐 Starting web UI...")
    print("📱 Open your browser and visit: http://localhost:8501\n")
    print("Features:")
    print("  • Describe your product idea")
    print("  • Generate complete backend + frontend")
    print("  • Download and run locally")
    print("  • Zero to deployed in minutes\n")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8501,
        log_level="info"
    )


if __name__ == "__main__":
    main()
