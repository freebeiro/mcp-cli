from typing import Dict, Any, AsyncGenerator, Optional, List
import os
import json
import logging
from pathlib import Path
from pydantic import BaseModel
from mcp_cli.messages.json_rpc_message import JSONRPCMessage
from mcp_cli.tools.tool_schema import ToolSchema, ToolParameter
import fnmatch

logger = logging.getLogger(__name__)

class MessageHandler:
    """Helper class to handle messages as an async context manager"""
    def __init__(self, gen: AsyncGenerator[Dict[str, Any], None]):
        self.gen = gen

    async def __aenter__(self) -> AsyncGenerator[Dict[str, Any], None]:
        return self.gen

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            await self.gen.aclose()
        except Exception as e:
            logger.error(f"Error closing generator: {str(e)}")

class FilesystemConfig(BaseModel):
    """Configuration for Filesystem server"""
    root_paths: List[str]  # List of root paths to search/operate in
    max_file_size: int = 10 * 1024 * 1024  # 10MB default max file size
    allowed_extensions: List[str] = ["*"]  # List of allowed file extensions, * for all

class FilesystemServer:
    """MCP-compatible Filesystem server implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = FilesystemConfig(**config)
        self._init_tools()
        
    def _init_tools(self) -> None:
        """Initialize available tools"""
        self.tools = {
            "search": ToolSchema(
                name="search",
                description="Search for files in configured directories",
                parameters=[
                    ToolParameter(
                        name="query",
                        description="Search query (glob pattern)",
                        type="string",
                        required=True
                    ),
                    ToolParameter(
                        name="max_results",
                        description="Maximum number of results",
                        type="integer",
                        required=False,
                        default=100
                    )
                ],
                returns={
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "size": {"type": "integer"},
                            "modified": {"type": "string"}
                        }
                    }
                },
                server_name="filesystem"
            ),
            "read": ToolSchema(
                name="read",
                description="Read contents of a file",
                parameters=[
                    ToolParameter(
                        name="path",
                        description="Path to file",
                        type="string",
                        required=True
                    ),
                    ToolParameter(
                        name="start_line",
                        description="Start line number (0-based)",
                        type="integer",
                        required=False,
                        default=0
                    ),
                    ToolParameter(
                        name="end_line",
                        description="End line number (0-based)",
                        type="integer",
                        required=False
                    )
                ],
                returns={
                    "type": "object",
                    "properties": {
                        "content": {"type": "string"},
                        "total_lines": {"type": "integer"},
                        "read_lines": {
                            "type": "object",
                            "properties": {
                                "start": {"type": "integer"},
                                "end": {"type": "integer"}
                            }
                        }
                    }
                },
                server_name="filesystem"
            ),
            "write": ToolSchema(
                name="write",
                description="Write content to a file",
                parameters=[
                    ToolParameter(
                        name="path",
                        description="Path to file",
                        type="string",
                        required=True
                    ),
                    ToolParameter(
                        name="content",
                        description="Content to write",
                        type="string",
                        required=True
                    ),
                    ToolParameter(
                        name="append",
                        description="Append to file instead of overwriting",
                        type="boolean",
                        required=False,
                        default=False
                    )
                ],
                returns={
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "bytes_written": {"type": "integer"}
                    }
                },
                server_name="filesystem"
            )
        }
    
    async def handle_message(self, message: Dict[str, Any]) -> MessageHandler:
        """Handle incoming JSON-RPC messages"""
        async def message_handler() -> AsyncGenerator[Dict[str, Any], None]:
            try:
                msg = JSONRPCMessage(**message)
                
                if msg.method == "discover_tools":
                    yield {
                        "jsonrpc": "2.0",
                        "id": msg.id,
                        "result": {
                            "tools": [tool.model_dump() for tool in self.tools.values()]
                        }
                    }
                    return
                    
                if msg.method in self.tools:
                    tool = self.tools[msg.method]
                    params = msg.params or {}
                    
                    if msg.method == "search":
                        result = await self._handle_search(params)
                        yield {
                            "jsonrpc": "2.0",
                            "id": msg.id,
                            "result": result
                        }
                        
                    elif msg.method == "read":
                        result = await self._handle_read(params)
                        yield {
                            "jsonrpc": "2.0",
                            "id": msg.id,
                            "result": result
                        }
                        
                    elif msg.method == "write":
                        result = await self._handle_write(params)
                        yield {
                            "jsonrpc": "2.0",
                            "id": msg.id,
                            "result": result
                        }
                else:
                    yield {
                        "jsonrpc": "2.0",
                        "id": msg.id,
                        "error": {
                            "code": -32601,
                            "message": f"Method {msg.method} not found"
                        }
                    }
                    
            except Exception as e:
                logger.error(f"Error handling message: {str(e)}")
                yield {
                    "jsonrpc": "2.0",
                    "id": msg.id if 'msg' in locals() else None,
                    "error": {
                        "code": -32000,
                        "message": str(e)
                    }
                }
                
        return MessageHandler(message_handler())
    
    async def _handle_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle search requests"""
        query = params["query"]
        max_results = params.get("max_results", 100)
        results = []
        
        for root_path in self.config.root_paths:
            root = Path(root_path)
            if not root.exists():
                continue
                
            for path in root.rglob(query):
                if not path.is_file():
                    continue
                    
                # Check file extension
                if "*" not in self.config.allowed_extensions:
                    if path.suffix[1:] not in self.config.allowed_extensions:
                        continue
                
                # Check file size
                size = path.stat().st_size
                if size > self.config.max_file_size:
                    continue
                    
                results.append({
                    "path": str(path.relative_to(root)),
                    "size": size,
                    "modified": path.stat().st_mtime
                })
                
                if len(results) >= max_results:
                    break
                    
        return results
        
    async def _handle_read(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle read requests"""
        file_path = params["path"]
        start_line = params.get("start_line", 0)
        end_line = params.get("end_line")
        
        # Find the actual file in root paths
        actual_path = None
        for root_path in self.config.root_paths:
            test_path = Path(root_path) / file_path
            if test_path.exists() and test_path.is_file():
                actual_path = test_path
                break
                
        if not actual_path:
            raise FileNotFoundError(f"File not found: {file_path}")
            
        # Check file size
        if actual_path.stat().st_size > self.config.max_file_size:
            raise ValueError(f"File too large: {file_path}")
            
        with open(actual_path, 'r') as f:
            lines = f.readlines()
            total_lines = len(lines)
            
            if end_line is None:
                end_line = total_lines
                
            content = ''.join(lines[start_line:end_line])
            
            return {
                "content": content,
                "total_lines": total_lines,
                "read_lines": {
                    "start": start_line,
                    "end": min(end_line, total_lines)
                }
            }
            
    async def _handle_write(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle write requests"""
        file_path = params["path"]
        content = params["content"]
        append = params.get("append", False)
        
        # Find writable path in root paths
        write_path = None
        for root_path in self.config.root_paths:
            test_path = Path(root_path) / file_path
            try:
                # Create parent directories if they don't exist
                test_path.parent.mkdir(parents=True, exist_ok=True)
                # Check if we can write to this location
                if not test_path.exists() or os.access(test_path, os.W_OK):
                    write_path = test_path
                    break
            except Exception:
                continue
                
        if not write_path:
            raise PermissionError(f"Cannot write to file: {file_path}")
            
        mode = 'a' if append else 'w'
        with open(write_path, mode) as f:
            bytes_written = f.write(content)
            
        return {
            "success": True,
            "bytes_written": bytes_written
        }
        
    async def close(self):
        """Clean up resources"""
        # Nothing to clean up for filesystem server
        pass

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        pass

    def discover_tools(self) -> Dict[str, ToolSchema]:
        """Return available tools"""
        return self.tools
