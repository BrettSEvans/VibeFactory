"""
OpenRouter Configuration for VibeFactory
Configure the system to use OpenRouter with Llama 3.3-70B
"""

import os
from typing import Optional

# OpenRouter API Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# Default model for OpenRouter
DEFAULT_MODEL = "openrouter/meta-llama/llama-3.3-70b-instruct:free"

# Alternative models available on OpenRouter:
# - meta-llama/llama-3.1-405b-instruct:free (405B - more capable)
# - meta-llama/llama-3.1-8b-instruct:free (8B - faster)
# - mistralai/mistral-nemo:free (12B - good balance)
# - google/gemma-7b-it:free (7B - lightweight)

def setup_openrouter_environment():
    """
    Set up OpenRouter environment variables.
    Call this before initializing any agents.
    """
    if not OPENROUTER_API_KEY:
        print("⚠️  WARNING: OPENROUTER_API_KEY not set!")
        print("   Get your API key from: https://openrouter.ai/keys")
        print("   Set it with: export OPENROUTER_API_KEY='your-key-here'")
        return False
    
    # Set the API key for litellm
    os.environ["OPENROUTER_API_KEY"] = OPENROUTER_API_KEY
    
    # Configure litellm to use OpenRouter
    os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "False"
    os.environ["LITELLM_LOG"] = "WARNING"
    
    print("✅ OpenRouter configured successfully!")
    print(f"   Model: {DEFAULT_MODEL}")
    print(f"   API Key: {'Set' if OPENROUTER_API_KEY else 'Not set'}")
    
    return True

def get_openrouter_config():
    """
    Get OpenRouter configuration for agents.
    
    Returns:
        dict: Configuration dictionary for orchestrator and engineer
    """
    return {
        "llm_model": DEFAULT_MODEL,
        "api_key": OPENROUTER_API_KEY,
        "max_retries": 3,
        "pass_score": 7,
        "worker_pool_size": 4
    }

def test_openrouter_connection():
    """
    Test if OpenRouter connection works.
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        import litellm
        from litellm import completion
        
        # Test completion
        response = completion(
            model=DEFAULT_MODEL,
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10,
            temperature=0.7
        )
        
        print("✅ OpenRouter connection test successful!")
        print(f"   Response: {response.choices[0].message.content}")
        return True
        
    except Exception as e:
        print(f"❌ OpenRouter connection test failed: {e}")
        return False

# Quick setup instructions
SETUP_INSTRUCTIONS = """
🚀 OpenRouter Setup Instructions
==================================

1. Get your API key:
   - Go to https://openrouter.ai/keys
   - Sign up / Log in
   - Create a new API key
   - Copy the key

2. Set the environment variable:
   export OPENROUTER_API_KEY='your-api-key-here'

3. Test the connection:
   python -c "from openrouter_config import test_openrouter_connection; test_openrouter_connection()"

4. Run VibeFactory:
   streamlit run app.py

Available Models on OpenRouter:
-------------------------------
- meta-llama/llama-3.3-70b-instruct:free (70B - Recommended)
- meta-llama/llama-3.1-405b-instruct:free (405B - Most capable)
- meta-llama/llama-3.1-8b-instruct:free (8B - Fastest)
- mistralai/mistral-nemo:free (12B - Good balance)
- google/gemma-7b-it:free (7B - Lightweight)

Note: Free tier models have rate limits. Check OpenRouter docs for details.
"""

if __name__ == "__main__":
    print(SETUP_INSTRUCTIONS)
    
    # Try to setup
    if setup_openrouter_environment():
        print("\n🧪 Testing connection...")
        test_openrouter_connection()
