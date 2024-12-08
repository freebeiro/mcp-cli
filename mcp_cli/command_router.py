from dataclasses import dataclass
from typing import Dict, List, Optional, Union, Any
import asyncio
import logging
from enum import Enum
import json
from mcp_cli.server_manager import ServerManager, ServerConnection
from mcp_cli.messages.json_rpc_message import JSONRPCMessage

class CommandTarget(Enum):
    """Specifies how a command should be routed"""
    SINGLE = "single"      # Send to a specific server
    GROUP = "group"        # Send to a server group
    BROADCAST = "broadcast"  # Send to all active servers

@dataclass
class CommandResponse:
    """Represents a response from a server"""
    server_name: str
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "server_name": self.server_name,
            "success": self.success,
            "data": self.data,
            "error": self.error
        }

@dataclass
class AggregatedResponse:
    """Represents aggregated responses from multiple servers"""
    success: bool
    responses: Dict[str, CommandResponse]
    error: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "success": self.success,
            "responses": {name: resp.to_dict() for name, resp in self.responses.items()},
            "error": self.error
        }

    @property
    def failed_servers(self) -> List[str]:
        """Get list of servers that failed to process the command"""
        return [name for name, resp in self.responses.items() if not resp.success]

    @property
    def successful_servers(self) -> List[str]:
        """Get list of servers that successfully processed the command"""
        return [name for name, resp in self.responses.items() if resp.success]

class ConnectionResolver:
    """Resolves target connections based on routing type"""
    
    def __init__(self, server_manager: ServerManager):
        self.server_manager = server_manager
        
    def resolve(self, target_type: CommandTarget, target: Optional[str] = None) -> List[ServerConnection]:
        """Get list of target connections based on routing type"""
        if target_type == CommandTarget.SINGLE:
            if not target:
                raise ValueError("Server name required for single-server command")
            conn = self.server_manager.get_connection(target)
            if not conn:
                raise ValueError(f"Server '{target}' not connected")
            return [conn]
            
        elif target_type == CommandTarget.GROUP:
            if not target:
                raise ValueError("Group name required for group command")
            connections = self.server_manager.get_group_connections(target)
            if not connections:
                raise ValueError(f"No connected servers in group '{target}'")
            return connections
                
        else:  # BROADCAST
            connections = self.server_manager.get_all_connections()
            if not connections:
                raise ValueError("No servers connected for broadcast")
            return connections

class CommandRouter:
    """Routes commands to appropriate servers and collects responses"""
    
    def __init__(self, server_manager: ServerManager):
        self.resolver = ConnectionResolver(server_manager)
        self.logger = logging.getLogger(__name__)

    async def _execute_command(self, connection: ServerConnection, command: str) -> CommandResponse:
        """Execute command on a single server and get response"""
        try:
            request = JSONRPCMessage(
                jsonrpc="2.0",
                method=command,
                params={},
                id="1"  # Changed to string type
            )
            
            await connection.writer.send(request)
            response = await connection.reader.receive()
            
            if isinstance(response, JSONRPCMessage):
                if response.error:
                    return CommandResponse(
                        server_name=connection.server_name,
                        success=False,
                        error=str(response.error)
                    )
                return CommandResponse(
                    server_name=connection.server_name,
                    success=True,
                    data=response.result
                )
            else:
                return CommandResponse(
                    server_name=connection.server_name,
                    success=False,
                    error="Invalid response format"
                )
                
        except Exception as e:
            return CommandResponse(
                server_name=connection.server_name,
                success=False,
                error=str(e)
            )

    async def send_command(
        self,
        command: str,
        target_type: CommandTarget,
        target: Optional[str] = None,
        timeout: float = 30.0
    ) -> AggregatedResponse:
        """Send command to target servers and collect responses"""
        try:
            # Get target connections
            connections = self.resolver.resolve(target_type, target)
            
            # Execute command on all targets with timeout
            tasks = [self._execute_command(conn, command) for conn in connections]
            async with asyncio.timeout(timeout):
                responses = await asyncio.gather(*tasks)
                
            # Aggregate responses
            response_dict = {resp.server_name: resp for resp in responses}
            success = all(resp.success for resp in responses)
            
            return AggregatedResponse(
                success=success,
                responses=response_dict,
                error=None if success else "Some servers failed to process command"
            )
            
        except asyncio.TimeoutError:
            return AggregatedResponse(
                success=False,
                responses={conn.server_name: CommandResponse(
                    server_name=conn.server_name,
                    success=False,
                    error="Timeout"
                ) for conn in connections},
                error="Command timed out"
            )
        except Exception as e:
            return AggregatedResponse(
                success=False,
                responses={},
                error=f"Command failed: {str(e)}"
            )
