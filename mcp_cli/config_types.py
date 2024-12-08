from dataclasses import dataclass
from typing import Dict, List, Optional
from mcp_cli.transport.stdio.stdio_server_parameters import StdioServerParameters

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
    server_groups: Dict[str, ServerGroup]
    active_servers: List[str]

    @classmethod
    def from_dict(cls, config_dict: dict) -> 'MCPConfig':
        """Create MCPConfig from a dictionary, handling both v1 and v2 formats"""
        version = config_dict.get('version', '1.0.0')
        
        # Convert mcpServers to StdioServerParameters
        server_params = {}
        for name, server_config in config_dict.get('mcpServers', {}).items():
            server_params[name] = StdioServerParameters(
                command=server_config['command'],
                args=server_config.get('args', []),
                env=server_config.get('env')
            )

        # Handle server groups based on version
        if version.startswith('1'):
            # v1: Create default group with single server
            server_groups = {
                'default': ServerGroup(
                    servers=[next(iter(server_params.keys()))] if server_params else [],
                    description="Default single server setup"
                )
            }
            active_servers = list(server_groups['default'].servers)
        else:
            # v2: Load groups and active servers from config
            server_groups = {
                name: ServerGroup(**group_data)
                for name, group_data in config_dict.get('serverGroups', {}).items()
            }
            active_servers = config_dict.get('activeServers', [])

        return cls(
            version=version,
            server_params=server_params,
            server_groups=server_groups,
            active_servers=active_servers
        )

    def get_server_params(self, server_name: str) -> StdioServerParameters:
        """Get server parameters for a specific server"""
        if server_name not in self.server_params:
            raise ValueError(f"Server '{server_name}' not found in configuration")
        return self.server_params[server_name]

    def get_active_server_params(self) -> List[StdioServerParameters]:
        """Get parameters for all active servers"""
        return [self.get_server_params(name) for name in self.active_servers]
