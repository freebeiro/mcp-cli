from typing import Dict, List

def convert_to_mcp_compatible_tools(tools: Dict) -> List[Dict]:
    """Convert MCP tools to OpenAI-compatible format while preserving MCP metadata."""
    openai_tools = []
    
    for tool_name, tool_info in tools.items():
        openai_tool = {
            "type": "function",
            "function": {
                "name": tool_name,
                "description": tool_info["description"],
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            "mcp_metadata": {  # Preserve MCP-specific information
                "server": tool_info.get("server"),
                "version": tool_info.get("version"),
                "protocol": "mcp"
            }
        }
        
        # Convert parameters
        for param in tool_info["parameters"]:
            openai_tool["function"]["parameters"]["properties"][param["name"]] = {
                "type": param["type"],
                "description": param["description"]
            }
            if param.get("required", False):
                openai_tool["function"]["parameters"]["required"].append(param["name"])
        
        openai_tools.append(openai_tool)
    
    return openai_tools 