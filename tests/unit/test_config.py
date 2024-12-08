import json
import pytest
from pathlib import Path
from mcp_cli.config_types import MCPConfig, ServerGroup
from mcp_cli.transport.stdio.stdio_server_parameters import StdioServerParameters

@pytest.fixture
def v1_config_file(tmp_path):
    """Create a v1 format config file"""
    config = {
        "mcpServers": {
            "sqlite": {
                "command": "uvx",
                "args": ["mcp-server-sqlite", "--db-path", "test.db"]
            }
        }
    }
    config_file = tmp_path / "v1_config.json"
    config_file.write_text(json.dumps(config))
    return config_file

@pytest.fixture
def v2_config_file(tmp_path):
    """Create a v2 format config file"""
    config = {
        "version": "2.0.0",
        "mcpServers": {
            "sqlite": {
                "command": "uvx",
                "args": ["mcp-server-sqlite", "--db-path", "test.db"]
            },
            "filesystem": {
                "command": "npx",
                "args": ["@modelcontextprotocol/server-filesystem", "/test/path"]
            }
        },
        "serverGroups": {
            "default": {
                "servers": ["sqlite"],
                "description": "Default setup"
            },
            "full": {
                "servers": ["sqlite", "filesystem"],
                "description": "Full setup"
            }
        },
        "activeServers": ["sqlite", "filesystem"]
    }
    config_file = tmp_path / "v2_config.json"
    config_file.write_text(json.dumps(config))
    return config_file

def test_load_v1_config(v1_config_file):
    """Test loading v1 format configuration"""
    config = MCPConfig.from_dict(json.loads(v1_config_file.read_text()))
    
    # Check version defaulted to 1.0.0
    assert config.version == "1.0.0"
    
    # Check server parameters
    assert len(config.server_params) == 1
    assert "sqlite" in config.server_params
    assert config.server_params["sqlite"].command == "uvx"
    
    # Check default group was created
    assert len(config.server_groups) == 1
    assert "default" in config.server_groups
    assert config.server_groups["default"].servers == ["sqlite"]
    
    # Check active servers
    assert config.active_servers == ["sqlite"]

def test_load_v2_config(v2_config_file):
    """Test loading v2 format configuration"""
    config = MCPConfig.from_dict(json.loads(v2_config_file.read_text()))
    
    # Check version
    assert config.version == "2.0.0"
    
    # Check server parameters
    assert len(config.server_params) == 2
    assert "sqlite" in config.server_params
    assert "filesystem" in config.server_params
    
    # Check server groups
    assert len(config.server_groups) == 2
    assert "default" in config.server_groups
    assert "full" in config.server_groups
    assert config.server_groups["full"].servers == ["sqlite", "filesystem"]
    
    # Check active servers
    assert set(config.active_servers) == {"sqlite", "filesystem"}

def test_get_server_params(v2_config_file):
    """Test getting server parameters"""
    config = MCPConfig.from_dict(json.loads(v2_config_file.read_text()))
    
    # Test valid server
    params = config.get_server_params("sqlite")
    assert isinstance(params, StdioServerParameters)
    assert params.command == "uvx"
    
    # Test invalid server
    with pytest.raises(ValueError):
        config.get_server_params("nonexistent")

def test_get_active_server_params(v2_config_file):
    """Test getting active server parameters"""
    config = MCPConfig.from_dict(json.loads(v2_config_file.read_text()))
    
    params = config.get_active_server_params()
    assert len(params) == 2
    assert all(isinstance(p, StdioServerParameters) for p in params)
    commands = {p.command for p in params}
    assert commands == {"uvx", "npx"}
