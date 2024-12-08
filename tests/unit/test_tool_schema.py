import pytest
from tools.tool_schema import ToolSchema, ToolParameter, ToolRegistry

def test_tool_parameter_creation():
    """Test creating a tool parameter"""
    param = ToolParameter(
        name="test_param",
        description="A test parameter",
        type="string",
        required=True
    )
    
    assert param.name == "test_param"
    assert param.description == "A test parameter"
    assert param.type == "string"
    assert param.required == True

def test_tool_schema_creation():
    """Test creating a tool schema"""
    param = ToolParameter(
        name="test_param",
        description="A test parameter",
        type="string",
        required=True
    )
    
    tool = ToolSchema(
        name="test_tool",
        description="A test tool",
        parameters=[param],
        returns={"type": "string"},
        server_name="test_server"
    )
    
    assert tool.name == "test_tool"
    assert tool.description == "A test tool"
    assert len(tool.parameters) == 1
    assert tool.parameters[0].name == "test_param"
    assert tool.server_name == "test_server"

def test_tool_registry():
    """Test tool registry functionality"""
    param = ToolParameter(
        name="test_param",
        description="A test parameter",
        type="string",
        required=True
    )
    
    tool = ToolSchema(
        name="test_tool",
        description="A test tool",
        parameters=[param],
        returns={"type": "string"},
        server_name="test_server"
    )
    
    registry = ToolRegistry()
    registry.register_tool(tool)
    
    # Test tool retrieval
    retrieved_tool = registry.get_tool("test_server.test_tool")
    assert retrieved_tool == tool
    
    # Test server tools retrieval
    server_tools = registry.get_server_tools("test_server")
    assert len(server_tools) == 1
    assert server_tools[0] == tool
    
    # Test JSON Schema conversion
    schema = registry.to_json_schema()
    assert "type" in schema
    assert "properties" in schema
    assert "test_server.test_tool" in schema["properties"]
