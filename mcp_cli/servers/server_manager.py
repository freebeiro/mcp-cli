import asyncio
import json
from typing import Dict, List, Optional
from enum import Enum

class CommandTarget(Enum):
    SINGLE = "SINGLE"
    GROUP = "GROUP"
    BROADCAST = "BROADCAST"

class ServerManager:
    def __init__(self):
        self.connections = {}
        self.groups = {}
        
    async def connect_server(self, server_name: str, config: Dict) -> bool:
        """Connect to a single server"""
        try:
            # Implementation details
            self.connections[server_name] = {"status": "connected"}
            return True
        except Exception as e:
            return False
            
    async def connect_all(self) -> Dict[str, bool]:
        """Connect to all configured servers"""
        results = {}
        for server_name, config in self.get_config().items():
            results[server_name] = await self.connect_server(server_name, config)
        return results
        
    async def disconnect_server(self, server_name: str) -> bool:
        """Disconnect from a server"""
        if server_name in self.connections:
            del self.connections[server_name]
            return True
        return False
        
    async def disconnect_all(self) -> None:
        """Disconnect from all servers"""
        for server_name in list(self.connections.keys()):
            await self.disconnect_server(server_name)
            
    def get_group_connections(self, group_name: str) -> List[str]:
        """Get all servers in a group"""
        return self.groups.get(group_name, [])
        
    def get_config(self) -> Dict:
        """Get server configuration"""
        # Mock configuration for testing
        return {
            "server1": {},
            "server2": {},
            "server3": {}
        }
