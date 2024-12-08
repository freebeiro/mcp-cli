# transport/stdio/stdio_server_parameters.py
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional
import os
from dataclasses import dataclass
from typing import Optional, List, Dict

@dataclass
class StdioServerParameters:
    """Parameters for launching a stdio-based server."""
    command: str
    args: List[str]
    env: Optional[Dict[str, str]] = None

def get_default_environment() -> Dict[str, str]:
    """Get default environment variables for server processes."""
    env = dict(os.environ)
    env["PYTHONUNBUFFERED"] = "1"  # Ensure Python output is unbuffered
    return env