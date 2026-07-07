import os
import sys
import shutil
import subprocess
from pathlib import Path

class SandboxManager:
    """
    Manages isolated sandbox directories for task execution.
    Handles copying target repositories, running test commands,
    and resetting files to ground truth between runs.
    """
    def __init__(self, original_repo_path: str, sandbox_parent_dir: str = None):
        self.original_repo_path = os.path.abspath(original_repo_path)
        
        if not os.path.isdir(self.original_repo_path):
            raise ValueError(f"Original repository path '{self.original_repo_path}' is not a valid directory.")
            
        # Resolve sandbox parent directory (default to .sandbox under project root)
        if sandbox_parent_dir is None:
            current_file = Path(__file__).resolve()
            project_root = current_file.parent.parent.parent
            sandbox_parent_dir = os.path.join(project_root, ".sandbox")
            
        self.sandbox_parent_dir = os.path.abspath(sandbox_parent_dir)
        os.makedirs(self.sandbox_parent_dir, exist_ok=True)
        
        # Unique sandbox path for this repo
        repo_name = os.path.basename(self.original_repo_path)
        self.sandbox_path = os.path.join(self.sandbox_parent_dir, f"{repo_name}_sandbox")
        
    def setup_sandbox(self) -> str:
        """
        Deletes existing sandbox folder and copies the original repository fresh.
        Returns the path to the sandboxed repository.
        """
        self.cleanup_sandbox()
        
        # Custom copytree to ignore node_modules, .git, and venv to keep copies extremely fast
        def ignore_patterns(path, names):
            ignored = []
            for name in names:
                if name in (".git", "node_modules", "dist", "build", ".venv", "venv", ".semantic_cache"):
                    ignored.append(name)
            return ignored
            
        shutil.copytree(
            self.original_repo_path,
            self.sandbox_path,
            ignore=ignore_patterns,
            dirs_exist_ok=True
        )
        
        return self.sandbox_path
        
    def reset_sandbox(self) -> str:
        """
        Resets the sandbox to a clean state by performing a fresh setup.
        """
        return self.setup_sandbox()
        
    def cleanup_sandbox(self):
        """
        Removes the sandbox folder from disk.
        """
        if os.path.exists(self.sandbox_path):
            # Workaround for read-only files on Windows
            def onerror(func, path, exc_info):
                import stat
                if not os.access(path, os.W_OK):
                    os.chmod(path, stat.S_IWUSR)
                    func(path)
                else:
                    raise exc_info[1]
            shutil.rmtree(self.sandbox_path, onerror=onerror)
            
    def run_command(self, command: str, timeout: int = 60) -> dict:
        """
        Runs a shell command inside the sandboxed repository.
        Returns a dictionary with:
            - passed: bool
            - exit_code: int
            - stdout: str
            - stderr: str
            - timeout_expired: bool
        """
        if not os.path.exists(self.sandbox_path):
            self.setup_sandbox()
            
        try:
            # Set PYTHONIOENCODING to utf-8 for Windows compatibility
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            
            # Use shell=True for running npm / arbitrary commands on Windows
            result = subprocess.run(
                command,
                cwd=self.sandbox_path,
                shell=True,
                capture_output=True,
                text=True,
                env=env,
                timeout=timeout
            )
            
            return {
                "passed": result.returncode == 0,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "timeout_expired": False
            }
            
        except subprocess.TimeoutExpired as e:
            return {
                "passed": False,
                "exit_code": -1,
                "stdout": e.stdout if e.stdout else "",
                "stderr": e.stderr if e.stderr else f"Timeout expired after {timeout}s",
                "timeout_expired": True
            }
        except Exception as e:
            return {
                "passed": False,
                "exit_code": -2,
                "stdout": "",
                "stderr": str(e),
                "timeout_expired": False
            }
