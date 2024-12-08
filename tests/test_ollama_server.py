import pytest
import asyncio
from typing import Dict, Any, List
from servers.ollama_server import OllamaServer, OllamaConfig

@pytest.fixture
def server_config() -> Dict[str, Any]:
    return {
        "model": "llama2",
        "host": "http://localhost:11434",
        "temperature": 0.7
    }

@pytest.fixture
def ollama_server(server_config):
    return OllamaServer(server_config)

@pytest.mark.asyncio
async def test_discover_tools(ollama_server):
    """Test tool discovery"""
    message = {
        "jsonrpc": "2.0",
        "id": "test",
        "method": "discover_tools"
    }
    
    responses = []
    async for response in ollama_server.handle_message(message):
        responses.append(response)
    
    assert len(responses) == 1
    response = responses[0]
    
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == "test"
    assert "tools" in response["result"]
    tools = response["result"]["tools"]
    
    # Verify tools
    tool_names = {tool["name"] for tool in tools}
    assert "generate" in tool_names
    assert "chat" in tool_names

@pytest.mark.asyncio
async def test_generate(ollama_server):
    """Test text generation"""
    message = {
        "jsonrpc": "2.0",
        "id": "test",
        "method": "generate",
        "params": {
            "prompt": "Hello, how are you?",
            "temperature": 0.7
        }
    }
    
    responses = []
    async for response in ollama_server.handle_message(message):
        responses.append(response)
    
    assert len(responses) > 0
    for response in responses:
        assert response["jsonrpc"] == "2.0"
        if "method" in response:
            assert response["method"] == "stream"
            assert "chunk" in response["params"]
            assert "done" in response["params"]

@pytest.mark.asyncio
async def test_chat(ollama_server):
    """Test chat functionality"""
    message = {
        "jsonrpc": "2.0",
        "id": "test",
        "method": "chat",
        "params": {
            "messages": [
                {"role": "user", "content": "Hello, how are you?"}
            ],
            "temperature": 0.7
        }
    }
    
    responses = []
    async for response in ollama_server.handle_message(message):
        responses.append(response)
    
    assert len(responses) > 0
    for response in responses:
        assert response["jsonrpc"] == "2.0"
        if "method" in response:
            assert response["method"] == "stream"
            assert "chunk" in response["params"]
            assert "done" in response["params"]

@pytest.mark.asyncio
async def test_invalid_method(ollama_server):
    """Test handling of invalid method"""
    message = {
        "jsonrpc": "2.0",
        "id": "test",
        "method": "invalid_method"
    }
    
    responses = []
    async for response in ollama_server.handle_message(message):
        responses.append(response)
    
    assert len(responses) == 1
    response = responses[0]
    
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == "test"
    assert "error" in response
    assert response["error"]["code"] == -32601  # Method not found

@pytest.mark.asyncio
async def test_invalid_params(ollama_server):
    """Test handling of invalid parameters"""
    message = {
        "jsonrpc": "2.0",
        "id": "test",
        "method": "generate",
        "params": {}  # Missing required prompt parameter
    }
    
    responses = []
    async for response in ollama_server.handle_message(message):
        responses.append(response)
    
    assert len(responses) == 1
    response = responses[0]
    
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == "test"
    assert "error" in response
