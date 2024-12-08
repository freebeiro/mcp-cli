import pytest
import json
import asyncio
from unittest.mock import AsyncMock, patch
from mcp_cli.servers import OllamaChat, process_request

@pytest.fixture
def mock_httpx_response():
    class MockResponse:
        def __init__(self, status_code, response_text):
            self.status_code = status_code
            self._response_text = response_text

        def json(self):
            return {"response": self._response_text}

    return MockResponse(200, "Test response")

@pytest.mark.asyncio
async def test_chat_basic_response():
    # Create a proper async mock response
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"response": "Hello! How can I help you today?"}
    
    with patch("httpx.AsyncClient.post", AsyncMock(return_value=mock_response)):
        chat = OllamaChat()
        response = await chat.chat("Hello")
        assert response == "Hello! How can I help you today?"
        assert len(chat.conversation_history) == 2
        assert chat.conversation_history[0]["role"] == "user"
        assert chat.conversation_history[1]["role"] == "assistant"

@pytest.mark.asyncio
async def test_chat_tool_identification():
    # Mock response that identifies and formats tool usage
    tool_response = json.dumps({
        "tool": "sqlite_query",
        "parameters": {
            "query": "SELECT * FROM scores"
        }
    })
    
    # Create a proper async mock response
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"response": tool_response}
    
    with patch("httpx.AsyncClient.post", AsyncMock(return_value=mock_response)):
        chat = OllamaChat()
        response = await chat.chat("Show me today's scores from the database")
        assert json.loads(response)["tool"] == "sqlite_query"

@pytest.mark.asyncio
async def test_process_request_chat():
    test_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "chat",
        "params": {"message": "Hello"}
    }

    with patch("mcp_cli.servers.OllamaChat.chat", AsyncMock(return_value="Hello there!")):
        response = await process_request(test_request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert response["result"]["response"] == "Hello there!"

@pytest.mark.asyncio
async def test_process_request_unknown_method():
    test_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "unknown",
        "params": {}
    }

    response = await process_request(test_request)
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    assert "error" in response
    assert "Unknown method" in response["error"]["message"]

@pytest.mark.asyncio
async def test_chat_api_error():
    mock_response = AsyncMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    with patch("httpx.AsyncClient.post", AsyncMock(return_value=mock_response)):
        chat = OllamaChat()
        with pytest.raises(Exception) as exc_info:
            await chat.chat("Hello")
        assert "Ollama API error" in str(exc_info.value)
