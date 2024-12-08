from typing import Dict, List, Optional
import asyncio
import logging
from messages.json_rpc_message import JSONRPCMessage
from server_manager import ServerManager, ServerConnection
from .tool_schema import ToolRegistry, ToolSchema, ToolParameter

logger = logging.getLogger(__name__)

class ToolDiscovery:
    """Discovers and manages tools from multiple servers"""
    
    def __init__(self, server_manager: ServerManager):
        self.server_manager = server_manager
        self.registry = ToolRegistry()
        
    async def discover_server_tools(self, server_name: str) -> List[ToolSchema]:
        """Discover tools from a specific server"""
        connection = self.server_manager.get_connection(server_name)
        if not connection:
            logger.warning(f"Server {server_name} not connected")
            return []
            
        try:
            # Send tool discovery request
            discovery_msg = JSONRPCMessage(
                method="discover_tools",
                id="tool_discovery"
            )
            
            await connection.write_stream.asend(discovery_msg.dict())
            
            # Wait for response
            async for message in connection.read_stream:
                if isinstance(message, dict) and message.get("id") == "tool_discovery":
                    tools_data = message.get("result", {}).get("tools", [])
                    tools = []
                    
                    for tool_data in tools_data:
                        # Convert parameters to ToolParameter objects
                        parameters = [
                            ToolParameter(
                                name=param["name"],
                                description=param["description"],
                                type=param["type"],
                                required=param.get("required", True),
                                default=param.get("default"),
                                enum=param.get("enum"),
                                items=param.get("items")
                            )
                            for param in tool_data.get("parameters", [])
                        ]
                        
                        # Create ToolSchema
                        tool = ToolSchema(
                            name=tool_data["name"],
                            description=tool_data["description"],
                            parameters=parameters,
                            returns=tool_data["returns"],
                            server_name=server_name,
                            version=tool_data.get("version", "1.0.0"),
                            tags=tool_data.get("tags", [])
                        )
                        
                        tools.append(tool)
                        self.registry.register_tool(tool)
                    
                    return tools
                    
        except Exception as e:
            logger.error(f"Error discovering tools from {server_name}: {str(e)}")
            return []
    
    async def discover_all_tools(self) -> Dict[str, List[ToolSchema]]:
        """Discover tools from all connected servers"""
        results = {}
        for server_name in self.server_manager.connections:
            tools = await self.discover_server_tools(server_name)
            results[server_name] = tools
        return results
    
    def get_tool_schema(self, tool_id: str) -> Optional[ToolSchema]:
        """Get schema for a specific tool"""
        return self.registry.get_tool(tool_id)
    
    def get_server_tools(self, server_name: str) -> List[ToolSchema]:
        """Get all tools for a specific server"""
        return self.registry.get_server_tools(server_name)
    
    def get_tools_by_tag(self, tag: str) -> List[ToolSchema]:
        """Get all tools with a specific tag"""
        return [
            tool for tool in self.registry.tools.values()
            if tag in tool.tags
        ]
    
    def to_json_schema(self) -> Dict:
        """Get complete tool registry as JSON Schema"""
        return self.registry.to_json_schema()
