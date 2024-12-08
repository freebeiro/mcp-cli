import pytest
import asyncio
from typing import AsyncGenerator, Dict
import json
from config_types import MCPConfig, ServerGroup
from server_manager import ServerManager, ServerConnection
from transport.stdio.stdio_server_parameters import StdioServerParameters

class MockAsyncGenerator:
    """Mock async generator for testing"""
    def __init__(self, responses=None):
        self.responses = responses or []
        self.current = 0
        self.closed = False
    
    async def __aiter__(self):
        return self
    
    async def __anext__(self):
        if self.current < len(self.responses):
            response = self.responses[self.current]
            self.current += 1
            return response
        raise StopAsyncIteration
    
    async def asend(self, value: Dict) -> None:
        """Mock send method"""
        self.responses.append(value)
    
    async def aclose(self) -> None:
        """Mock close method"""
        self.closed = True

@pytest.fixture
def mock_config():
    """Create a mock configuration"""
    return MCPConfig({
        "version": "2.0.0",
        "mcpServers": {
            "server1": {
                "command": "test1",
                "args": [],
                "env": None
            },
            "server2": {
                "command": "test2",
                "args": [],
                "env": None
            }
        },
        "serverGroups": {
            "group1": {
                "servers": ["server1"],
                "description": "Test group 1"
            },
            "group2": {
                "servers": ["server1", "server2"],
                "description": "Test group 2"
            }
        }
    })

@pytest.fixture
def mock_streams():
    """Create mock streams for testing"""
    read_stream = MockAsyncGenerator([
        {"method": "ready", "id": "init", "params": {"server": "test"}},
        {"method": "notification", "params": {"message": "test"}}
    ])
    write_stream = MockAsyncGenerator()
    return read_stream, write_stream

@pytest.mark.asyncio
async def test_connect_server(mock_config, monkeypatch, mock_streams):
    """Test connecting to a single server"""
    read_stream, write_stream = mock_streams
    
    async def mock_stdio_client(params):
        return read_stream, write_stream
    
    # Patch the stdio_client function
    monkeypatch.setattr("server_manager.stdio_client", mock_stdio_client)
    
    manager = ServerManager(mock_config)
    connection = await manager.connect_server("server1")
    
    assert connection.name == "server1"
    assert connection.status == "connected"
    assert connection.last_error is None
    assert manager.get_connection("server1") == connection

@pytest.mark.asyncio
async def test_connect_all(mock_config, monkeypatch, mock_streams):
    """Test connecting to all active servers"""
    read_stream, write_stream = mock_streams
    
    async def mock_stdio_client(params):
        return read_stream, write_stream
    
    monkeypatch.setattr("server_manager.stdio_client", mock_stdio_client)
    
    manager = ServerManager(mock_config)
    connections = await manager.connect_all()
    
    assert len(connections) == 2
    assert all(conn.status == "connected" for conn in connections)
    assert set(manager.connections.keys()) == {"server1", "server2"}

@pytest.mark.asyncio
async def test_disconnect_server(mock_config, monkeypatch, mock_streams):
    """Test disconnecting from a server"""
    read_stream, write_stream = mock_streams
    
    async def mock_stdio_client(params):
        return read_stream, write_stream
    
    monkeypatch.setattr("server_manager.stdio_client", mock_stdio_client)
    
    manager = ServerManager(mock_config)
    await manager.connect_server("server1")
    await manager.disconnect_server("server1")
    
    assert "server1" not in manager.connections
    assert read_stream.closed
    assert write_stream.closed

@pytest.mark.asyncio
async def test_get_group_connections(mock_config, monkeypatch, mock_streams):
    """Test getting connections by group"""
    read_stream, write_stream = mock_streams
    
    async def mock_stdio_client(params):
        return read_stream, write_stream
    
    monkeypatch.setattr("server_manager.stdio_client", mock_stdio_client)
    
    manager = ServerManager(mock_config)
    await manager.connect_all()
    
    group1_conns = manager.get_group_connections("group1")
    assert len(group1_conns) == 1
    assert group1_conns[0].name == "server1"
    
    group2_conns = manager.get_group_connections("group2")
    assert len(group2_conns) == 2
    assert {conn.name for conn in group2_conns} == {"server1", "server2"}

@pytest.mark.asyncio
async def test_context_manager(mock_config, monkeypatch, mock_streams):
    """Test using ServerManager as a context manager"""
    read_stream, write_stream = mock_streams
    
    async def mock_stdio_client(params):
        return read_stream, write_stream
    
    monkeypatch.setattr("server_manager.stdio_client", mock_stdio_client)
    
    async with ServerManager(mock_config) as manager:
        assert len(manager.connections) == 2
        assert all(conn.status == "connected" for conn in manager.connections.values())
    
    # After context exit, all connections should be closed
    assert read_stream.closed
    assert write_stream.closed
    assert len(manager.connections) == 0
