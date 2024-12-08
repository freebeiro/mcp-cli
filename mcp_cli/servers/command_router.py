import asyncio
from dataclasses import dataclass
from typing import Dict, List, Optional
from .server_manager import ServerManager, CommandTarget
from .tool_router import ToolRouter

@dataclass
class CommandResponse:
    success: bool
    result: Optional[Dict] = None
    error: Optional[str] = None

class CommandRouter:
    def __init__(self, server_manager: ServerManager):
        self.server_manager = server_manager
        self.tool_router = ToolRouter()
        
    async def send_command(
        self,
        command: str,
        target_type: CommandTarget,
        target: str,
        timeout: float = 30.0
    ) -> CommandResponse:
        """Send a command to target(s)"""
        try:
            if target_type == CommandTarget.SINGLE:
                if target not in self.server_manager.connections:
                    return CommandResponse(
                        success=False,
                        error=f"Server '{target}' not connected"
                    )
                
                server = self.server_manager.connections[target]
                try:
                    # Create request object
                    request = {
                        "method": "chat",
                        "params": {
                            "message": command
                        }
                    }
                    
                    # Process request and get response
                    response = await server.process_request(request)
                    
                    # Handle any tool calls
                    try:
                        tool_result = await self.tool_router.handle_tool(response)
                        if tool_result:
                            return CommandResponse(success=True, result=tool_result)
                    except Exception as e:
                        return CommandResponse(success=False, error=str(e))
                        
                    return CommandResponse(success=True, result={"response": response})
                    
                except Exception as e:
                    return CommandResponse(
                        success=False,
                        error=f"Command failed: {str(e)}"
                    )
                
            elif target_type == CommandTarget.GROUP:
                servers = self.server_manager.get_group_connections(target)
                if not servers:
                    return CommandResponse(
                        success=False,
                        error=f"Group '{target}' not found or empty"
                    )
                
                try:
                    # Create request object
                    request = {
                        "method": "chat",
                        "params": {
                            "message": command
                        }
                    }
                    
                    # Process request on all servers in group
                    tasks = [
                        server.process_request(request)
                        for server in servers
                    ]
                    responses = await asyncio.gather(*tasks)
                    
                    # Handle any tool calls from responses
                    tool_results = []
                    for response in responses:
                        try:
                            tool_result = await self.tool_router.handle_tool(response)
                            if tool_result:
                                tool_results.append(tool_result)
                        except Exception as e:
                            return CommandResponse(success=False, error=str(e))
                            
                    if tool_results:
                        return CommandResponse(success=True, result={"tool_results": tool_results})
                        
                    return CommandResponse(success=True, result={"responses": responses})
                    
                except Exception as e:
                    return CommandResponse(
                        success=False,
                        error=f"Group command failed: {str(e)}"
                    )
                
            elif target_type == CommandTarget.BROADCAST:
                if not self.server_manager.connections:
                    return CommandResponse(
                        success=False,
                        error="No servers connected"
                    )
                
                try:
                    # Create request object
                    request = {
                        "method": "chat",
                        "params": {
                            "message": command
                        }
                    }
                    
                    # Process request on all connected servers
                    tasks = [
                        server.process_request(request)
                        for server in self.server_manager.connections.values()
                    ]
                    responses = await asyncio.gather(*tasks)
                    
                    # Handle any tool calls from responses
                    tool_results = []
                    for response in responses:
                        try:
                            tool_result = await self.tool_router.handle_tool(response)
                            if tool_result:
                                tool_results.append(tool_result)
                        except Exception as e:
                            return CommandResponse(success=False, error=str(e))
                            
                    if tool_results:
                        return CommandResponse(success=True, result={"tool_results": tool_results})
                        
                    return CommandResponse(success=True, result={"responses": responses})
                    
                except Exception as e:
                    return CommandResponse(
                        success=False,
                        error=f"Broadcast command failed: {str(e)}"
                    )
                
            else:
                return CommandResponse(
                    success=False,
                    error=f"Invalid target type: {target_type}"
                )
                
        except Exception as e:
            return CommandResponse(
                success=False,
                error=f"Command routing failed: {str(e)}"
            )
