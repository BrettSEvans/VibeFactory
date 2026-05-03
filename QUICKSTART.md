# 🎨 VibeFactory - Quick Start Guide

## Overview
VibeFactory is an AI-powered software development lifecycle (SDLC) system with a beautiful Neumorphic UI. Describe your project idea, and our multi-agent system will handle everything from requirements to testing.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Navigate to the project
cd /Users/brettevanssf/Code/Saasless/VibeFactory

# Activate virtual environment
source venv/bin/activate

# Install dependencies (if needed)
pip install -r requirements.txt
```

### 2. Set API Key

```bash
export OPENAI_API_KEY='your-openai-api-key-here'
```

### 3. Ensure Docker is Running

```bash
# Docker Desktop should be open
docker ps  # Should show Docker daemon running
```

### 4. Launch the UI

```bash
streamlit run app.py
```

Your browser will automatically open to `http://localhost:8501`

## 📋 Using the UI

### Starting a New Project

1. **Enter Project Idea**: Describe what you want to build in detail
   - Example: "Build a task management API with user authentication, CRUD operations, and real-time notifications"

2. **Click "🚀 Start Building"**: The AI agents will begin working

3. **Watch Progress**: The UI shows real-time progress through each phase:
   - ✅ BRD Generation (Business Requirements)
   - ✅ PRD Generation (Product Requirements)
   - ✅ TRD Generation (Technical Requirements)
   - ✅ User Stories
   - 👤 Human Approval (you review and approve)
   - ⚙️ Engineering (code generation & testing)
   - 🧪 E2E Testing (end-to-end validation)

### Human Approval Phase

Before engineering begins, you'll see:
- Project summary
- All generated documents
- Options to **Approve** or **Reject**

### Viewing Results

After completion, you'll see:
- Document previews (BRD, PRD, TRD, Stories)
- Engineering results (success/failure, retries)
- E2E test results

## 🎨 Design System

The UI uses a **Neumorphism (Soft UI)** design system:
- **Color**: Cool grey `#E0E5EC` background
- **Shadows**: Dual opposing shadows for 3D depth
- **Typography**: Plus Jakarta Sans + DM Sans
- **Interactions**: Smooth micro-animations and hover effects
- **Accessibility**: WCAG AA compliant contrast ratios

## 🔧 Configuration

### Customizing the Runner

Edit `runner.py` to adjust:
- **LLM Model**: Change `llm_model` in `OrchestratorConfig` or `EngineerConfig`
- **Worker Pool Size**: Adjust `worker_pool_size` in `EngineerConfig`
- **Max Retries**: Set `max_retries` in both configs
- **Pass Score**: Configure `pass_score` threshold

### State Directory

By default, state is saved to `./sdlc_state/`. Customize in `runner.py`:

```python
runner = LangGraphRunner(state_dir="./custom_state_path")
```

## 📁 Project Structure

```
VibeFactory/
├── app.py                 # Streamlit UI (Neumorphic)
├── runner.py              # LangGraph FSM orchestrator
├── engineer.py            # Engineering execution
├── orchestrator.py        # Document generation
├── sandbox.py             # Docker execution
├── state.py               # Pydantic models
├── requirements.txt       # Dependencies
├── README.md              # Documentation
└── sdlc_state/            # Project state storage
```

## 🎯 Example Workflow

1. **Input**: "Build a REST API for a blog with user authentication, posts, comments, and search"

2. **AI Processing**:
   - Generates BRD with ROI and KPIs
   - Creates PRD with personas and features
   - Designs TRD with architecture and API endpoints
   - Breaks into user stories with dependencies

3. **Your Review**: Approve the plan

4. **Engineering**:
   - Code generation for each story
   - Security validation
   - Pytest execution
   - E2E test generation and execution

5. **Result**: Fully tested, documented project ready for deployment

## 🐛 Troubleshooting

### Docker Not Running
```bash
# Start Docker Desktop
open -a Docker

# Verify
docker ps
```

### API Key Issues
```bash
# Set API key
export OPENAI_API_KEY='sk-...'

# Verify
python -c "import os; print(os.getenv('OPENAI_API_KEY') is not None)"
```

### Port Already in Use
```bash
# Run on different port
streamlit run app.py --server.port 8502
```

### State Loading Issues
```bash
# Clear state directory
rm -rf sdlc_state/*

# Try again
streamlit run app.py
```

## 🎓 Next Steps

- **Customize Prompts**: Edit prompts in `orchestrator.py` and `engineer.py`
- **Add New Agents**: Extend the LangGraph workflow
- **Integrate Other LLMs**: Modify `litellm` configuration
- **Deploy**: Containerize with Docker for production use

## 📞 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review error messages in the UI
3. Check terminal output for detailed logs

## 🎉 Enjoy Building!

VibeFactory turns your ideas into fully developed, tested software with AI assistance. Happy coding! 🚀
