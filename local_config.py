"""
Local Model Configuration for VibeFactory
Configures the system to use local Qwen3.5 model via Ollama
"""

import os
from typing import Optional

# Local Model Configuration
LOCAL_MODEL = "qwen3.5:7b"  # Default local model
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# Alternative local models available via Ollama:
# - qwen3.5:72b (72B - most capable, requires more RAM)
# - qwen3.5:32b (32B - good balance)
# - qwen3.5:14b (14B - lighter weight)
# - llama3.2:3b (3B - very fast, less capable)
# - mistral:7b (7B - good alternative)

def setup_local_environment():
    """
    Set up local environment variables.
    Call this before initializing any agents.
    """
    # Check if Ollama is running
    import urllib.request
    
    try:
        response = urllib.request.urlopen(f"{OLLAMA_HOST}/api/tags", timeout=5)
        if response.status == 200:
            print("✅ Ollama is running!")
            return True
    except Exception as e:
        print(f"⚠️  Ollama doesn't appear to be running: {e}")
        print("   Start Ollama with: ollama serve")
        return False
    
    return False

def get_local_config():
    """
    Get local model configuration for agents.
    
    Returns:
        dict: Configuration dictionary for orchestrator and engineer
    """
    return {
        "llm_model": LOCAL_MODEL,
        "ollama_host": OLLAMA_HOST,
        "max_retries": 3,
        "pass_score": 7,
        "worker_pool_size": 4
    }

def check_model_available():
    """
    Check if the local model is available.
    
    Returns:
        bool: True if model is available, False otherwise
    """
    import urllib.request
    import json
    
    try:
        response = urllib.request.urlopen(f"{OLLAMA_HOST}/api/tags", timeout=5)
        data = json.loads(response.read().decode())
        
        models = [m["name"] for m in data.get("models", [])]
        
        if LOCAL_MODEL in models:
            print(f"✅ Model '{LOCAL_MODEL}' is available!")
            return True
        else:
            print(f"⚠️  Model '{LOCAL_MODEL}' not found!")
            print(f"   Available models: {', '.join(models)}")
            print(f"\n   To pull the model:")
            print(f"   ollama pull {LOCAL_MODEL}")
            return False
            
    except Exception as e:
        print(f"❌ Error checking models: {e}")
        return False

def pull_model():
    """
    Pull the local model using Ollama.
    
    Returns:
        bool: True if successful, False otherwise
    """
    import subprocess
    
    print(f"\n📥 Pulling model: {LOCAL_MODEL}")
    print("   This may take several minutes depending on your connection...")
    
    try:
        result = subprocess.run(
            ["ollama", "pull", LOCAL_MODEL],
            capture_output=False,
            text=True
        )
        
        if result.returncode == 0:
            print(f"✅ Model '{LOCAL_MODEL}' installed successfully!")
            return True
        else:
            print(f"❌ Failed to pull model: {result.stderr}")
            return False
            
    except FileNotFoundError:
        print("❌ Ollama not found. Install from: https://ollama.ai")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

# Quick setup instructions
SETUP_INSTRUCTIONS = """
🚀 Local Model Setup (Qwen3.5 via Ollama)
==========================================

1. Install Ollama:
   - Go to: https://ollama.ai
   - Download and install for your OS
   - Or via Homebrew: brew install ollama

2. Pull the Qwen3.5 model:
   ollama pull qwen3.5:7b
   
   For larger models (if you have the RAM):
   ollama pull qwen3.5:32b  # 32GB RAM recommended
   ollama pull qwen3.5:72b  # 64GB RAM recommended

3. Start Ollama:
   ollama serve
   
   (Or it may start automatically on macOS/Windows)

4. Test the connection:
   python -c "from local_config import check_model_available; check_model_available()"

5. Run VibeFactory:
   streamlit run app.py

System Requirements:
--------------------
- qwen3.5:7b  - 8GB RAM minimum, 16GB recommended
- qwen3.5:14b - 16GB RAM minimum, 32GB recommended
- qwen3.5:32b - 32GB RAM minimum, 64GB recommended
- qwen3.5:72b - 64GB RAM minimum, 128GB recommended

Note: Local models are completely free and private!
No API keys required. Runs entirely on your hardware.
"""

if __name__ == "__main__":
    print(SETUP_INSTRUCTIONS)
    
    # Try to setup
    if setup_local_environment():
        print("\n🧪 Checking model availability...")
        check_model_available()
    else:
        print("\n⚠️  Please start Ollama first")
