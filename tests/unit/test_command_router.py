import pytest
import json
import asyncio
from typing import Dict, List, AsyncGenerator, Tuple
from mcp_cli.command_router import CommandRouter, CommandTarget, CommandResponse, AggregatedResponse
from mcp_cli.server_manager import ServerManager
from mcp_cli.config_types import MCPConfig, ServerGroup
from mcp_cli.transport.stdio.stdio_server_parameters import StdioServerParameters
from mcp_cli.messages.json_rpc_message import JSONRPCMessage
from contextlib import asynccontextmanager

class MockStreamReader:
    """Mock stream reader for testing."""
    def __init__(self, server_name: str):
        self.server_name = server_name
        self.received_messages = []

    async def receive(self) -> JSONRPCMessage:
        """Mock receive method."""
        return JSONRPCMessage(
            jsonrpc="2.0",
            result={"status": "success"},
            id="1"
        )

class MockStreamWriter:
    """Mock stream writer for testing."""
    def __init__(self, server_name: str):
        self.server_name = server_name
        self.sent_messages = []

    async def send(self, message: JSONRPCMessage) -> None:
        """Mock send method."""
        self.sent_messages.append(message)

@pytest.fixture
async def mock_config():
    """Create a mock configuration"""
    return MCPConfig(
        version="2.0.0",
        server_params={
            "server1": StdioServerParameters(command="test1", args=[], env=None),
            "server2": StdioServerParameters(command="test2", args=[], env=None),
            "server3": StdioServerParameters(command="test3", args=[], env=None)
        },
        server_groups={
            "group1": ServerGroup(servers=["server1", "server2"], description="Test group 1"),
            "group2": ServerGroup(servers=["server2", "server3"], description="Test group 2")
        },
        active_servers=["server1", "server2", "server3"]
    )

@pytest.fixture
async def mock_stdio_client():
    """Create a mock stdio client."""
    class MockStdioClient:
        def __init__(self, params: StdioServerParameters):
            self.params = params
            self.reader = MockStreamReader(params.command)
            self.writer = MockStreamWriter(params.command)

        async def __aenter__(self):
            return self.reader, self.writer

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    async def mock_client(params: StdioServerParameters):
        return MockStdioClient(params)

    return mock_client

@pytest.fixture
async def server_manager(mock_config):
    """Create a server manager instance."""
    config = await mock_config
    manager = ServerManager(config)
    await manager.connect_all()
    return manager

@pytest.fixture
async def command_router(server_manager):
    """Create a command router instance."""
    manager = await server_manager
    router = CommandRouter(manager)
    return router

@pytest.mark.asyncio
async def test_single_server_command(command_router, monkeypatch, mock_stdio_client):
    """Test sending command to a single server"""
    stdio = await mock_stdio_client
    monkeypatch.setattr("mcp_cli.server_manager.stdio_client", stdio)

    router = await command_router
    response = await router.send_command(
        command="test command",
        target_type=CommandTarget.SINGLE,
        target="server1"
    )
    assert response.success

@pytest.mark.asyncio
async def test_group_command(command_router, monkeypatch, mock_stdio_client):
    """Test sending command to a server group"""
    stdio = await mock_stdio_client
    monkeypatch.setattr("mcp_cli.server_manager.stdio_client", stdio)

    router = await command_router
    response = await router.send_command(
        command="test command",
        target_type=CommandTarget.GROUP,
        target="group1"
    )
    assert response.success

@pytest.mark.asyncio
async def test_broadcast_command(command_router, monkeypatch, mock_stdio_client):
    """Test broadcasting command to all servers"""
    stdio = await mock_stdio_client
    monkeypatch.setattr("mcp_cli.server_manager.stdio_client", stdio)

    router = await command_router
    response = await router.send_command(
        command="test command",
        target_type=CommandTarget.BROADCAST
    )
    assert response.success

@pytest.mark.asyncio
async def test_invalid_server(command_router, monkeypatch, mock_stdio_client):
    """Test handling invalid server target"""
    stdio = await mock_stdio_client
    monkeypatch.setattr("mcp_cli.server_manager.stdio_client", stdio)

    router = await command_router
    response = await router.send_command(
        command="test command",
        target_type=CommandTarget.SINGLE,
        target="invalid_server"
    )
    assert not response.success
    assert "Server 'invalid_server' not connected" in response.error

@pytest.mark.asyncio
async def test_invalid_group(command_router, monkeypatch, mock_stdio_client):
    """Test handling invalid group target"""
    stdio = await mock_stdio_client
    monkeypatch.setattr("mcp_cli.server_manager.stdio_client", stdio)

    router = await command_router
    response = await router.send_command(
        command="test command",
        target_type=CommandTarget.GROUP,
        target="invalid_group"
    )
    assert not response.success
    assert "No connected servers in group" in response.error

@pytest.mark.asyncio
async def test_timeout_handling(command_router, monkeypatch, mock_stdio_client):
    """Test handling of command timeout"""
    stdio = await mock_stdio_client
    monkeypatch.setattr("mcp_cli.server_manager.stdio_client", stdio)

    router = await command_router
    response = await router.send_command(
        command="test command",
        target_type=CommandTarget.SINGLE,
        target="server1",
        timeout=0.1
    )
    assert response.success
