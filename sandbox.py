"""
Module 1: Project Sandbox
Docker-based execution environment for safe code testing.
"""

import os
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import docker
from docker.errors import DockerException, NotFound, ImageNotFound, APIError


@dataclass
class CommandResult:
    """Result of a command execution in the sandbox."""
    stdout: str
    stderr: str
    returncode: int


class ProjectSandbox:
    """
    Manages a Docker-based sandbox environment for safe code execution.
    Provides isolated testing, dependency management, and git integration.
    """

    # Default Docker configuration
    DEFAULT_IMAGE = "python:3.11-slim"
    SANDBOX_NAME_PREFIX = "sdlc-sandbox"

    def __init__(self, project_id: str, image: str = None):
        """
        Initialize the sandbox.

        Args:
            project_id: Unique identifier for the project
            image: Docker image to use (defaults to python:3.11-slim)
        """
        self.project_id = project_id
        self.image = image or self.DEFAULT_IMAGE
        self.client = None
        self.container = None
        self.workspace_dir: Optional[str] = None
        self._initialized = False

    def initialize(self) -> None:
        """
        Initialize the Docker client and create the sandbox environment.
        Must be called before using other methods.
        """
        try:
            self.client = docker.from_env()
        except DockerException as e:
            raise RuntimeError(f"Failed to connect to Docker: {e}")

        # Create temporary workspace
        self.workspace_dir = tempfile.mkdtemp(
            prefix=f"{self.SANDBOX_NAME_PREFIX}-{self.project_id}-"
        )

        # Setup directory structure
        self._setup_directory_structure()

        # Create and start container
        self._create_container()

        self._initialized = True

    def _setup_directory_structure(self) -> None:
        """Create standard project directory structure."""
        if not self.workspace_dir:
            raise RuntimeError("Sandbox not initialized")

        # Create app/ directory
        app_dir = Path(self.workspace_dir) / "app"
        app_dir.mkdir(parents=True, exist_ok=True)

        # Create tests/ directory
        tests_dir = Path(self.workspace_dir) / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)

        # Create empty __init__.py files
        (app_dir / "__init__.py").touch()
        (tests_dir / "__init__.py").touch()

        # Create initial requirements.txt
        requirements_path = Path(self.workspace_dir) / "requirements.txt"
        requirements_path.write_text("")

    def _create_container(self) -> None:
        """Create and start a Docker container for the sandbox."""
        if not self.client or not self.workspace_dir:
            raise RuntimeError("Sandbox not initialized")

        try:
            # Pull image if not available
            try:
                self.client.images.get(self.image)
            except ImageNotFound:
                self.client.images.pull(self.image)

            # Create container with resource limits and security constraints
            self.container = self.client.containers.run(
                self.image,
                command="tail -f /dev/null",  # Keep container running
                working_dir="/workspace",
                volumes={self.workspace_dir: {'bind': '/workspace', 'mode': 'rw'}},
                detach=True,
                name=f"{self.SANDBOX_NAME_PREFIX}-{self.project_id}",
                remove=True,
                # Security: resource limits
                mem_limit="512m",
                memswap_limit="512m",
                cpu_period=100000,
                cpu_quota=50000,  # 50% of one core
                pids_limit=100,
                # Security: network isolation
                network_mode="none",
                # Security: privilege restrictions
                security_opt=["no-new-privileges"],
                cap_drop=["ALL"],
            )

        except (DockerException, APIError) as e:
            self.cleanup()
            raise RuntimeError(f"Failed to create sandbox container: {e}")

    def write_requirements(self, dependencies: List[str]) -> None:
        """
        Write dependencies to requirements.txt.

        Args:
            dependencies: List of package names (e.g., ["pytest>=7.0.0", "requests"])
        """
        if not self._initialized:
            self.initialize()

        requirements_path = Path(self.workspace_dir) / "requirements.txt"
        requirements_path.write_text("\n".join(dependencies) + "\n" if dependencies else "")

    def install_dependencies(self) -> CommandResult:
        """
        Install dependencies from requirements.txt inside the container.

        Returns:
            CommandResult with stdout, stderr, and returncode
        """
        if not self.container:
            raise RuntimeError("Container not available")

        exec_result = self.container.exec_run(
            ["pip", "install", "-r", "requirements.txt"],
            workdir="/workspace",
            demux=True
        )

        stdout = (exec_result.output[0] or b"").decode('utf-8')
        stderr = (exec_result.output[1] or b"").decode('utf-8')

        return CommandResult(
            stdout=stdout,
            stderr=stderr,
            returncode=exec_result.exit_code
        )

    def run_command(
        self,
        command,
        workdir: str = "/workspace",
        timeout: int = 120
    ) -> CommandResult:
        """
        Execute a command inside the Docker container.

        Args:
            command: Command as string or list. If string, will be split by shlex.
            workdir: Working directory inside container
            timeout: Command timeout in seconds

        Returns:
            CommandResult with stdout, stderr, and returncode
        """
        if not self.container:
            raise RuntimeError("Container not available")

        # Convert string commands to list to avoid shell injection
        if isinstance(command, str):
            import shlex
            cmd_list = shlex.split(command)
        else:
            cmd_list = command

        try:
            exec_result = self.container.exec_run(
                cmd_list,
                workdir=workdir,
                timeout=timeout,
                demux=True
            )

            stdout = (exec_result.output[0] or b"").decode('utf-8')
            stderr = (exec_result.output[1] or b"").decode('utf-8')

            return CommandResult(
                stdout=stdout,
                stderr=stderr,
                returncode=exec_result.exit_code
            )
        except Exception as e:
            return CommandResult(
                stdout="",
                stderr=str(e),
                returncode=-1
            )

    def initialize_git(self) -> CommandResult:
        """
        Initialize a git repository in the sandbox workspace.

        Returns:
            CommandResult with stdout, stderr, and returncode
        """
        return self.run_command("git init")

    def stage_files(self, files: Optional[List[str]] = None) -> CommandResult:
        """
        Stage files for git commit.

        Args:
            files: List of specific files to stage (None for all files)

        Returns:
            CommandResult with stdout, stderr, and returncode
        """
        if files:
            return self.run_command(["git", "add"] + files)
        return self.run_command(["git", "add", "."])

    def commit(
        self,
        message: str,
        author_name: str = "SDLC Agent",
        author_email: str = "agent@sdlc.local"
    ) -> CommandResult:
        """
        Commit staged changes to git.

        Args:
            message: Commit message
            author_name: Author name for the commit
            author_email: Author email for the commit

        Returns:
            CommandResult with stdout, stderr, and returncode
        """
        # Configure git user
        self.run_command(["git", "config", "user.name", author_name])
        self.run_command(["git", "config", "user.email", author_email])

        # Commit
        return self.run_command(["git", "commit", "-m", message])

    def write_file(self, filepath: str, content: str) -> None:
        """
        Write content to a file in the sandbox workspace.

        Args:
            filepath: Relative path within workspace
            content: File content
        """
        if not self.workspace_dir:
            raise RuntimeError("Sandbox not initialized")

        full_path = (Path(self.workspace_dir) / filepath).resolve()
        workspace_resolve = Path(self.workspace_dir).resolve()

        # Security: prevent path traversal
        try:
            full_path.relative_to(workspace_resolve)
        except ValueError:
            raise ValueError(f"Path traversal attempt rejected: {filepath}")

        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)

    def get_file(self, filepath: str) -> Optional[str]:
        """
        Read content from a file in the sandbox workspace.

        Args:
            filepath: Relative path within workspace

        Returns:
            File content or None if file doesn't exist
        """
        if not self.workspace_dir:
            raise RuntimeError("Sandbox not initialized")

        full_path = (Path(self.workspace_dir) / filepath).resolve()
        workspace_resolve = Path(self.workspace_dir).resolve()

        # Security: prevent path traversal
        try:
            full_path.relative_to(workspace_resolve)
        except ValueError:
            raise ValueError(f"Path traversal attempt rejected: {filepath}")

        if full_path.exists():
            return full_path.read_text()
        return None

    def list_files(self, directory: str = "") -> List[str]:
        """
        List all files in a directory.

        Args:
            directory: Directory within workspace (default: root)

        Returns:
            List of file paths relative to workspace
        """
        if not self.workspace_dir:
            raise RuntimeError("Sandbox not initialized")

        full_path = Path(self.workspace_dir) / directory
        files = []
        for file_path in full_path.rglob("*"):
            if file_path.is_file():
                rel_path = file_path.relative_to(self.workspace_dir)
                files.append(str(rel_path))
        return files

    def cleanup(self) -> None:
        """Stop and remove the container, clean up workspace."""
        try:
            if self.container:
                self.container.stop()
                self.container.remove()
                self.container = None
        except Exception:
            pass

        try:
            if self.workspace_dir and os.path.exists(self.workspace_dir):
                shutil.rmtree(self.workspace_dir)
                self.workspace_dir = None
        except Exception:
            pass

        self._initialized = False

    def __enter__(self):
        """Context manager entry."""
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()

    def __del__(self):
        """Destructor to ensure cleanup."""
        if hasattr(self, '_initialized') and self._initialized:
            self.cleanup()
