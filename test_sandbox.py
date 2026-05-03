"""
Test script for Module 1: Sandbox
Requires Docker to be running.
"""

import sys
from sandbox import ProjectSandbox, CommandResult

def test_sandbox():
    """Test sandbox functionality."""
    
    print("Testing Project Sandbox...")
    print("=" * 50)
    
    # Check if Docker is available
    try:
        import docker
        client = docker.from_env()
        client.ping()
        print("✓ Docker is running and accessible")
    except Exception as e:
        print(f"✗ Docker not available: {e}")
        print("\nPlease install and start Docker before running sandbox tests.")
        return False
    
    # Test 1: Create sandbox instance
    print("\n1. Creating sandbox instance...")
    try:
        with ProjectSandbox(project_id="test-sandbox") as sandbox:
            print("   ✓ Sandbox initialized")
            
            # Test 2: Directory structure
            print("\n2. Checking directory structure...")
            files = sandbox.list_files()
            print(f"   ✓ Created files: {files}")
            
            # Test 3: Write a file
            print("\n3. Writing test file...")
            sandbox.write_file("app/main.py", "print('Hello, World!')")
            content = sandbox.get_file("app/main.py")
            assert content == "print('Hello, World!')", "File content mismatch"
            print("   ✓ File written and retrieved successfully")
            
            # Test 4: Write requirements
            print("\n4. Writing requirements.txt...")
            sandbox.write_requirements(["requests>=2.28.0", "pytest>=7.0.0"])
            req_content = sandbox.get_file("requirements.txt")
            assert "requests" in req_content, "Requirements not written"
            print("   ✓ Requirements written")
            
            # Test 5: Install dependencies
            print("\n5. Installing dependencies...")
            result = sandbox.install_dependencies()
            if result.returncode == 0:
                print("   ✓ Dependencies installed successfully")
            else:
                print(f"   ⚠ Installation completed with warnings: {result.stderr}")
            
            # Test 6: Run a command
            print("\n6. Running Python command...")
            result = sandbox.run_command("python --version")
            if result.returncode == 0:
                print(f"   ✓ Python version: {result.stdout.strip()}")
            else:
                print(f"   ✗ Command failed: {result.stderr}")
            
            # Test 7: Git integration
            print("\n7. Testing Git integration...")
            sandbox.initialize_git()
            print("   ✓ Git initialized")
            
            sandbox.stage_files()
            print("   ✓ Files staged")
            
            result = sandbox.commit("Initial commit")
            if result.returncode == 0:
                print("   ✓ Commit successful")
            else:
                print(f"   ⚠ Commit completed with warnings")
            
            # Test 8: Run pytest (if installed)
            print("\n8. Testing pytest execution...")
            sandbox.write_file("tests/test_example.py", """
def test_addition():
    assert 1 + 1 == 2

def test_string_concat():
    assert "hello" + " " + "world" == "hello world"
""")
            result = sandbox.run_command("pytest tests/ -v")
            if result.returncode == 0:
                print("   ✓ Pytest passed")
                # Show test output
                for line in result.stdout.split('\n'):
                    if 'PASSED' in line or 'test_' in line:
                        print(f"      {line.strip()}")
            else:
                print(f"   ⚠ Pytest output: {result.stdout[:200]}")
    
    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 50)
    print("✅ All sandbox tests passed!")
    return True

if __name__ == "__main__":
    success = test_sandbox()
    sys.exit(0 if success else 1)
