"""Python Code Execution Sandbox — Runs generated snippets in an isolated Docker container."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Predefined set of Python standard library modules to avoid pip installing them
_STD_LIBS = {
    "os", "sys", "math", "time", "re", "json", "collections", "itertools", "typing",
    "asyncio", "datetime", "random", "logging", "hashlib", "io", "copy", "functools",
    "pathlib", "abc", "subprocess", "shutil", "tempfile", "traceback", "inspect", "enum",
    "ctypes", "select", "socket", "struct", "thread", "threading", "queue", "csv", "xml",
    "html", "urllib", "http", "ftplib", "smtplib", "email", "sqlite3", "uuid", "decimal",
    "fractions", "numbers", "platform", "unittest", "mock", "pprint", "warnings"
}


def extract_imports(code: str) -> list[str]:
    """Parse imports from python code block and extract top-level module names."""
    imports = []
    
    # Match "import x, y, z" or "import x"
    import_matches = re.findall(r"^\s*import\s+([a-zA-Z0-9_, ]+)", code, re.MULTILINE)
    for match in import_matches:
        for name in match.split(","):
            # Strip "as alias" if present
            name_clean = re.split(r"\s+as\s+", name, flags=re.IGNORECASE)[0].strip()
            parts = name_clean.split(".")
            if parts:
                imports.append(parts[0].strip())
                
    # Match "from x import y"
    from_matches = re.findall(r"^\s*from\s+([a-zA-Z0-9_.]+)\s+import", code, re.MULTILINE)
    for match in from_matches:
        parts = match.strip().split(".")
        if parts:
            imports.append(parts[0].strip())
            
    # Filter out empty entries and standard libraries
    filtered = []
    for imp in set(imports):
        if imp and imp.lower() not in _STD_LIBS:
            filtered.append(imp)
            
    return sorted(filtered)


async def run_code_in_sandbox(code: str, timeout_seconds: float = 30.0) -> dict[str, Any]:
    """Execute Python code in an isolated Docker container and return stdout/stderr.

    Automatically extracts imports, installs required dependencies inside the container,
    and runs the script.

    Parameters
    ----------
    code : str
        The raw Python code string to test.
    timeout_seconds : float
        Maximum allowed duration before terminating execution.
    """
    logger.info("Sandbox: starting isolated Docker execution test")

    # 1. Parse imports and determine required external packages
    libs = extract_imports(code)
    
    # 2. Build the command to install packages (if any) and execute Python
    if libs:
        libs_str = " ".join(libs)
        logger.info("Sandbox: identified external requirements to install -> %s", libs_str)
        # Run pip install first, then python
        docker_cmd = f"pip install --no-cache-dir -q {libs_str} && python"
    else:
        logger.info("Sandbox: no external requirements detected")
        docker_cmd = "python"

    try:
        # Start docker subprocess
        # We run bash inside python:3.12-slim and pass the install and run script
        proc = await asyncio.create_subprocess_exec(
            "docker",
            "run",
            "--rm",
            "-i",
            "python:3.12-slim",
            "bash",
            "-c",
            docker_cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            # Send python code to stdin and wait for completion
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(input=code.encode("utf-8")),
                timeout=timeout_seconds
            )
            exit_code = proc.returncode
        except asyncio.TimeoutError:
            logger.warning("Sandbox: code execution timed out. Terminating docker process.")
            try:
                proc.kill()
            except Exception:
                pass
            stdout_bytes, stderr_bytes = await proc.communicate()
            exit_code = -1
            return {
                "success": False,
                "stdout": stdout_bytes.decode("utf-8", errors="replace"),
                "stderr": f"Error: Code execution timed out after {timeout_seconds} seconds in Docker sandbox.",
                "exit_code": exit_code,
            }

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        
        # If pip fails, that output is written to stderr.
        # Check exit_code for absolute status.
        success = (exit_code == 0)

        logger.info("Sandbox finished: success=%s  exit_code=%d", success, exit_code)
        return {
            "success": success,
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": exit_code,
        }

    except Exception as e:
        logger.exception("Sandbox: failed to run docker subprocess")
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Docker Sandbox execution failed to start: {e}",
            "exit_code": -1,
        }
