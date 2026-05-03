#!/usr/bin/env python3
"""
VibeFactory Local Model Setup
Configures the system to use local Qwen3.5 model via Ollama
"""

import os
import sys
import subprocess

def check_ollama_installed():
    """Check if Ollama is installed."""
    try:
        result = subprocess.run(
            ["ollama", "--version"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"✅ Ollama is installed: {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        pass
    
    print("❌ Ollama not found!")
    print("\nTo install Ollama:")
    print("  macOS: brew install ollama")
    print("  Linux: curl -fsSL https://ollama.ai/install.sh | sh")
    print("  Windows: Download from https://ollama.ai")
    return False

def check_ollama_running():
    """Check if Ollama is running."""
    import urllib.request
    
    try:
        response = urllib.request.urlopen("http://localhost:11434/api/tags", timeout=5)
        if response.status == 200:
            print("✅ Ollama is running!")
            return True
    except Exception as e:
        print(f"⚠️  Ollama doesn't appear to be running")
        print("   Start it with: ollama serve")
        print("   Or on macOS/Windows, it may start automatically")
        return False
    
    return False

def pull_model(model_name="qwen3.5:7b"):
    """Pull the model using Ollama."""
    print(f"\n📥 Pulling model: {model_name}")
    print("   This may take several minutes...")
    
    try:
        result = subprocess.run(
            ["ollama", "pull", model_name],
            capture_output=False,
            text=True
        )
        
        if result.returncode == 0:
            print(f"✅ Model '{model_name}' installed successfully!")
            return True
        else:
            print(f"❌ Failed to pull model")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def check_model_available(model_name="qwen3.5:7b"):
    """Check if model is available."""
    import urllib.request
    import json
    
    try:
        response = urllib.request.urlopen("http://localhost:11434/api/tags", timeout=5)
        data = json.loads(response.read().decode())
        
        models = [m["name"] for m in data.get("models", [])]
        
        if model_name in models:
            print(f"✅ Model '{model_name}' is available!")
            return True
        else:
            print(f"⚠️  Model '{model_name}' not found!")
            print(f"   Available models: {', '.join(models[:5])}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def update_config_files():
    """Update configuration files to use local model."""
    print("\n🔧 Updating configuration files...")
    
    # Update orchestrator.py
    try:
        with open("orchestrator.py", "r") as f:
            content = f.read()
        
        # Update default model
        content = content.replace(
            'default="meta-llama/llama-3.3-70b-instruct:free"',
            'default="qwen3.5:7b"'
        )
        
        with open("orchestrator.py", "w") as f:
            f.write(content)
        
        print("  ✅ Updated orchestrator.py")
    except Exception as e:
        print(f"  ⚠️  Could not update orchestrator.py: {e}")
    
    # Update engineer.py
    try:
        with open("engineer.py", "r") as f:
            content = f.read()
        
        # Update default model
        content = content.replace(
            'default="meta-llama/llama-3.3-70b-instruct:free"',
            'default="qwen3.5:7b"'
        )
        
        with open("engineer.py", "w") as f:
            f.write(content)
        
        print("  ✅ Updated engineer.py")
    except Exception as e:
        print(f"  ⚠️  Could not update engineer.py: {e}")
    
    print("  ✅ Configuration updated!")

def main():
    """Main setup function."""
    print("=" * 60)
    print("🚀 VibeFactory - Local Model Setup (Qwen3.5)")
    print("=" * 60)
    print()
    
    # Check Ollama installation
    if not check_ollama_installed():
        print("\n❌ Please install Ollama first, then run this script again.")
        return False
    
    # Check if running
    if not check_ollama_running():
        print("\n⚠️  Please start Ollama first:")
        print("   ollama serve")
        print("   (Or restart the Ollama application)")
        return False
    
    # Pull model
    model_name = "qwen3.5:7b"
    if not check_model_available(model_name):
        if not pull_model(model_name):
            print("\n❌ Failed to pull model")
            return False
    
    # Update config
    update_config_files()
    
    # Test
    print("\n🧪 Testing local model...")
    try:
        import litellm
        from litellm import completion
        
        response = completion(
            model=f"ollama/{model_name}",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=20,
            temperature=0.7
        )
        
        print("✅ Local model test successful!")
        print(f"   Response: {response.choices[0].message.content}")
        
    except Exception as e:
        print(f"⚠️  Test failed (may need configuration): {e}")
    
    print("\n" + "=" * 60)
    print("✅ Setup complete! You're ready to use local Qwen3.5!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  1. Run the UI: streamlit run app.py")
    print("  2. Enter your project idea")
    print("  3. Watch AI agents build your software (locally!)")
    print()
    print("💡 Tip: For better quality, try larger models:")
    print("   ollama pull qwen3.5:32b  # Requires 32GB+ RAM")
    print("   ollama pull qwen3.5:72b  # Requires 64GB+ RAM")
    print()
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
