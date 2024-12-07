import pytest
import json
import asyncio
from typing import Dict, List
from command_router import CommandRouter, CommandTarget, CommandResponse, AggregatedResponse
from server_manager import ServerManager
from config_types import MCPConfig, ServerGroup
from transport.stdio.stdio_server_parameters import StdioServerParameters

class MockStreamReader:
    """Mock stream reader that returns predefined responses"""
    def __init__(self, responses: List[str]):
        self.responses = [json.dumps(r).encode() + b"\n" for r in responses]
        self.current = 0

    async def readline(self) -> bytes:
        if self.current < len(self.responses):
            response = self.responses[self.current]
            self.current += 1
            return response
        return b""

class MockStreamWriter:
    """Mock stream writer that records commands"""
    def __init__(self):
        self.commands: List[str] = []
        self.closed = False

    async def write(self, data: bytes) -> None:
        self.commands.append(data.decode().strip())

    async def drain(self) -> None:
        pass

    async def aclose(self) -> None:
        self.closed = True

@pytest.fixture
def mock_config():
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
async def server_manager(mock_config, monkeypatch):
    """Create a ServerManager with mock connections"""
    async def mock_stdio_client(params):
        responses = [{"status": "ok", "server": params.command}]
        return MockStreamReader(responses), MockStreamWriter()

    monkeypatch.setattr("server_manager.stdio_client", mock_stdio_client)
    
    manager = ServerManager(mock_config)
    await manager.connect_all()
    return manager

@pytest.fixture
def command_router(event_loop, server_manager):
    """Create a CommandRouter instance"""
    return event_loop.run_until_complete(async_command_router(server_manager))

async def async_command_router(server_manager):
    """Helper to create CommandRouter asynchronously"""
    manager = await server_manager
    return CommandRouter(manager)

@pytest.mark.asyncio
async def test_single_server_command(command_router):
    """Test sending command to a single server"""
    response = await command_router.send_command(
        command="test command",
        target_type=CommandTarget.SINGLE,
        target="server1"
    )
    
    assert response.success
    assert len(response.responses) == 1
    assert "server1" in response.responses
    assert response.responses["server1"].success
    assert response.responses["server1"].data == {"status": "ok", "server": "test1"}

@pytest.mark.asyncio
async def test_group_command(command_router):
    """Test sending command to a server group"""
    response = await command_router.send_command(
        command="test command",
        target_type=CommandTarget.GROUP,
        target="group1"
    )
    
    assert response.success
    assert len(response.responses) == 2
    assert all(name in response.responses for name in ["server1", "server2"])
    assert all(resp.success for resp in response.responses.values())

@pytest.mark.asyncio
async def test_broadcast_command(command_router):
    """Test broadcasting command to all servers"""
    response = await command_router.send_command(
        command="test command",
        target_type=CommandTarget.BROADCAST
    )
    
    assert response.success
    assert len(response.responses) == 3
    assert all(name in response.responses for name in ["server1", "server2", "server3"])
    assert all(resp.success for resp in response.responses.values())

@pytest.mark.asyncio
async def test_invalid_server(command_router):
    """Test sending command to non-existent server"""
    with pytest.raises(ValueError, match="Server 'invalid' not connected"):
        await command_router.send_command(
            command="test command",
            target_type=CommandTarget.SINGLE,
            target="invalid"
        )

@pytest.mark.asyncio
async def test_invalid_group(command_router):
    """Test sending command to non-existent group"""
    with pytest.raises(ValueError, match="No connected servers in group 'invalid'"):
        await command_router.send_command(
            command="test command",
            target_type=CommandTarget.GROUP,
            target="invalid"
        )

@pytest.mark.asyncio
async def test_timeout_handling(command_router, monkeypatch):
    """Test handling of command timeout"""
    async def slow_send_command(*args, **kwargs):
        await asyncio.sleep(0.2)  # Simulate slow response
        return CommandResponse(server_name="test", success=True)

    monkeypatch.setattr(command_router, "_send_command", slow_send_command)
    
    response = await command_router.send_command(
        command="test command",
        target_type=CommandTarget.SINGLE,
        target="server1",
        timeout=0.1
    )
    
    assert not response.success
    assert response.error == "Command timed out"
    assert all(r.error == "Timeout" for r in response.responses.values())
