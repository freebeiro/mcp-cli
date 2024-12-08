import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from tools.tool_discovery import ToolDiscovery
from tools.tool_schema import ToolSchema, ToolParameter

@pytest.fixture
def mock_server_manager():
    manager = MagicMock()
    connection = MagicMock()
    
    # Mock async generator for read_stream
    async def mock_read():
        yield {
            "id": "tool_discovery",
            "result": {
                "tools": [
                    {
                        "name": "test_tool",
                        "description": "A test tool",
                        "parameters": [
                            {
                                "name": "param1",
                                "description": "Test parameter",
                                "type": "string",
                                "required": True
                            }
                        ],
                        "returns": {"type": "string"}
                    }
                ]
            }
        }
    
    connection.read_stream = mock_read()
    connection.write_stream = AsyncMock()
    manager.get_connection.return_value = connection
    manager.connections = {"test_server": connection}
    
    return manager

@pytest.mark.asyncio
async def test_discover_server_tools(mock_server_manager):
    """Test discovering tools from a server"""
    discovery = ToolDiscovery(mock_server_manager)
    tools = await discovery.discover_server_tools("test_server")
    
    assert len(tools) == 1
    tool = tools[0]
    assert tool.name == "test_tool"
    assert len(tool.parameters) == 1
    assert tool.parameters[0].name == "param1"

@pytest.mark.asyncio
async def test_discover_all_tools(mock_server_manager):
    """Test discovering tools from all servers"""
    discovery = ToolDiscovery(mock_server_manager)
    results = await discovery.discover_all_tools()
    
    assert "test_server" in results
    assert len(results["test_server"]) == 1
    
def test_get_tool_schema(mock_server_manager):
    """Test retrieving tool schema"""
    discovery = ToolDiscovery(mock_server_manager)
    
    # Register a test tool
    tool = ToolSchema(
        name="test_tool",
        description="A test tool",
        parameters=[
            ToolParameter(
                name="param1",
                description="Test parameter",
                type="string",
                required=True
            )
        ],
        returns={"type": "string"},
        server_name="test_server"
    )
    discovery.registry.register_tool(tool)
    
    # Test retrieval
    retrieved = discovery.get_tool_schema("test_server.test_tool")
    assert retrieved == tool
    
def test_get_server_tools(mock_server_manager):
    """Test retrieving all tools for a server"""
    discovery = ToolDiscovery(mock_server_manager)
    
    # Register test tools
    tool1 = ToolSchema(
        name="tool1",
        description="Tool 1",
        parameters=[],
        returns={"type": "string"},
        server_name="test_server"
    )
    tool2 = ToolSchema(
        name="tool2",
        description="Tool 2",
        parameters=[],
        returns={"type": "string"},
        server_name="test_server"
    )
    
    discovery.registry.register_tool(tool1)
    discovery.registry.register_tool(tool2)
    
    # Test retrieval
    tools = discovery.get_server_tools("test_server")
    assert len(tools) == 2
    assert tool1 in tools
    assert tool2 in tools
