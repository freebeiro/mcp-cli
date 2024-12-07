from dataclasses import dataclass
from typing import Dict, List, Optional, AsyncIterator
import asyncio
import logging
from transport.stdio.stdio_server_parameters import StdioServerParameters
from transport.stdio.stdio_client import stdio_client
from config_types import MCPConfig, ServerGroup

@dataclass
class ServerConnection:
    """Represents an active server connection"""
    name: str
    parameters: StdioServerParameters
    read_stream: AsyncIterator[str]
    write_stream: asyncio.StreamWriter
    status: str = "connected"
    last_error: Optional[str] = None

class ServerManager:
    """Manages multiple server connections and their lifecycle"""
    
    def __init__(self, config: MCPConfig):
        self.config = config
        self.connections: Dict[str, ServerConnection] = {}
        self.logger = logging.getLogger(__name__)

    async def connect_server(self, server_name: str) -> ServerConnection:
        """Connect to a single server"""
        if server_name in self.connections:
            return self.connections[server_name]

        try:
            params = self.config.get_server_params(server_name)
            read_stream, write_stream = await stdio_client(params)
            
            connection = ServerConnection(
                name=server_name,
                parameters=params,
                read_stream=read_stream,
                write_stream=write_stream
            )
            
            self.connections[server_name] = connection
            self.logger.info(f"Connected to server: {server_name}")
            return connection
            
        except Exception as e:
            self.logger.error(f"Failed to connect to server {server_name}: {str(e)}")
            raise

    async def connect_all(self) -> List[ServerConnection]:
        """Connect to all active servers"""
        connections = []
        for server_name in self.config.active_servers:
            try:
                connection = await self.connect_server(server_name)
                connections.append(connection)
            except Exception as e:
                self.logger.error(f"Failed to connect to {server_name}: {str(e)}")
                # Continue connecting to other servers even if one fails
                continue
        return connections

    async def disconnect_server(self, server_name: str) -> None:
        """Disconnect from a specific server"""
        if server_name not in self.connections:
            return

        connection = self.connections[server_name]
        try:
            await connection.write_stream.aclose()
            del self.connections[server_name]
            self.logger.info(f"Disconnected from server: {server_name}")
        except Exception as e:
            self.logger.error(f"Error disconnecting from {server_name}: {str(e)}")
            raise

    async def disconnect_all(self) -> None:
        """Disconnect from all servers"""
        for server_name in list(self.connections.keys()):
            await self.disconnect_server(server_name)

    def get_connection(self, server_name: str) -> Optional[ServerConnection]:
        """Get an active server connection"""
        return self.connections.get(server_name)

    def get_group_connections(self, group_name: str) -> List[ServerConnection]:
        """Get all connections for servers in a group"""
        if group_name not in self.config.server_groups:
            return []
            
        group = self.config.server_groups[group_name]
        return [
            conn for name, conn in self.connections.items()
            if name in group.servers
        ]

    async def __aenter__(self):
        """Context manager entry"""
        await self.connect_all()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.disconnect_all()
