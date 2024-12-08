import pytest
import asyncio
from typing import AsyncIterator, Tuple
import json
from mcp_cli.config_types import MCPConfig, ServerGroup
from mcp_cli.server_manager import ServerManager, ServerConnection
from mcp_cli.transport.stdio.stdio_server_parameters import StdioServerParameters

class MockStreamReader:
    """Mock stream reader for testing."""
    def __init__(self, responses):
        self.responses = responses
        self.current = 0
        
    async def readline(self):
        if self.current < len(self.responses):
            response = self.responses[self.current]
            self.current += 1
            return json.dumps(response).encode()
        return b""

class MockStreamWriter:
    """Mock stream writer for testing."""
    def __init__(self):
        self.written = []
        
    async def write(self, data):
        self.written.append(data)
        
    async def drain(self):
        pass
        
    async def aclose(self):
        pass

@pytest.fixture
async def mock_streams():
    """Create mock streams for testing."""
    reader = MockStreamReader([{"status": "ok", "server": "test"}])
    writer = MockStreamWriter()
    return reader, writer

@pytest.fixture
async def mock_stdio_client(mock_streams):
    """Create a mock stdio client for testing."""
    reader, writer = await mock_streams
    
    class MockAsyncContextManager:
        async def __aenter__(self):
            return reader, writer
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            await writer.aclose()
    
    async def _mock_stdio_client(params):
        return MockAsyncContextManager()
    
    return _mock_stdio_client

@pytest.fixture
async def mock_config():
    """Create a mock configuration"""
    config = MCPConfig(
        version="2.0.0",
        server_params={
            "server1": StdioServerParameters(command="test1", args=[], env=None),
            "server2": StdioServerParameters(command="test2", args=[], env=None)
        },
        server_groups={
            "group1": ServerGroup(servers=["server1"], description="Test group 1"),
            "group2": ServerGroup(servers=["server1", "server2"], description="Test group 2")
        },
        active_servers=["server1", "server2"]
    )
    return config

@pytest.fixture
async def server_manager(mock_config):
    """Create a server manager instance for testing."""
    return ServerManager(await mock_config)

@pytest.mark.asyncio
async def test_connect_server(mock_config, monkeypatch, mock_stdio_client):
    """Test connecting to a single server"""
    stdio = await mock_stdio_client
    monkeypatch.setattr("mcp_cli.server_manager.stdio_client", stdio)
    
    config = await mock_config
    manager = ServerManager(config)
    await manager.connect_server("server1")
    
    assert "server1" in manager.connections
    assert isinstance(manager.connections["server1"], ServerConnection)

@pytest.mark.asyncio
async def test_connect_all(mock_config, monkeypatch, mock_stdio_client):
    """Test connecting to all active servers"""
    stdio = await mock_stdio_client
    monkeypatch.setattr("mcp_cli.server_manager.stdio_client", stdio)
    
    config = await mock_config
    manager = ServerManager(config)
    connections = await manager.connect_all()
    
    assert len(connections) == 2
    assert all(isinstance(conn, ServerConnection) for conn in connections)

@pytest.mark.asyncio
async def test_disconnect_server(mock_config, monkeypatch, mock_stdio_client):
    """Test disconnecting from a server"""
    stdio = await mock_stdio_client
    monkeypatch.setattr("mcp_cli.server_manager.stdio_client", stdio)
    
    config = await mock_config
    manager = ServerManager(config)
    await manager.connect_server("server1")
    assert "server1" in manager.connections
    
    await manager.disconnect_server("server1")
    assert "server1" not in manager.connections

@pytest.mark.asyncio
async def test_get_group_connections(mock_config, monkeypatch, mock_stdio_client):
    """Test getting connections by group"""
    stdio = await mock_stdio_client
    monkeypatch.setattr("mcp_cli.server_manager.stdio_client", stdio)
    
    config = await mock_config
    manager = ServerManager(config)
    await manager.connect_all()
    
    group1_conns = manager.get_group_connections("group1")
    assert len(group1_conns) == 1
    assert "server1" in [conn.server_name for conn in group1_conns]
    
    group2_conns = manager.get_group_connections("group2")
    assert len(group2_conns) == 2
    assert all(conn.server_name in ["server1", "server2"] for conn in group2_conns)

@pytest.mark.asyncio
async def test_context_manager(mock_config, monkeypatch, mock_stdio_client):
    """Test using ServerManager as a context manager"""
    stdio = await mock_stdio_client
    monkeypatch.setattr("mcp_cli.server_manager.stdio_client", stdio)
    
    config = await mock_config
    async with ServerManager(config) as manager:
        assert len(manager.connections) == 2
        assert "server1" in manager.connections
        assert "server2" in manager.connections
