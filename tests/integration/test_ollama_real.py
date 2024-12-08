import pytest
import asyncio
from servers.ollama_server import OllamaServer

@pytest.mark.asyncio
async def test_ollama_generate():
    """Test real text generation with Ollama"""
    config = {
        "model": "llama2",
        "host": "http://localhost:11434",
        "temperature": 0.7
    }
    
    server = OllamaServer(config)
    
    # Test tool discovery
    discover_msg = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "discover_tools"
    }
    
    async for response in server.handle_message(discover_msg):
        tools = response["result"]["tools"]
        assert len(tools) == 2
        assert any(t["name"] == "generate" for t in tools)
        assert any(t["name"] == "chat" for t in tools)
        break
    
    # Test text generation
    generate_msg = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "generate",
        "params": {
            "prompt": "Write a haiku about coding",
            "system_prompt": "You are a creative poet.",
            "temperature": 0.7
        }
    }
    
    chunks = []
    async for response in server.handle_message(generate_msg):
        if "error" in response:
            pytest.fail(f"Error in generation: {response['error']}")
        if "params" in response:
            chunks.append(response["params"]["chunk"])
            if response["params"]["done"]:
                break
    
    generated_text = "".join(chunks)
    assert len(generated_text) > 0
    print(f"\nGenerated haiku:\n{generated_text}")

@pytest.mark.asyncio
async def test_ollama_chat():
    """Test real chat interaction with Ollama"""
    config = {
        "model": "llama2",
        "host": "http://localhost:11434",
        "temperature": 0.7
    }
    
    server = OllamaServer(config)
    
    # Test chat
    chat_msg = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "chat",
        "params": {
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "What's the best way to learn Python?"}
            ],
            "temperature": 0.7
        }
    }
    
    chunks = []
    async for response in server.handle_message(chat_msg):
        if "error" in response:
            pytest.fail(f"Error in chat: {response['error']}")
        if "params" in response:
            chunks.append(response["params"]["chunk"])
            if response["params"]["done"]:
                break
    
    chat_response = "".join(chunks)
    assert len(chat_response) > 0
    print(f"\nChat response:\n{chat_response}")

if __name__ == "__main__":
    asyncio.run(test_ollama_generate())
    asyncio.run(test_ollama_chat())
