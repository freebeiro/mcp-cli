import pytest
from pathlib import Path
from mcp_cli.servers.filesystem_server import FilesystemServer
from mcp_cli.tools.tool_schema import ToolSchema

@pytest.fixture
def server():
    """Create a FilesystemServer instance for testing"""
    config = {
        "root_paths": ["/tmp/mcp-test"],
        "max_file_size": 1024 * 1024,  # 1MB
        "allowed_extensions": ["txt", "py"]
    }
    return FilesystemServer(config)

@pytest.mark.asyncio
async def test_tool_discovery(server):
    """Test tool discovery"""
    tools = server.discover_tools()
    assert len(tools) > 0
    for tool in tools.values():
        assert isinstance(tool, ToolSchema)

@pytest.mark.asyncio
async def test_discover_tools_message(server):
    """Test discover_tools message handling"""
    message = {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "discover_tools"
    }

    handler = await server.handle_message(message)
    async with handler as agen:
        async for response in agen:
            assert response["jsonrpc"] == "2.0"
            assert response["id"] == "1"
            assert "result" in response
            assert "tools" in response["result"]
            tools = response["result"]["tools"]
            assert len(tools) == 3
            tool_names = [t["name"] for t in tools]
            assert "search" in tool_names
            assert "read" in tool_names
            assert "write" in tool_names
            break

@pytest.mark.asyncio
async def test_invalid_method(server):
    """Test handling of invalid method"""
    message = {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "invalid_method"
    }

    handler = await server.handle_message(message)
    async with handler as agen:
        async for response in agen:
            assert response["jsonrpc"] == "2.0"
            assert response["id"] == "1"
            assert "error" in response
            assert response["error"]["code"] == -32601
            assert "not found" in response["error"]["message"]
            break
