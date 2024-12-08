from typing import Dict, List, Any, Optional
import json
import jsonschema
from llm_client import LLMClient
from rich.console import Console
import os

async def load_mcp_config():
    """Load and validate MCP configuration."""
    try:
        with open('server_config.json', 'r') as f:
            config_data = json.load(f)
        return MCPConfig(config_data)
    except Exception as e:
        raise RuntimeError(f"Failed to load MCP configuration: {str(e)}")

async def verify_mcp_compatibility(connection: Any) -> bool:
    """Verify if a server connection is MCP-compatible."""
    try:
        # Check for required MCP methods
        required_methods = ["get_tools", "execute_tool", "get_status"]
        for method in required_methods:
            if not hasattr(connection, method):
                return False
        
        # Verify protocol version
        status = await connection.get_status()
        if not status.get("mcp_version"):
            return False
            
        return True
    except Exception:
        return False

def validate_tool_schema(tool_schema: Dict) -> bool:
    """Validate a tool schema against MCP specification."""
    mcp_tool_schema = {
        "type": "object",
        "required": ["name", "description", "parameters"],
        "properties": {
            "name": {"type": "string"},
            "description": {"type": "string"},
            "parameters": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["name", "description", "type"],
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "type": {"type": "string"},
                        "required": {"type": "boolean"}
                    }
                }
            }
        }
    }
    
    try:
        jsonschema.validate(tool_schema, mcp_tool_schema)
        return True
    except jsonschema.exceptions.ValidationError:
        return False

def format_server_list(tools: Dict) -> str:
    """Format the list of servers and their tools."""
    server_tools = {}
    for tool_name, tool_info in tools.items():
        server_name = tool_info.get("server", "unknown")
        if server_name not in server_tools:
            server_tools[server_name] = []
        server_tools[server_name].append(tool_name)
    
    formatted_list = []
    for server, tool_list in server_tools.items():
        formatted_list.append(f"- {server}:")
        for tool in tool_list:
            formatted_list.append(f"  - {tool}")
    
    return "\n".join(formatted_list)

def categorize_mcp_tools(tools: Dict) -> str:
    """Categorize tools by their functionality."""
    categories = {
        "file_operations": [],
        "database": [],
        "git": [],
        "utility": []
    }
    
    for tool_name, tool_info in tools.items():
        category = determine_tool_category(tool_info)
        categories[category].append(tool_name)
    
    formatted_categories = []
    for category, tools in categories.items():
        if tools:
            formatted_categories.append(f"- {category.replace('_', ' ').title()}:")
            for tool in tools:
                formatted_categories.append(f"  - {tool}")
    
    return "\n".join(formatted_categories)

def determine_tool_category(tool_info: Dict) -> str:
    """Determine the category of a tool based on its properties."""
    name = tool_info.get("name", "").lower()
    description = tool_info.get("description", "").lower()
    
    if any(kw in name or kw in description for kw in ["file", "read", "write", "directory"]):
        return "file_operations"
    elif any(kw in name or kw in description for kw in ["sql", "database", "query"]):
        return "database"
    elif any(kw in name or kw in description for kw in ["git", "commit", "pull", "push"]):
        return "git"
    else:
        return "utility" 

def create_mcp_aware_llm(tools: Dict[str, Any]) -> LLMClient:
    """Create an LLM client with MCP tool awareness."""
    return LLMClient(
        provider=os.getenv("LLM_PROVIDER", "ollama"),
        model=os.getenv("LLM_MODEL", "llama3.2"),
        tools=tools,
        mcp_compatible=True,
        timeout=int(os.getenv("LLM_TIMEOUT", "30"))
    )

async def handle_mcp_tool_calls(
    tool_calls: List[Dict],
    messages: List[Dict],
    server_manager: Any,
    console: Console
):
    """Handle MCP tool calls with proper routing."""
    for tool_call in tool_calls:
        try:
            # Extract server info from tool metadata
            server_name = tool_call.get("mcp_metadata", {}).get("server")
            if not server_name:
                raise ValueError("No server specified for tool call")

            # Get server connection
            server = server_manager.get_server(server_name)
            if not server:
                raise ValueError(f"Server {server_name} not found")

            # Execute tool
            result = await server.execute_tool(
                tool_call["function"]["name"],
                json.loads(tool_call["function"]["arguments"])
            )

            # Add result to conversation
            messages.append({
                "role": "tool",
                "content": str(result),
                "tool_call_id": tool_call["id"]
            })

        except Exception as e:
            error_msg = f"Tool execution error: {str(e)}"
            console.print(f"[red]{error_msg}[/red]")
            messages.append({
                "role": "system",
                "content": error_msg
            }) 