from dataclasses import dataclass
from typing import Dict, List, Optional
from transport.stdio.stdio_server_parameters import StdioServerParameters

@dataclass
class ServerGroup:
    """Represents a group of servers that can be managed together"""
    servers: List[str]
    description: str

@dataclass
class MCPConfig:
    """Represents the full MCP configuration"""
    version: str
    server_params: Dict[str, StdioServerParameters]
    server_groups: Optional[Dict[str, ServerGroup]] = None
    active_servers: Optional[List[str]] = None

    def __init__(self, config_dict: dict):
        """Initialize MCPConfig from a dictionary"""
        self.version = config_dict.get('version', '1.0.0')
        self.server_params = {}
        
        # Convert mcpServers to StdioServerParameters
        for name, server_config in config_dict.get('mcpServers', {}).items():
            self.server_params[name] = StdioServerParameters(
                command=server_config['command'],
                args=server_config.get('args', []),
                env=server_config.get('env', {})
            )

        # Set active servers to all available servers by default
        self.active_servers = list(self.server_params.keys())
        
        # Handle server groups based on version
        if self.version.startswith('1'):
            # v1: Create default group with all servers
            self.server_groups = {
                'default': ServerGroup(
                    servers=self.active_servers,
                    description="Default server group"
                )
            }
        else:
            # v2: Load groups from config
            self.server_groups = {
                name: ServerGroup(**group_data)
                for name, group_data in config_dict.get('serverGroups', {}).items()
            }

    def get_server_params(self, server_name: str) -> StdioServerParameters:
        """Get parameters for a specific server"""
        if server_name not in self.server_params:
            raise ValueError(f"Server '{server_name}' not found in configuration")
        return self.server_params[server_name]

    def get_active_servers(self) -> List[str]:
        """Get list of active servers"""
        return self.active_servers or []

    def get_server_group(self, group_name: str) -> ServerGroup:
        """Get a server group by name"""
        if not self.server_groups or group_name not in self.server_groups:
            raise ValueError(f"Server group '{group_name}' not found")
        return self.server_groups[group_name]
