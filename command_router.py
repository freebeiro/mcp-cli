from dataclasses import dataclass
from typing import Dict, List, Optional, Union, Any
import asyncio
import logging
from enum import Enum
import json
from server_manager import ServerManager, ServerConnection

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

@dataclass
class AggregatedResponse:
    """Represents aggregated responses from multiple servers"""
    success: bool
    responses: Dict[str, CommandResponse]
    error: Optional[str] = None

    @property
    def failed_servers(self) -> List[str]:
        """Get list of servers that failed to process the command"""
        return [name for name, resp in self.responses.items() if not resp.success]

    @property
    def successful_servers(self) -> List[str]:
        """Get list of servers that successfully processed the command"""
        return [name for name, resp in self.responses.items() if resp.success]

class CommandRouter:
    """Routes commands to appropriate servers and collects responses"""
    
    def __init__(self, server_manager: ServerManager):
        self.server_manager = server_manager
        self.logger = logging.getLogger(__name__)

    async def _send_command(self, connection: ServerConnection, command: str) -> CommandResponse:
        """Send command to a single server and get response"""
        try:
            # Send command
            command_bytes = (command + "\n").encode()
            await connection.write_stream.write(command_bytes)
            
            # Get response
            response = await connection.read_stream.readline()
            if not response:
                raise ConnectionError(f"No response from server {connection.name}")
            
            # Parse response
            try:
                data = json.loads(response.decode())
                return CommandResponse(
                    server_name=connection.name,
                    success=True,
                    data=data
                )
            except json.JSONDecodeError as e:
                return CommandResponse(
                    server_name=connection.name,
                    success=False,
                    error=f"Invalid JSON response: {str(e)}"
                )
                
        except Exception as e:
            return CommandResponse(
                server_name=connection.name,
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
        """Send command to target servers and collect responses
        
        Args:
            command: The command to send
            target_type: How to route the command (single server, group, or broadcast)
            target: Server name or group name (not needed for broadcast)
            timeout: Maximum time to wait for responses in seconds
        """
        # Get target connections based on routing type
        connections: List[ServerConnection] = []
        if target_type == CommandTarget.SINGLE:
            if not target:
                raise ValueError("Server name required for single-server command")
            conn = self.server_manager.get_connection(target)
            if not conn:
                raise ValueError(f"Server '{target}' not connected")
            connections = [conn]
            
        elif target_type == CommandTarget.GROUP:
            if not target:
                raise ValueError("Group name required for group command")
            connections = self.server_manager.get_group_connections(target)
            if not connections:
                raise ValueError(f"No connected servers in group '{target}'")
                
        else:  # BROADCAST
            connections = self.server_manager.get_all_connections()
            if not connections:
                raise ValueError("No servers connected for broadcast")

        # Send command to all target connections with timeout
        tasks = [self._send_command(conn, command) for conn in connections]
        try:
            async with asyncio.timeout(timeout):
                responses = await asyncio.gather(*tasks)
        except asyncio.TimeoutError:
            return AggregatedResponse(
                success=False,
                responses={conn.name: CommandResponse(
                    server_name=conn.name,
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

        # Aggregate responses
        response_dict = {resp.server_name: resp for resp in responses}
        success = all(resp.success for resp in responses)
        
        return AggregatedResponse(
            success=success,
            responses=response_dict,
            error=None if success else "Some servers failed to process command"
        )
