import asyncio
import json
import os
from typing import Dict, List, Optional
from enum import Enum
from .ollama_server import OllamaChat

class CommandTarget(Enum):
    SINGLE = "SINGLE"
    GROUP = "GROUP"
    BROADCAST = "BROADCAST"

class ServerManager:
    def __init__(self, config_path: str = None):
        self.connections = {}
        self.groups = {}
        self.config_path = config_path or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "server_config.json")
        
    async def connect_server(self, server_name: str, config: Dict) -> bool:
        """Connect to a single server"""
        try:
            if server_name == "ollama":
                self.connections[server_name] = OllamaChat()
            else:
                # Other server types will be implemented later
                pass
            return True
        except Exception as e:
            print(f"Failed to connect to {server_name}: {str(e)}")
            return False
            
    async def connect_all(self) -> Dict[str, bool]:
        """Connect to all configured servers"""
        results = {}
        config = self.get_config()
        if not config:
            return results
            
        for server_name, server_config in config.get("mcpServers", {}).items():
            results[server_name] = await self.connect_server(server_name, server_config)
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
            
    def get_server(self, server_name: str) -> Optional[object]:
        """Get a server instance by name"""
        return self.connections.get(server_name)
            
    def get_group_connections(self, group_name: str) -> List[str]:
        """Get all servers in a group"""
        return self.groups.get(group_name, [])
        
    def get_config(self) -> Dict:
        """Get server configuration"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Failed to load config from {self.config_path}: {str(e)}")
            return {}
