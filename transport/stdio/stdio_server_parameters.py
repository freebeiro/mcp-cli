# transport/stdio/stdio_server_parameters.py
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional

class StdioServerParameters(BaseModel):
    command: str
    args: list[str] = Field(default_factory=list)
    env: Optional[Dict[str, str]] = None

def get_default_environment() -> Dict[str, str]:
    """Get the default environment variables for server processes."""
    return {
        "PYTHONUNBUFFERED": "1",  # Ensure Python output is unbuffered
        "NODE_NO_WARNINGS": "1",   # Suppress Node.js warnings
        "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"  # Basic PATH
    }