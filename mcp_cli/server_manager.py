from dataclasses import dataclass
from typing import Dict, List, Optional, AsyncIterator
import anyio
import logging
from mcp_cli.transport.stdio.stdio_server_parameters import StdioServerParameters
from mcp_cli.transport.stdio.stdio_client import stdio_client
from mcp_cli.config_types import MCPConfig
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream

class ServerConnection:
    """Represents a connection to a server."""
    def __init__(self, server_name: str, reader: MemoryObjectReceiveStream, writer: MemoryObjectSendStream):
        self.server_name = server_name
        self.reader = reader
        self.writer = writer
        
    async def close(self):
        """Close the connection."""
        if self.writer:
            await self.writer.aclose()

class ServerManager:
    """Manages multiple server connections"""
    
    def __init__(self, config: MCPConfig):
        self.config = config
        self.connections: Dict[str, ServerConnection] = {}
        self.logger = logging.getLogger(__name__)

    async def connect_server(self, server_name: str) -> None:
        """Connect to a single server"""
        if server_name not in self.config.server_params:
            raise ValueError(f"Server '{server_name}' not found in configuration")

        try:
            params = self.config.server_params[server_name]
            client = await stdio_client(params)
            async with client as (reader, writer):
                self.connections[server_name] = ServerConnection(
                    server_name=server_name,
                    reader=reader,
                    writer=writer
                )
                self.logger.info(f"Connected to server {server_name}")
        except Exception as e:
            self.logger.error(f"Failed to connect to server {server_name}: {e}")
            raise

    async def connect_all(self) -> List[ServerConnection]:
        """Connect to all active servers"""
        connections = []
        for server_name in self.config.active_servers:
            try:
                await self.connect_server(server_name)
                connections.append(self.connections[server_name])
            except Exception as e:
                self.logger.error(f"Failed to connect to server {server_name}: {e}")
                raise
        return connections

    async def disconnect_server(self, server_name: str) -> None:
        """Disconnect from a server"""
        if server_name not in self.connections:
            return
        
        try:
            connection = self.connections[server_name]
            await connection.close()
            del self.connections[server_name]
            self.logger.info(f"Disconnected from server {server_name}")
        except Exception as e:
            self.logger.error(f"Failed to disconnect from server {server_name}: {e}")
            raise

    async def disconnect_all(self) -> None:
        """Disconnect from all servers"""
        for server_name in list(self.connections.keys()):
            await self.disconnect_server(server_name)

    def get_connection(self, server_name: str) -> Optional[ServerConnection]:
        """Get connection for a specific server"""
        return self.connections.get(server_name)

    def get_all_connections(self) -> List[ServerConnection]:
        """Get all connections"""
        return list(self.connections.values())

    def get_group_connections(self, group_name: str) -> List[ServerConnection]:
        """Get all connections for servers in a group"""
        if group_name not in self.config.server_groups:
            return []
        
        group = self.config.server_groups[group_name]
        return [conn for name, conn in self.connections.items() if name in group.servers]

    async def __aenter__(self):
        """Context manager entry"""
        await self.connect_all()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.disconnect_all()
