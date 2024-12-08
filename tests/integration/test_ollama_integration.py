import pytest
import asyncio
from servers.ollama_server import OllamaServer
from tools.tool_discovery import ToolDiscovery
from tools.tool_router import ToolRouter
from server_manager import ServerManager

@pytest.fixture
async def setup_components():
    """Set up all components for integration testing"""
    # Create server manager
    server_manager = ServerManager()
    
    # Create and register Ollama server
    ollama_config = {
        "model": "llama2",
        "host": "http://localhost:11434",
        "temperature": 0.7
    }
    ollama_server = OllamaServer(ollama_config)
    await server_manager.add_server("ollama", ollama_server)
    
    # Create tool discovery and router
    tool_discovery = ToolDiscovery(server_manager)
    tool_router = ToolRouter(server_manager, tool_discovery)
    
    # Discover tools
    await tool_discovery.discover_all_tools()
    
    yield server_manager, tool_discovery, tool_router
    
    # Cleanup
    await server_manager.close_all()

@pytest.mark.asyncio
async def test_ollama_tool_discovery(setup_components):
    """Test discovering Ollama tools"""
    _, tool_discovery, _ = setup_components
    
    # Get Ollama tools
    tools = tool_discovery.get_server_tools("ollama")
    
    # Verify tools exist
    tool_names = {t.name for t in tools}
    assert "generate" in tool_names
    assert "chat" in tool_names

@pytest.mark.asyncio
async def test_ollama_text_generation(setup_components):
    """Test generating text through tool router"""
    _, _, tool_router = setup_components
    
    result = await tool_router.call_tool("ollama.generate", {
        "prompt": "Write a haiku about coding",
        "temperature": 0.7
    })
    
    assert result is not None
    assert isinstance(result, dict)
    assert "text" in result

@pytest.mark.asyncio
async def test_ollama_chat_conversation(setup_components):
    """Test having a chat conversation"""
    _, _, tool_router = setup_components
    
    # First message
    result1 = await tool_router.call_tool("ollama.chat", {
        "messages": [
            {"role": "user", "content": "What is your name?"}
        ]
    })
    
    assert result1 is not None
    assert "message" in result1
    
    # Follow-up message
    result2 = await tool_router.call_tool("ollama.chat", {
        "messages": [
            {"role": "user", "content": "What is your name?"},
            {"role": "assistant", "content": result1["message"]["content"]},
            {"role": "user", "content": "Can you remember what I just asked you?"}
        ]
    })
    
    assert result2 is not None
    assert "message" in result2
    assert "name" in result2["message"]["content"].lower()

@pytest.mark.asyncio
async def test_parallel_tool_calls(setup_components):
    """Test calling multiple tools in parallel"""
    _, _, tool_router = setup_components
    
    results = await tool_router.call_tools_parallel({
        "ollama.generate": {
            "prompt": "Write a short poem"
        },
        "ollama.chat": {
            "messages": [
                {"role": "user", "content": "Hello!"}
            ]
        }
    })
    
    assert len(results) == 2
    assert "ollama.generate" in results
    assert "ollama.chat" in results
    assert all(r is not None for r in results.values())
