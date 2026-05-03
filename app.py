"""
VibeFactory - Neumorphic UI for Multi-Agent SDLC System
A tactile, modern interface for AI-powered software development.
"""

import streamlit as st
import asyncio
import os
import json
from pathlib import Path
from datetime import datetime

# Page config
st.set_page_config(
    page_title="VibeFactory",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS with Neumorphism Design System
st.markdown("""
<style>
    /* Import Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800&family=DM+Sans:wght@400;500;700&display=swap');
    
    /* Design Tokens */
    :root {
        --bg-color: #E0E5EC;
        --fg-color: #3D4852;
        --muted-color: #6B7280;
        --accent-color: #6C63FF;
        --accent-light: #8B84FF;
        --accent-secondary: #38B2AC;
        --shadow-light: rgba(255, 255, 255, 0.5);
        --shadow-dark: rgb(163, 177, 198, 0.6);
    }
    
    /* Global Styles */
    .stApp {
        background-color: var(--bg-color);
        font-family: 'DM Sans', sans-serif;
    }
    
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Plus Jakarta Sans', sans-serif;
        color: var(--fg-color);
        font-weight: 800;
        letter-spacing: -0.02em;
    }
    
    /* Neumorphic Components */
    .neumorph-container {
        background: var(--bg-color);
        border-radius: 32px;
        box-shadow: 9px 9px 16px var(--shadow-dark), 
                   -9px -9px 16px var(--shadow-light);
        padding: 2rem;
        margin: 1rem 0;
        transition: all 0.3s ease-out;
    }
    
    .neumorph-container:hover {
        transform: translateY(-2px);
        box-shadow: 12px 12px 20px var(--shadow-dark), 
                   -12px -12px 20px var(--shadow-light);
    }
    
    .neumorph-card {
        background: var(--bg-color);
        border-radius: 16px;
        box-shadow: 5px 5px 10px var(--shadow-dark), 
                   -5px -5px 10px var(--shadow-light);
        padding: 1.5rem;
        transition: all 0.3s ease-out;
    }
    
    .neumorph-card:hover {
        transform: translateY(-1px);
        box-shadow: 8px 8px 14px var(--shadow-dark), 
                   -8px -8px 14px var(--shadow-light);
    }
    
    .neumorph-input {
        background: var(--bg-color);
        border-radius: 16px;
        box-shadow: inset 6px 6px 10px var(--shadow-dark), 
                   inset -6px -6px 10px var(--shadow-light);
        border: none;
        padding: 1rem 1.5rem;
        font-size: 1rem;
        color: var(--fg-color);
        transition: all 0.3s ease-out;
        width: 100%;
    }
    
    .neumorph-input:focus {
        outline: none;
        box-shadow: inset 10px 10px 20px var(--shadow-dark), 
                   inset -10px -10px 20px var(--shadow-light);
    }
    
    .neumorph-input::placeholder {
        color: #A0AEC0;
    }
    
    /* Buttons */
    .neumorph-btn {
        background: var(--bg-color);
        color: var(--accent-color);
        border: none;
        border-radius: 16px;
        padding: 0.875rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        cursor: pointer;
        box-shadow: 6px 6px 12px var(--shadow-dark), 
                   -6px -6px 12px var(--shadow-light);
        transition: all 0.3s ease-out;
        font-family: 'Plus Jakarta Sans', sans-serif;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .neumorph-btn:hover {
        transform: translateY(-2px);
        box-shadow: 10px 10px 18px var(--shadow-dark), 
                   -10px -10px 18px var(--shadow-light);
        color: var(--accent-light);
    }
    
    .neumorph-btn:active {
        transform: translateY(1px);
        box-shadow: inset 4px 4px 8px var(--shadow-dark), 
                   inset -4px -4px 8px var(--shadow-light);
    }
    
    .neumorph-btn-primary {
        background: var(--accent-color);
        color: white;
        box-shadow: 6px 6px 12px rgba(108, 99, 255, 0.3), 
                   -6px -6px 12px rgba(108, 99, 255, 0.1);
    }
    
    .neumorph-btn-primary:hover {
        background: var(--accent-light);
        box-shadow: 10px 10px 18px rgba(108, 99, 255, 0.4), 
                   -10px -10px 18px rgba(108, 99, 255, 0.2);
    }
    
    /* Progress Steps */
    .progress-step {
        display: flex;
        align-items: center;
        margin-bottom: 1.5rem;
        opacity: 0.5;
        transition: all 0.3s ease-out;
    }
    
    .progress-step.active {
        opacity: 1;
        transform: scale(1.02);
    }
    
    .progress-step.completed {
        opacity: 0.8;
    }
    
    .step-number {
        width: 48px;
        height: 48px;
        border-radius: 50%;
        background: var(--bg-color);
        box-shadow: 5px 5px 10px var(--shadow-dark), 
                   -5px -5px 10px var(--shadow-light);
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 1.1rem;
        color: var(--fg-color);
        margin-right: 1rem;
        flex-shrink: 0;
    }
    
    .progress-step.active .step-number {
        color: var(--accent-color);
        box-shadow: 6px 6px 12px var(--shadow-dark), 
                   -6px -6px 12px var(--shadow-light);
        animation: pulse 2s infinite;
    }
    
    .progress-step.completed .step-number {
        color: var(--accent-secondary);
    }
    
    .step-info {
        flex: 1;
    }
    
    .step-title {
        font-weight: 600;
        color: var(--fg-color);
        margin-bottom: 0.25rem;
    }
    
    .step-status {
        font-size: 0.875rem;
        color: var(--muted-color);
    }
    
    /* Status Indicators */
    .status-badge {
        display: inline-block;
        padding: 0.5rem 1rem;
        border-radius: 9999px;
        font-size: 0.875rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .status-pending {
        background: var(--bg-color);
        box-shadow: inset 3px 3px 6px var(--shadow-dark), 
                   inset -3px -3px 6px var(--shadow-light);
        color: var(--muted-color);
    }
    
    .status-active {
        background: var(--bg-color);
        box-shadow: 5px 5px 10px var(--shadow-dark), 
                   -5px -5px 10px var(--shadow-light);
        color: var(--accent-color);
        animation: pulse 2s infinite;
    }
    
    .status-completed {
        background: var(--bg-color);
        box-shadow: inset 3px 3px 6px var(--shadow-dark), 
                   inset -3px -3px 6px var(--shadow-light);
        color: var(--accent-secondary);
    }
    
    .status-failed {
        background: var(--bg-color);
        box-shadow: inset 3px 3px 6px var(--shadow-dark), 
                   inset -3px -3px 6px var(--shadow-light);
        color: #E53E3E;
    }
    
    /* Animation */
    @keyframes pulse {
        0%, 100% {
            box-shadow: 6px 6px 12px var(--shadow-dark), 
                       -6px -6px 12px var(--shadow-light);
        }
        50% {
            box-shadow: 8px 8px 16px var(--shadow-dark), 
                       -8px -8px 16px var(--shadow-light);
        }
    }
    
    @keyframes float {
        0%, 100% {
            transform: translateY(0px);
        }
        50% {
            transform: translateY(-10px);
        }
    }
    
    .floating {
        animation: float 3s ease-in-out infinite;
    }
    
    /* Decorative Elements */
    .decorative-circle {
        position: absolute;
        border-radius: 50%;
        background: var(--bg-color);
        box-shadow: 8px 8px 16px var(--shadow-dark), 
                   -8px -8px 16px var(--shadow-light);
        z-index: -1;
    }
    
    /* Hide Streamlit Branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Custom Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: var(--bg-color);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: var(--accent-color);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: var(--accent-light);
    }
    
    /* Responsive */
    @media (max-width: 768px) {
        .neumorph-container {
            padding: 1.5rem;
            border-radius: 24px;
        }
        
        .step-number {
            width: 40px;
            height: 40px;
            font-size: 1rem;
        }
    }
</style>
""", unsafe_allow_html=True)


# Custom components
def neumorph_button(label, key=None, primary=False, disabled=False):
    """Create a neumorphic button."""
    btn_class = "neumorph-btn neumorph-btn-primary" if primary else "neumorph-btn"
    disabled_attr = "disabled" if disabled else ""
    
    html = f"""
    <button class="{btn_class}" {disabled_attr} style="width: 100%; border: none; background: transparent; cursor: {'pointer' if not disabled else 'not-allowed'}; font-family: inherit;">
        {label}
    </button>
    """
    st.markdown(html, unsafe_allow_html=True)


def neumorph_input(label, placeholder="", key=None, type="text", disabled=False):
    """Create a neumorphic input field."""
    st.markdown(f"<p style='color: var(--fg-color); font-weight: 600; margin-bottom: 0.5rem;'>{label}</p>", unsafe_allow_html=True)
    
    input_html = f"""
    <input 
        type="{type}" 
        class="neumorph-input" 
        placeholder="{placeholder}" 
        {'disabled' if disabled else ''}
        id="{key}"
    />
    """
    st.markdown(input_html, unsafe_allow_html=True)
    
    if key:
        return st.session_state.get(key, "")
    return None


def neumorph_card(content, padding="1.5rem"):
    """Create a neumorphic card."""
    st.markdown(f"""
    <div class="neumorph-card" style="padding: {padding};">
        {content}
    </div>
    """, unsafe_allow_html=True)


def progress_step(number, title, status="pending", description=""):
    """Create a progress step indicator."""
    status_class = f"status-{status}"
    
    icon = "⏳" if status == "pending" else ("✅" if status == "completed" else ("🔄" if status == "active" else "❌"))
    
    st.markdown(f"""
    <div class="progress-step {'active' if status == 'active' else ''} {'completed' if status == 'completed' else ''}">
        <div class="step-number">{icon}</div>
        <div class="step-info">
            <div class="step-title">{title}</div>
            <div class="step-status status-badge status-{status}">{status.capitalize()}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_header():
    """Render the header section."""
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown("""
        <div style="text-align: center; padding: 2rem 0;">
            <h1 style="font-size: 3.5rem; margin-bottom: 0.5rem; background: linear-gradient(135deg, var(--accent-color), var(--accent-light)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">
                VibeFactory
            </h1>
            <p style="font-size: 1.25rem; color: var(--muted-color); font-weight: 500;">
                AI-Powered Software Development
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style="text-align: center;">
            <div class="neumorph-card" style="width: 120px; height: 120px; display: flex; align-items: center; justify-content: center; margin: 0 auto;">
                <span style="font-size: 4rem;" class="floating">🎨</span>
            </div>
        </div>
        """, unsafe_allow_html=True)


def render_project_input():
    """Render the project idea input section."""
    with st.container():
        st.markdown("""
        <div class="neumorph-container" style="text-align: center; padding: 3rem 2rem;">
            <h2 style="font-size: 2rem; margin-bottom: 1rem;">What would you like to build?</h2>
            <p style="color: var(--muted-color); font-size: 1.1rem; margin-bottom: 2rem;">
                Describe your project idea and our AI agents will handle the rest
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    # Project idea input
    project_id = st.text_input(
        "Project ID (optional)",
        placeholder="Leave empty for auto-generated ID",
        key="project_id",
        label_visibility="collapsed"
    )
    
    project_idea = st.text_area(
        "Project Idea",
        placeholder="e.g., Build a task management API with user authentication, CRUD operations, and real-time notifications...",
        key="project_idea",
        height=150,
        label_visibility="collapsed"
    )
    
    # Start button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button(
            "🚀 Start Building",
            use_container_width=True,
            type="primary"
        ):
            if not project_idea.strip():
                st.error("Please enter a project idea")
                return None, None
            
            st.session_state.project_idea = project_idea
            st.session_state.project_id = project_id.strip() if project_id.strip() else f"proj_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            st.session_state.project_started = True
            st.rerun()
    
    return None, None


def render_progress_section(state):
    """Render the progress tracking section."""
    st.markdown("""
    <div class="neumorph-container" style="margin-top: 2rem;">
        <h2 style="font-size: 1.75rem; margin-bottom: 2rem;">Development Progress</h2>
    </div>
    """, unsafe_allow_html=True)
    
    with st.container():
        progress_data = state.get('progress', [])
        
        for step in progress_data:
            progress_step(
                number=step.get('number', 0),
                title=step.get('title', ''),
                status=step.get('status', 'pending'),
                description=step.get('description', '')
            )


def render_documents_section(state):
    """Render the documents preview section."""
    st.markdown("""
    <div class="neumorph-container" style="margin-top: 2rem;">
        <h2 style="font-size: 1.75rem; margin-bottom: 2rem;">Generated Documents</h2>
    </div>
    """, unsafe_allow_html=True)
    
    with st.container():
        docs = state.get('documents', {})
        
        doc_cols = st.columns(4)
        doc_titles = {
            'BRD': 'Business Requirements',
            'PRD': 'Product Requirements',
            'TRD': 'Technical Requirements',
            'STORIES': 'User Stories'
        }
        
        for i, (doc_type, title) in enumerate(doc_titles.items()):
            with doc_cols[i]:
                doc_content = docs.get(doc_type, {})
                is_completed = doc_content.get('passed', False)
                
                card_html = f"""
                <div class="neumorph-card" style="text-align: center; cursor: pointer; transition: all 0.3s ease;">
                    <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">
                        {'✅' if is_completed else '📄'}
                    </div>
                    <div style="font-weight: 600; color: var(--fg-color); margin-bottom: 0.25rem;">
                        {title}
                    </div>
                    <div style="font-size: 0.875rem; color: var(--muted-color);">
                        {len(doc_content.get('content', ''))} chars
                    </div>
                </div>
                """
                st.markdown(card_html, unsafe_allow_html=True)


def render_human_approval(state):
    """Render the human-in-the-loop approval section."""
    st.markdown("""
    <div class="neumorph-container" style="margin-top: 2rem;">
        <h2 style="font-size: 1.75rem; margin-bottom: 1rem;">👤 Human Approval Required</h2>
        <p style="color: var(--muted-color);">Review all documents before proceeding to engineering</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.container():
        approval_data = state.get('approval', {})
        
        # Summary
        summary_html = f"""
        <div class="neumorph-container" style="margin-bottom: 2rem;">
            <h3 style="font-size: 1.25rem; margin-bottom: 1rem;">Project Summary</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem;">
                <div class="neumorph-card">
                    <div style="font-weight: 600; color: var(--fg-color); margin-bottom: 0.5rem;">Project ID</div>
                    <div style="color: var(--muted-color);">{approval_data.get('project_id', 'N/A')}</div>
                </div>
                <div class="neumorph-card">
                    <div style="font-weight: 600; color: var(--fg-color); margin-bottom: 0.5rem;">Idea</div>
                    <div style="color: var(--muted-color);">{approval_data.get('idea', 'N/A')[:100]}...</div>
                </div>
            </div>
        </div>
        """
        st.markdown(summary_html, unsafe_allow_html=True)
        
        # Action buttons
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button(
                "✅ Approve & Continue",
                use_container_width=True,
                type="primary"
            ):
                st.session_state.approval_action = "approve"
                st.rerun()
        
        with col2:
            if st.button(
                "❌ Reject & Revise",
                use_container_width=True
            ):
                st.session_state.approval_action = "reject"
                st.rerun()


def render_engineering_results(state):
    """Render engineering execution results."""
    st.markdown("""
    <div class="neumorph-container" style="margin-top: 2rem;">
        <h2 style="font-size: 1.75rem; margin-bottom: 2rem;">Engineering Results</h2>
    </div>
    """, unsafe_allow_html=True)
    
    with st.container():
        eng_data = state.get('engineering', {})
        
        result_html = f"""
        <div class="neumorph-container">
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1.5rem;">
                <div class="neumorph-card">
                    <div style="font-size: 2rem; margin-bottom: 0.5rem;">
                        {'✅' if eng_data.get('completed') and not eng_data.get('failed') else '❌'}
                    </div>
                    <div style="font-weight: 600; color: var(--fg-color);">Status</div>
                    <div style="color: var(--muted-color);">
                        {'Completed' if eng_data.get('completed') and not eng_data.get('failed') else 'Failed'}
                    </div>
                </div>
                <div class="neumorph-card">
                    <div style="font-size: 2rem; margin-bottom: 0.5rem;">🔄</div>
                    <div style="font-weight: 600; color: var(--fg-color);">Retries</div>
                    <div style="color: var(--muted-color);">{eng_data.get('retry_count', 0)}</div>
                </div>
                <div class="neumorph-card">
                    <div style="font-size: 2rem; margin-bottom: 0.5rem;">📊</div>
                    <div style="font-weight: 600; color: var(--fg-color);">Stories</div>
                    <div style="color: var(--muted-color);">{eng_data.get('total_stories', 0)}</div>
                </div>
            </div>
        </div>
        """
        st.markdown(result_html, unsafe_allow_html=True)


def render_e2e_results(state):
    """Render E2E testing results."""
    st.markdown("""
    <div class="neumorph-container" style="margin-top: 2rem;">
        <h2 style="font-size: 1.75rem; margin-bottom: 2rem;">E2E Testing Results</h2>
    </div>
    """, unsafe_allow_html=True)
    
    with st.container():
        e2e_data = state.get('e2e', {})
        
        result_html = f"""
        <div class="neumorph-container">
            <div style="text-align: center; padding: 2rem;">
                <div style="font-size: 4rem; margin-bottom: 1rem;">
                    {'✅' if e2e_data.get('passed') else '❌'}
                </div>
                <div style="font-weight: 700; color: var(--fg-color); font-size: 1.5rem; margin-bottom: 1rem;">
                    {'E2E Tests Passed!' if e2e_data.get('passed') else 'E2E Tests Failed'}
                </div>
                <div style="color: var(--muted-color); max-width: 600px; margin: 0 auto;">
                    {e2e_data.get('feedback', 'No feedback available')}
                </div>
            </div>
        </div>
        """
        st.markdown(result_html, unsafe_allow_html=True)


def render_footer():
    """Render the footer."""
    st.markdown("""
    <div style="text-align: center; padding: 2rem; color: var(--muted-color); font-size: 0.875rem;">
        <p>Built with ❤️ using Neumorphism Design System</p>
        <p style="margin-top: 0.5rem;">Multi-Agent SDLC System</p>
    </div>
    """, unsafe_allow_html=True)


def main():
    """Main application."""
    # Initialize session state
    if 'project_started' not in st.session_state:
        st.session_state.project_started = False
    if 'project_idea' not in st.session_state:
        st.session_state.project_idea = ""
    if 'project_id' not in st.session_state:
        st.session_state.project_id = ""
    if 'approval_action' not in st.session_state:
        st.session_state.approval_action = None
    
    # Render header
    render_header()
    
    # Show project input or progress based on state
    if not st.session_state.project_started:
        render_project_input()
    else:
        # Import runner
        from runner import LangGraphRunner
        
        # Initialize runner
        runner = LangGraphRunner()
        
        # Check for human approval action
        if st.session_state.approval_action:
            st.session_state.approval_action = None
            st.rerun()
        
        # Run the graph
        with st.spinner("🚀 Running SDLC pipeline..."):
            try:
                final_state = runner.resume_or_start(st.session_state.project_id)
                
                # Extract progress data
                progress_data = [
                    {'number': 1, 'title': 'BRD Generation', 'status': 'completed' if final_state.get('brd_passed') else 'failed'},
                    {'number': 2, 'title': 'PRD Generation', 'status': 'completed' if final_state.get('prd_passed') else 'failed'},
                    {'number': 3, 'title': 'TRD Generation', 'status': 'completed' if final_state.get('trd_passed') else 'failed'},
                    {'number': 4, 'title': 'User Stories', 'status': 'completed' if final_state.get('stories_passed') else 'failed'},
                    {'number': 5, 'title': 'Human Approval', 'status': 'completed'},
                    {'number': 6, 'title': 'Engineering', 'status': 'completed' if final_state.get('engineering_completed') and not final_state.get('engineering_failed') else 'failed'},
                    {'number': 7, 'title': 'E2E Testing', 'status': 'completed' if final_state.get('e2e_passed') else 'failed'},
                ]
                
                # Update session state for UI
                st.session_state.progress = progress_data
                st.session_state.documents = {
                    'BRD': {'content': final_state.get('brd_content', ''), 'passed': final_state.get('brd_passed')},
                    'PRD': {'content': final_state.get('prd_content', ''), 'passed': final_state.get('prd_passed')},
                    'TRD': {'content': final_state.get('trd_content', ''), 'passed': final_state.get('trd_passed')},
                    'STORIES': {'content': final_state.get('stories_content', ''), 'passed': final_state.get('stories_passed')},
                }
                st.session_state.approval = {
                    'project_id': final_state.get('project_id'),
                    'idea': final_state.get('rough_idea'),
                }
                st.session_state.engineering = {
                    'completed': final_state.get('engineering_completed'),
                    'failed': final_state.get('engineering_failed'),
                    'retry_count': final_state.get('engineering_retry_count', 0),
                    'total_stories': len(final_state.get('stories', [])),
                }
                st.session_state.e2e = {
                    'passed': final_state.get('e2e_passed'),
                    'feedback': final_state.get('e2e_feedback', ''),
                }
                
                # Render progress
                render_progress_section(st.session_state)
                
                # Render documents
                render_documents_section(st.session_state)
                
                # Render engineering results
                render_engineering_results(st.session_state)
                
                # Render E2E results
                render_e2e_results(st.session_state)
                
                # Success message
                if final_state.get('e2e_passed'):
                    st.success("🎉 Project completed successfully!")
                
            except Exception as e:
                st.error(f"Error: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
    
    # Render footer
    render_footer()


if __name__ == "__main__":
    main()
