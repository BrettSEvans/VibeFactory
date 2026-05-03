#!/usr/bin/env python3
"""
VibeFactory Setup Script
Configures the system to use OpenRouter with Llama 3.3-70B
"""

import os
import sys

def setup_openrouter():
    """Setup OpenRouter configuration."""
    
    print("=" * 60)
    print("🚀 VibeFactory - OpenRouter Setup")
    print("=" * 60)
    print()
    
    # Check if API key is set
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    if not api_key:
        print("⚠️  OpenRouter API Key not found!")
        print()
        print("To get your API key:")
        print("  1. Go to: https://openrouter.ai/keys")
        print("  2. Sign up / Log in")
        print("  3. Create a new API key")
        print("  4. Copy the key")
        print()
        print("Then set it with:")
        print("  export OPENROUTER_API_KEY='your-api-key-here'")
        print()
        
        # Ask if user wants to set it now
        response = input("Do you want to set it now? (y/n): ").strip().lower()
        
        if response == 'y':
            api_key = input("Enter your OpenRouter API key: ").strip()
            
            if api_key:
                # Set in current environment
                os.environ["OPENROUTER_API_KEY"] = api_key
                
                # Ask to save to .env file
                save_response = input("Save to .env file for future use? (y/n): ").strip().lower()
                
                if save_response == 'y':
                    save_api_key_to_env(api_key)
                    print("✅ API key saved to .env file")
            else:
                print("❌ No API key provided")
                return False
        else:
            print("❌ Setup cancelled")
            return False
    else:
        print("✅ OpenRouter API key found!")
    
    print()
    print("📋 Configuration:")
    print(f"   Model: meta-llama/llama-3.3-70b-instruct:free")
    print(f"   API Key: {'✓ Set' if api_key else '✗ Not set'}")
    print()
    
    # Test connection
    print("🧪 Testing OpenRouter connection...")
    try:
        import litellm
        from litellm import completion
        
        response = completion(
            model="meta-llama/llama-3.3-70b-instruct:free",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10,
            temperature=0.7
        )
        
        print("✅ Connection successful!")
        print(f"   Response: {response.choices[0].message.content}")
        print()
        
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        print()
        print("Troubleshooting:")
        print("  - Check your API key is correct")
        print("  - Check your internet connection")
        print("  - Verify you have credits on OpenRouter (free tier has limits)")
        print()
        return False
    
    print("=" * 60)
    print("✅ Setup complete! You're ready to use VibeFactory!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  1. Run the UI: streamlit run app.py")
    print("  2. Enter your project idea")
    print("  3. Watch AI agents build your software!")
    print()
    
    return True

def save_api_key_to_env(api_key):
    """Save API key to .env file."""
    env_file = ".env"
    
    # Check if .env exists
    if os.path.exists(env_file):
        # Read existing content
        with open(env_file, 'r') as f:
            content = f.read()
        
        # Check if OPENROUTER_API_KEY already exists
        if "OPENROUTER_API_KEY=" in content:
            # Replace existing key
            import re
            content = re.sub(
                r'OPENROUTER_API_KEY=.*',
                f'OPENROUTER_API_KEY={api_key}',
                content
            )
        else:
            # Add new key
            content += f"\nOPENROUTER_API_KEY={api_key}\n"
    else:
        # Create new file
        content = f"OPENROUTER_API_KEY={api_key}\n"
    
    # Write to file
    with open(env_file, 'w') as f:
        f.write(content)

def main():
    """Main setup function."""
    success = setup_openrouter()
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
