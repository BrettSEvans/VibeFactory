"""
Web UI for VibeFactory Product Generator
Simple FastAPI server with HTML/JS frontend for interactive product generation.
"""

import asyncio
import json
import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
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

from state import ProjectState, Document, Story, stories_from_markdown
from orchestrator import BlindOrchestrator, OrchestratorConfig, Phase
from product_generator import ProductGenerator, ProductGeneratorConfig
from local_config import OLLAMA_HOST


class GenerationRequest(BaseModel):
    """Request to generate a product."""
    project_id: Optional[str] = None  # User-provided project ID (optional, will generate if not provided)
    rough_idea: str
    skip_documents: bool = False  # Skip BRD/PRD/TRD if True
    llm_provider: str = "openrouter"  # "ollama", "openrouter", or "inception"
    llm_model: Optional[str] = None  # Specific model within provider


class GenerationProgress(BaseModel):
    """Progress update during generation."""
    step: str
    status: str  # "started", "in_progress", "completed", "failed"
    progress: int  # 0-100
    message: str
    error: Optional[str] = None


class ApprovalRequest(BaseModel):
    """Request to approve a document phase and resume the pipeline."""
    phase: str
    content: str  # The (possibly edited) document text


# Create FastAPI app
app = FastAPI(title="VibeFactory UI", version="1.0")

# Store generation status
generation_status = {}
progress_queues = {}  # {project_id: asyncio.Queue of progress updates}
approval_futures: Dict[str, Dict[str, Any]] = {}  # {project_id: {phase: asyncio.Future}}


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
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/easymde/dist/easymde.min.css">
        <script src="https://cdn.jsdelivr.net/npm/easymde/dist/easymde.min.js"></script>
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

            /* LLM Provider Selection Styles */
            .btn-provider {
                flex: 1;
                padding: 12px;
                border: 2px solid #e0e0e0;
                background: white;
                color: #333;
                border-radius: 8px;
                cursor: pointer;
                font-weight: 400;
                transition: all 0.3s;
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 4px;
            }

            .btn-provider:hover:not(:disabled) {
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            }

            .btn-provider.selected {
                background: #4caf50;
                color: white;
                border-color: #4caf50;
                font-weight: 600;
                box-shadow: 0 4px 12px rgba(76, 175, 80, 0.3);
            }

            .btn-provider.selected:hover:not(:disabled) {
                background: #43a047;
                border-color: #43a047;
            }

            .btn-provider.unavailable {
                background: #f5f5f5;
                color: #999;
                border-color: #ddd;
                cursor: not-allowed;
                opacity: 0.6;
            }

            .btn-provider.unavailable:hover {
                transform: none;
                box-shadow: none;
            }

            .btn-provider .provider-status {
                font-size: 11px;
                opacity: 0.8;
            }

            .btn-provider.selected .provider-status {
                opacity: 0.9;
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

            /* HITL Review Panel */
            .review-panel {
                background: #fff;
                border: 2px solid #667eea;
                border-radius: 12px;
                padding: 24px;
                margin-top: 24px;
            }
            .review-header h2 {
                margin: 0 0 6px 0;
                font-size: 1.2rem;
                color: #333;
            }
            .review-header p {
                margin: 0 0 16px 0;
                color: #666;
                font-size: 0.9rem;
            }
            #editorContainer .EasyMDEContainer {
                border-radius: 8px;
                overflow: hidden;
            }
            #documentEditor {
                width: 100%;
                min-height: 300px;
                padding: 12px;
                font-family: monospace;
                font-size: 0.85rem;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                resize: vertical;
                box-sizing: border-box;
            }
            .review-actions {
                display: flex;
                justify-content: flex-end;
                margin-top: 16px;
            }
            .review-actions .btn-generate {
                padding: 12px 28px;
                font-size: 1rem;
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

                <!-- LLM Provider Selection -->
                <div class="form-group">
                    <label>LLM Provider</label>
                    <div id="providers-loading" class="status-message">
                        🔍 Detecting available LLM providers...
                    </div>
                    <div id="providers-container" style="display: none;">
                        <div id="provider-buttons" style="display: flex; gap: 12px; margin-bottom: 16px;"></div>
                        <div id="model-selection" style="display: none; margin-top: 12px;">
                            <label for="model-select" style="margin-bottom: 8px;">Model:</label>
                            <select id="model-select" style="width: 100%; padding: 10px; border: 2px solid #e0e0e0; border-radius: 8px; font-family: inherit;">
                            </select>
                        </div>
                    </div>
                </div>

                <div class="form-group">
                    <label for="roughIdea">Your Idea</label>
                    <textarea
                        id="roughIdea"
                        name="roughIdea"
                        placeholder="Describe what you want to build..."
                        required
                    ></textarea>

                </div>

                <div class="form-group checkbox-group">
                    <input
                        type="checkbox"
                        id="skipDocs"
                        name="skipDocs"
                    >
                    <label for="skipDocs">Skip document generation (BRD/PRD/TRD) — go straight to code</label>
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
                        <div class="stage-label">BRD</div>
                    </div>
                    <div class="stage" data-progress="20">
                        <div class="stage-dot">2</div>
                        <div class="stage-label">PRD</div>
                    </div>
                    <div class="stage" data-progress="35">
                        <div class="stage-dot">3</div>
                        <div class="stage-label">TRD</div>
                    </div>
                    <div class="stage" data-progress="50">
                        <div class="stage-dot">4</div>
                        <div class="stage-label">Stories</div>
                    </div>
                    <div class="stage" data-progress="75">
                        <div class="stage-dot">5</div>
                        <div class="stage-label">Code</div>
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

            <!-- HITL Document Review Panel -->
            <div class="review-panel" id="reviewPanel" style="display:none;">
                <div class="review-header">
                    <h2 id="reviewTitle">📄 Review Document</h2>
                    <p id="reviewHint">Read the document below. Edit if needed, then click <strong>Approve &amp; Continue</strong> to proceed to the next phase.</p>
                </div>
                <div id="editorContainer">
                    <textarea id="documentEditor"></textarea>
                </div>
                <div class="review-actions">
                    <button id="approveBtn" class="btn-generate" onclick="approveDocument()">
                        ✅ Approve &amp; Continue
                    </button>
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

            // LLM Provider selection
            let selectedProvider = localStorage.getItem('vibefactory_llm_provider') || 'openrouter';
            let selectedModel = localStorage.getItem('vibefactory_llm_model') || null;

            async function loadProviders() {
                try {
                    const response = await fetch('/api/llm-providers');
                    const data = await response.json();

                    document.getElementById('providers-loading').style.display = 'none';
                    document.getElementById('providers-container').style.display = 'block';

                    // Render provider buttons
                    const container = document.getElementById('provider-buttons');
                    container.innerHTML = '';

                    for (const provider of data.providers) {
                        const btn = document.createElement('button');
                        btn.type = 'button';
                        btn.className = 'btn-provider';
                        
                        // Add selected or unavailable class
                        if (selectedProvider === provider.id) {
                            btn.classList.add('selected');
                        }
                        if (!provider.available) {
                            btn.classList.add('unavailable');
                            btn.disabled = true;
                        }
                        
                        btn.innerHTML = `${provider.name}<br><span class="provider-status">${provider.status}</span>`;

                        if (provider.available) {
                            btn.addEventListener('click', (e) => {
                                e.preventDefault();
                                selectProvider(provider);
                            });
                        }
                        container.appendChild(btn);
                    }

                    // Initialize with default or stored provider
                    const defaultProvider = data.providers.find(p => p.id === selectedProvider && p.available) ||
                                             data.providers.find(p => p.available);
                    if (defaultProvider) {
                        selectProvider(defaultProvider);
                    }
                } catch (error) {
                    document.getElementById('providers-loading').innerHTML = '❌ Failed to load providers';
                    console.error('Error loading providers:', error);
                }
            }

            function selectProvider(provider) {
                selectedProvider = provider.id;
                selectedModel = null;
                localStorage.setItem('vibefactory_llm_provider', provider.id);
                localStorage.removeItem('vibefactory_llm_model');

                // Update button styles - apply selected/unavailable classes
                document.querySelectorAll('.btn-provider').forEach(btn => {
                    const btnProviderName = btn.querySelector(':scope > span:first-child, :scope > div:first-child');
                    const btnText = btnProviderName ? btnProviderName.textContent : btn.textContent;
                    const isSelected = btnText.includes(provider.name);
                    
                    // Remove all state classes
                    btn.classList.remove('selected', 'unavailable');
                    
                    if (isSelected) {
                        btn.classList.add('selected');
                    } else if (btn.disabled) {
                        btn.classList.add('unavailable');
                    }
                });

                // Update model dropdown
                const modelSelect = document.getElementById('model-select');
                const modelDiv = document.getElementById('model-selection');

                if (provider.models && provider.models.length > 0) {
                    modelSelect.innerHTML = '';
                    for (const model of provider.models) {
                        const option = document.createElement('option');
                        option.value = model;
                        option.textContent = model;
                        modelSelect.appendChild(option);
                    }
                    modelDiv.style.display = 'block';

                    // Auto-select stored model or first available
                    const storedModel = localStorage.getItem('vibefactory_llm_model');
                    const storedOption = storedModel && [...modelSelect.options].find(o => o.value === storedModel);
                    if (storedOption) {
                        modelSelect.value = storedModel;
                        selectedModel = storedModel;
                    } else {
                        modelSelect.selectedIndex = 0;
                        selectedModel = modelSelect.options[0].value;
                        localStorage.setItem('vibefactory_llm_model', selectedModel);
                    }

                    modelSelect.addEventListener('change', (e) => {
                        selectedModel = e.target.value;
                        localStorage.setItem('vibefactory_llm_model', selectedModel);
                    }, { once: true });
                } else {
                    modelDiv.style.display = 'none';
                }
            }

            // ── HITL document review ────────────────────────────────────────────
            let easyMDE = null;
            let currentReviewPhase = null;
            let currentProjectId = null;

            function showReviewPanel(phase, docContent) {
                currentReviewPhase = phase;
                document.getElementById('reviewTitle').textContent = `📄 Review ${phase}`;
                document.getElementById('reviewPanel').style.display = 'block';

                // Destroy previous EasyMDE instance if any
                if (easyMDE) { try { easyMDE.toTextArea(); } catch(e) {} easyMDE = null; }

                // All documents use EasyMDE markdown editor now
                // (STORIES was converted from JSON to markdown format)
                document.getElementById('documentEditor').style.display = 'block';
                easyMDE = new EasyMDE({
                    element: document.getElementById('documentEditor'),
                    initialValue: docContent,
                    spellChecker: false,
                    autosave: { enabled: false },
                    toolbar: ['bold','italic','heading','|','quote','unordered-list','ordered-list','|','preview','side-by-side','fullscreen'],
                });
                document.getElementById('reviewPanel').scrollIntoView({ behavior: 'smooth' });
            }

            async function approveDocument() {
                const content = easyMDE
                    ? easyMDE.value()
                    : document.getElementById('documentEditor').value;

                const btn = document.getElementById('approveBtn');
                btn.disabled = true;
                btn.textContent = '⏳ Submitting...';

                try {
                    await fetch(`/api/approve/${currentProjectId}`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ phase: currentReviewPhase, content })
                    });
                    document.getElementById('reviewPanel').style.display = 'none';
                    addStatusMessage(`✅ ${currentReviewPhase} approved`, 'success');
                } catch(err) {
                    addStatusMessage(`❌ Failed to submit approval: ${err.message}`, 'error');
                } finally {
                    btn.disabled = false;
                    btn.textContent = '✅ Approve & Continue';
                }
            }
            // ────────────────────────────────────────────────────────────────────

            form.addEventListener('submit', async (e) => {
                e.preventDefault();

                const projectId = document.getElementById('projectId').value;
                currentProjectId = projectId;  // needed by HITL approveDocument()
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

                        // Handle HITL document review pause
                        if (data.status === 'review_required') {
                            addStatusMessage(`📄 ${data.phase} ready for review`, 'info');
                            showReviewPanel(data.phase, data.document);
                            return;  // don't update progress bar — wait for user approval
                        }

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
                            generateBtn.disabled = false;

                            // Show result section using product_path from SSE event
                            if (data.product_path) {
                                resultPath.textContent = data.product_path;
                                const projectName = projectId.replace(/[^a-z0-9_-]/gi, '_');
                                document.getElementById('localLink').href = `/product/${projectName}/frontend/index.html`;
                                document.getElementById('docsLink').onclick = (e) => {
                                    e.preventDefault();
                                    fetch(`/api/open-folder/${projectName}`, {method: 'POST'}).catch(err => console.error(err));
                                };
                                resultSection.classList.add('active');
                            }
                        } else if (data.status === 'failed') {
                            generationComplete = true;
                            eventSource.close();
                            addStatusMessage(`❌ Generation failed: ${data.message}`, 'error');
                            generateBtn.disabled = false;
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
                            skip_documents: skipDocs,
                            llm_provider: selectedProvider,
                            llm_model: selectedModel || null
                        })
                    });

                    if (!response.ok) {
                        throw new Error(`Generation failed: ${response.statusText}`);
                    }

                    const data = await response.json();

                    // Generation started in background — product_path and result section
                    // are handled by the SSE onmessage 'completed' event handler above.
                    if (data.status !== 'started') {
                        throw new Error(`Unexpected response: ${JSON.stringify(data)}`);
                    }

                } catch (error) {
                    console.error('Error:', error);
                    generateBtn.disabled = false;
                    eventSource.close();
                    if (!generationComplete) {
                        addStatusMessage(`❌ ${error.message}`, 'error');
                    }
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

            // Load providers when page loads
            document.addEventListener('DOMContentLoaded', loadProviders);
        </script>
    </body>
    </html>
    """


async def update_progress(project_id: str, step: str, progress: int, message: str, status: str = "in_progress", extra: dict = None):
    """Update generation progress and broadcast to SSE clients."""
    update = {
        "step": step,
        "progress": progress,
        "message": message,
        "status": status,
        **(extra or {})
    }

    # Update status dictionary
    generation_status[project_id] = update

    # Broadcast to SSE clients
    if project_id in progress_queues:
        try:
            await progress_queues[project_id].put(update)
        except Exception as e:
            logger.error(f"Failed to broadcast progress: {e}")


async def wait_for_human_approval(
    project_id: str, phase: str, doc_content: str, progress_pct: int
) -> str:
    """
    Emit a review_required SSE event, then suspend until the user POSTs approval.
    Returns the (possibly edited) document content.
    """
    if project_id not in approval_futures:
        approval_futures[project_id] = {}
    loop = asyncio.get_event_loop()
    future: asyncio.Future = loop.create_future()
    approval_futures[project_id][phase] = future

    await update_progress(
        project_id, f"{phase}_REVIEW", progress_pct,
        f"📄 {phase} ready — review and approve to continue",
        status="review_required",
        extra={"phase": phase, "document": doc_content},
    )

    approved_content = await future  # suspends here until /api/approve is called
    if project_id in approval_futures and phase in approval_futures[project_id]:
        del approval_futures[project_id][phase]
    return approved_content


@app.post("/api/approve/{project_id}")
async def approve_document(project_id: str, body: ApprovalRequest):
    """Receive user approval (and possibly edited content) for a document phase."""
    future = approval_futures.get(project_id, {}).get(body.phase)
    if not future or future.done():
        raise HTTPException(
            status_code=404,
            detail=f"No pending review for phase '{body.phase}' in project '{project_id}'"
        )
    future.set_result(body.content)
    return {"status": "approved", "phase": body.phase}


@app.get("/api/llm-providers")
async def get_llm_providers():
    """Get available LLM providers and their status."""
    providers = []

    # Check Ollama availability
    try:
        import urllib.request
        response = urllib.request.urlopen(f"{OLLAMA_HOST}/api/tags", timeout=5)
        if response.status == 200:
            data = json.loads(response.read().decode())
            models = [m["name"] for m in data.get("models", [])]
            providers.append({
                "name": "Local Qwen (Ollama)",
                "id": "ollama",
                "available": True,
                "models": models if models else ["qwen3.5:7b"],
                "status": "✅ Ollama running"
            })
        else:
            raise Exception("Failed to connect to Ollama")
    except Exception as e:
        providers.append({
            "name": "Local Qwen (Ollama)",
            "id": "ollama",
            "available": False,
            "models": [],
            "status": "⚠️ Ollama not running. Start with: ollama serve"
        })

    # Check OpenRouter API key
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    providers.append({
        "name": "OpenRouter (Cloud)",
        "id": "openrouter",
        "available": bool(openrouter_api_key),
        "models": ["meta-llama/llama-3.3-70b-instruct:free"],
        "status": "✅ API key configured" if openrouter_api_key else "⚠️ OPENROUTER_API_KEY not set"
    })

    # Check Inception API key
    inception_api_key = os.getenv("INCEPTION_API_KEY")
    providers.append({
        "name": "Inception Mercury-2",
        "id": "inception",
        "available": bool(inception_api_key),
        "models": ["mercury-2"],
        "status": "✅ API key configured" if inception_api_key else "⚠️ INCEPTION_API_KEY not set"
    })

    # Determine default based on availability (prefer local, then inception, then openrouter)
    default = "ollama"
    if not providers[0]["available"]:
        default = "inception" if providers[2]["available"] else "openrouter"

    return {"providers": providers, "default": default}


async def _run_generation_task(
    project_id: str,
    rough_idea: str,
    llm_model: str,
    llm_api_key: Optional[str],
    skip_documents: bool = False,
    llm_api_base: Optional[str] = None,
):
    """
    Background asyncio task: optionally runs BRD→PRD→TRD→Stories via BlindOrchestrator,
    then generates product code via ProductGenerator.
    Each orchestrator phase runs in a thread executor so the async event loop stays free
    to flush SSE progress messages between phases.
    """
    loop = asyncio.get_event_loop()
    try:
        context_docs = {}
        stories = None  # Will be populated from orchestrator or fall-through default

        if not skip_documents:
            # ── Document generation phase ──────────────────────────────────────
            from state import ProjectState
            from orchestrator import BlindOrchestrator, OrchestratorConfig, Phase

            project_state = ProjectState(project_id=project_id, rough_idea=rough_idea)
            orchestrator_config = OrchestratorConfig(
                llm_model=llm_model,
                api_key=llm_api_key,
                api_base=llm_api_base,
                max_retries=2,
                pass_score=6,
            )
            orchestrator = BlindOrchestrator(config=orchestrator_config, state=project_state)

            # BRD
            await update_progress(project_id, "BRD", 5,
                "📋 Writing Business Requirements Document...", "in_progress")
            await asyncio.sleep(0)
            await loop.run_in_executor(
                None, lambda: orchestrator.orchestrate_phase(Phase.BRD)
            )
            # HITL: pause for BRD review
            brd_doc = project_state.docs.get("BRD")
            if brd_doc and brd_doc.content:
                approved_brd = await wait_for_human_approval(project_id, "BRD", brd_doc.content, 12)
                brd_doc.content = approved_brd
                brd_doc.status = "approved"

            # PRD
            await update_progress(project_id, "PRD", 20,
                "📝 Writing Product Requirements Document...", "in_progress")
            await asyncio.sleep(0)
            await loop.run_in_executor(
                None, lambda: orchestrator.orchestrate_phase(Phase.PRD)
            )
            # HITL: pause for PRD review
            prd_doc = project_state.docs.get("PRD")
            if prd_doc and prd_doc.content:
                approved_prd = await wait_for_human_approval(project_id, "PRD", prd_doc.content, 27)
                prd_doc.content = approved_prd
                prd_doc.status = "approved"

            # TRD
            await update_progress(project_id, "TRD", 35,
                "🏗️ Writing Technical Requirements Document...", "in_progress")
            await asyncio.sleep(0)
            await loop.run_in_executor(
                None, lambda: orchestrator.orchestrate_phase(Phase.TRD)
            )
            # HITL: pause for TRD review
            trd_doc = project_state.docs.get("TRD")
            if trd_doc and trd_doc.content:
                approved_trd = await wait_for_human_approval(project_id, "TRD", trd_doc.content, 42)
                trd_doc.content = approved_trd
                trd_doc.status = "approved"

            # Stories
            await update_progress(project_id, "Stories", 50,
                "📖 Breaking down User Stories...", "in_progress")
            await asyncio.sleep(0)
            await loop.run_in_executor(
                None, lambda: orchestrator.orchestrate_phase(Phase.STORIES)
            )
            # HITL: pause for STORIES review
            stories_hitl_doc = project_state.docs.get("STORIES")
            if stories_hitl_doc and stories_hitl_doc.content:
                approved_stories = await wait_for_human_approval(
                    project_id, "STORIES", stories_hitl_doc.content, 55
                )
                stories_hitl_doc.content = approved_stories
                stories_hitl_doc.status = "approved"

            # Save docs to disk inside the product directory
            docs_dir = Path(f"./products/{project_id}/docs")
            docs_dir.mkdir(parents=True, exist_ok=True)
            for doc_type in ["BRD", "PRD", "TRD", "STORIES"]:
                doc = project_state.docs.get(doc_type)
                if doc and doc.content:
                    # All documents are now markdown format
                    ext = ".md"
                    (docs_dir / f"{doc_type}{ext}").write_text(doc.content)
                    context_docs[doc_type] = doc.content
                    logger.info(f"Saved {doc_type} ({len(doc.content)} chars)")

            # Parse stories from the STORIES document (markdown format)
            stories_doc = project_state.docs.get("STORIES")
            if stories_doc and stories_doc.content:
                try:
                    # Parse markdown format stories
                    stories = stories_from_markdown(stories_doc.content)
                    logger.info(f"✓ Parsed {len(stories)} stories from STORIES doc")
                except Exception as e:
                    logger.warning(f"⚠ Could not parse STORIES markdown ({type(e).__name__}: {str(e)[:100]}); using single-story fallback")
                    stories = None

        # ── Fallback: single story if docs skipped or STORIES parse failed ──
        if not stories:
            story_name = rough_idea.strip().rstrip('.').title()
            if len(story_name) > 60:
                story_name = story_name[:57] + "..."

            # Generate a default LLM prompt based on rough_idea
            llm_prompt = f"""Implement a product based on the following description:

{rough_idea}

Create the complete implementation (both backend and frontend as needed) that matches this description.
Ensure the code is production-ready, includes error handling, and is well-documented."""

            stories = [Story(
                id="story_001",
                name=story_name,
                description=rough_idea,
                llm_prompt=llm_prompt,
                tech_suggestions={},  # Will be determined by code generators
                depends_on=[],
                sequence_order=1,
                success_criteria=["Implementation complete"],
            )]

        # ── Code generation phase ──────────────────────────────────────────────
        # Determine provider label based on actual provider (not LiteLLM format)
        if llm_api_base and "inceptionlabs.ai" in llm_api_base:
            provider_label = "Inception Mercury-2"
        else:
            provider_label = llm_model.split("/")[0].capitalize()
        await update_progress(project_id, "Code", 55,
            f"⚙️ Generating code with {provider_label}...", "in_progress")
        await asyncio.sleep(0)

        # Build a thread-safe story-progress callback
        def _story_callback(story_index: int, total_stories: int, story_name: str, status_msg: str):
            pct = 60 + int(30 * story_index / max(total_stories, 1))
            msg = f"Story {story_index} of {total_stories} — {story_name}: {status_msg}"
            asyncio.run_coroutine_threadsafe(
                update_progress(project_id, "Code", pct, msg, "in_progress"),
                loop,
            )

        product_generator_config = ProductGeneratorConfig(
            llm_model=llm_model,
            api_key=llm_api_key,
            api_base=llm_api_base,
            max_retries=2,
            run_tests=False,
            worker_pool_size=2,
            progress_callback=_story_callback,
        )
        generator = ProductGenerator(config=product_generator_config)

        product_path = await generator.generate_product(
            project_id=project_id,
            stories=stories,
            context_docs=context_docs,
        )

        await update_progress(project_id, "Complete", 100,
            "✅ Product generation complete!", "completed",
            extra={"product_path": product_path})

    except Exception as e:
        logger.error(f"Error generating product: {str(e)}", exc_info=True)
        await update_progress(project_id, "Failed", 0, f"Error: {str(e)}", "failed")


@app.post("/api/generate")
async def generate_product(request: GenerationRequest):
    """Launch product generation as a background task; returns immediately."""
    if not request.rough_idea or not request.rough_idea.strip():
        raise HTTPException(status_code=400, detail="Rough idea is required")

    if not request.project_id or not request.project_id.strip():
        project_id = f"project_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    else:
        project_id = request.project_id.strip().lower().replace(" ", "_").replace("-", "_")

    logger.info(f"Starting generation for project: {project_id}")

    # Ensure progress queue exists before task starts
    if project_id not in progress_queues:
        progress_queues[project_id] = asyncio.Queue()

    # Determine LLM model and API configuration
    llm_api_base = None
    if request.llm_provider == "ollama":
        llm_model = f"ollama/{request.llm_model or 'qwen3.5:7b'}"
        llm_api_key = None
    elif request.llm_provider == "inception":
        # Inception API is OpenAI-compatible — use openai prefix with custom base URL
        llm_model = "openai/mercury-2"
        llm_api_key = os.getenv("INCEPTION_API_KEY")
        llm_api_base = "https://api.inceptionlabs.ai/v1"
    else:  # openrouter
        llm_model = f"openrouter/{request.llm_model or 'meta-llama/llama-3.3-70b-instruct:free'}"
        llm_api_key = os.getenv("OPENROUTER_API_KEY")

    logger.info(f"Using LLM: {llm_model} (provider: {request.llm_provider})")

    mode = "skipping docs" if request.skip_documents else "BRD → PRD → TRD → Stories → Code"
    await update_progress(project_id, "Initializing", 2,
                           f"Starting ({mode}) with {llm_model}...", "in_progress")

    # Launch as background task — returns immediately, SSE streams all progress
    asyncio.create_task(_run_generation_task(
        project_id, request.rough_idea, llm_model, llm_api_key,
        skip_documents=request.skip_documents,
        llm_api_base=llm_api_base,
    ))

    return {"project_id": project_id, "status": "started"}


@app.get("/api/status/{project_id}")
async def get_status(project_id: str):
    """Get generation status for a project."""
    if project_id not in generation_status:
        raise HTTPException(status_code=404, detail="Project not found")
    return generation_status[project_id]


@app.get("/product/{project_id}/{full_path:path}")
async def serve_product_file(project_id: str, full_path: str):
    """Serve generated product files via HTTP."""
    product_dir = Path("./products") / project_id / full_path

    if not product_dir.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if product_dir.is_file():
        return FileResponse(product_dir)

    # If it's a directory with index.html, serve that
    index = product_dir / "index.html"
    if index.exists():
        return FileResponse(index)

    raise HTTPException(status_code=404, detail="Not a file")


@app.post("/api/open-folder/{project_id}")
async def open_folder(project_id: str):
    """Open the product directory in Finder/Explorer."""
    product_dir = Path("./products") / project_id

    if not product_dir.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        import subprocess
        import platform

        if platform.system() == "Darwin":  # macOS
            subprocess.Popen(["open", str(product_dir)])
        elif platform.system() == "Windows":
            subprocess.Popen(["explorer", str(product_dir)])
        else:  # Linux
            subprocess.Popen(["xdg-open", str(product_dir)])

        return {"status": "opened"}
    except Exception as e:
        logger.error(f"Failed to open folder: {e}")
        raise HTTPException(status_code=500, detail="Failed to open folder")


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
