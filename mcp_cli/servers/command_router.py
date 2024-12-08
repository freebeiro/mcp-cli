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
                server = self.server_manager.get_server(target)
                if not server:
                    return CommandResponse(
                        success=False,
                        error=f"Server '{target}' not connected"
                    )
                
                try:
                    # For Ollama server
                    if target == "ollama":
                        response = await server.chat(command)
                        return CommandResponse(success=True, result={"response": response})
                    
                    # For other servers
                    request = {
                        "method": "chat",
                        "params": {
                            "message": command
                        }
                    }
                    response = await server.process_request(request)
                    
                    # Handle any tool calls
                    tool_result = await self.tool_router.handle_tool(response)
                    if tool_result:
                        return CommandResponse(success=True, result=tool_result)
                        
                    return CommandResponse(success=True, result=response)
                    
                except Exception as e:
                    return CommandResponse(
                        success=False,
                        error=f"Error processing command: {str(e)}"
                    )
                    
            elif target_type == CommandTarget.GROUP:
                # Group commands will be implemented later
                return CommandResponse(
                    success=False,
                    error="Group commands not implemented yet"
                )
                
            elif target_type == CommandTarget.BROADCAST:
                # Broadcast commands will be implemented later
                return CommandResponse(
                    success=False,
                    error="Broadcast commands not implemented yet"
                )
                
            else:
                return CommandResponse(
                    success=False,
                    error=f"Unknown target type: {target_type}"
                )
                
        except Exception as e:
            return CommandResponse(
                success=False,
                error=f"Error routing command: {str(e)}"
            )
