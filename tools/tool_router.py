from typing import Dict, Any, Optional
import logging
import asyncio
from messages.json_rpc_message import JSONRPCMessage
from server_manager import ServerManager
from .tool_discovery import ToolDiscovery
from .tool_schema import ToolSchema

logger = logging.getLogger(__name__)

class ToolRouter:
    """Routes tool calls to appropriate servers"""
    
    def __init__(self, server_manager: ServerManager, tool_discovery: ToolDiscovery):
        self.server_manager = server_manager
        self.tool_discovery = tool_discovery
        self._call_counter = 0
    
    def _get_call_id(self) -> str:
        """Generate a unique call ID"""
        self._call_counter += 1
        return f"tool_call_{self._call_counter}"
    
    async def call_tool(self, tool_id: str, parameters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Call a tool with given parameters"""
        # Get tool schema
        tool = self.tool_discovery.get_tool_schema(tool_id)
        if not tool:
            logger.error(f"Tool {tool_id} not found")
            return None
            
        # Get server connection
        connection = self.server_manager.get_connection(tool.server_name)
        if not connection:
            logger.error(f"Server {tool.server_name} not connected")
            return None
            
        try:
            # Create tool call message
            call_id = self._get_call_id()
            message = JSONRPCMessage(
                method=tool.name,
                params=parameters,
                id=call_id
            )
            
            # Send request
            await connection.write_stream.asend(message.dict())
            
            # Wait for response
            async for response in connection.read_stream:
                if isinstance(response, dict) and response.get("id") == call_id:
                    if "error" in response:
                        logger.error(f"Tool call error: {response['error']}")
                        return None
                    return response.get("result")
                    
        except Exception as e:
            logger.error(f"Error calling tool {tool_id}: {str(e)}")
            return None
    
    async def call_tools_parallel(self, calls: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Call multiple tools in parallel"""
        tasks = {
            tool_id: asyncio.create_task(self.call_tool(tool_id, params))
            for tool_id, params in calls.items()
        }
        
        results = {}
        for tool_id, task in tasks.items():
            try:
                results[tool_id] = await task
            except Exception as e:
                logger.error(f"Error in parallel tool call {tool_id}: {str(e)}")
                results[tool_id] = None
                
        return results
    
    def validate_parameters(self, tool_id: str, parameters: Dict[str, Any]) -> bool:
        """Validate parameters against tool schema"""
        tool = self.tool_discovery.get_tool_schema(tool_id)
        if not tool:
            return False
            
        # Check required parameters
        required_params = {
            param.name for param in tool.parameters
            if param.required
        }
        if not all(param in parameters for param in required_params):
            return False
            
        # Validate parameter types (basic validation)
        for param in tool.parameters:
            if param.name in parameters:
                value = parameters[param.name]
                
                # Check type
                if param.type == "string" and not isinstance(value, str):
                    return False
                elif param.type == "number" and not isinstance(value, (int, float)):
                    return False
                elif param.type == "integer" and not isinstance(value, int):
                    return False
                elif param.type == "boolean" and not isinstance(value, bool):
                    return False
                elif param.type == "array" and not isinstance(value, list):
                    return False
                elif param.type == "object" and not isinstance(value, dict):
                    return False
                    
                # Check enum values
                if param.enum and value not in param.enum:
                    return False
                    
        return True
