from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

class ToolParameter(BaseModel):
    """Represents a parameter for a tool"""
    name: str
    description: str
    type: str
    required: bool = True
    default: Optional[Any] = None
    enum: Optional[List[Any]] = None
    items: Optional[Dict[str, Any]] = None  # For array types

class ToolSchema(BaseModel):
    """Represents a tool's schema"""
    name: str
    description: str
    parameters: List[ToolParameter]
    returns: Dict[str, Any]  # JSON Schema for return value
    server_name: str  # Which server provides this tool
    version: str = "1.0.0"
    tags: List[str] = []

class ToolRegistry(BaseModel):
    """Registry of all available tools"""
    tools: Dict[str, ToolSchema] = {}
    
    def register_tool(self, tool: ToolSchema):
        """Register a new tool"""
        self.tools[f"{tool.server_name}.{tool.name}"] = tool
    
    def get_tool(self, tool_id: str) -> Optional[ToolSchema]:
        """Get a tool by its ID"""
        return self.tools.get(tool_id)
    
    def get_server_tools(self, server_name: str) -> List[ToolSchema]:
        """Get all tools for a specific server"""
        return [
            tool for tool in self.tools.values()
            if tool.server_name == server_name
        ]
    
    def to_json_schema(self) -> Dict[str, Any]:
        """Convert registry to JSON Schema format"""
        return {
            "type": "object",
            "properties": {
                tool_id: {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "const": tool.name},
                        "description": {"type": "string", "const": tool.description},
                        "parameters": {
                            "type": "object",
                            "properties": {
                                param.name: {
                                    "type": param.type,
                                    "description": param.description,
                                    **({"enum": param.enum} if param.enum else {}),
                                    **({"default": param.default} if param.default is not None else {}),
                                    **({"items": param.items} if param.items else {})
                                }
                                for param in tool.parameters
                            },
                            "required": [
                                param.name for param in tool.parameters
                                if param.required
                            ]
                        },
                        "returns": tool.returns
                    }
                }
                for tool_id, tool in self.tools.items()
            }
        }
