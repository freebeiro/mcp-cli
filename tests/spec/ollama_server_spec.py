import pytest
import asyncio
from typing import Dict, Any, List
from servers.ollama_server import OllamaServer, OllamaConfig

class TestOllamaServerBehavior:
    """
    Behavior Specification for the Ollama MCP Server
    
    The Ollama server should:
    1. Implement the MCP protocol for tool discovery and execution
    2. Provide streaming responses for generate and chat methods
    3. Handle errors gracefully and return appropriate JSON-RPC errors
    4. Maintain connection state and cleanup resources properly
    """
    
    @pytest.fixture
    def server_config(self) -> Dict[str, Any]:
        """Given a standard server configuration"""
        return {
            "model": "llama2",
            "host": "http://localhost:11434",
            "temperature": 0.7
        }
    
    @pytest.fixture
    def server(self, server_config) -> OllamaServer:
        """And a running Ollama server"""
        return OllamaServer(server_config)
    
    class DescribeToolDiscovery:
        """When discovering available tools"""
        
        @pytest.mark.asyncio
        async def it_should_return_all_available_tools(self, server):
            """Then it should return a list of all available tools"""
            message = {
                "jsonrpc": "2.0",
                "id": "test_discovery",
                "method": "discover_tools"
            }
            
            responses = [r async for r in server.handle_message(message)]
            assert len(responses) == 1
            
            tools = responses[0]["result"]["tools"]
            tool_names = {t["name"] for t in tools}
            
            # Should have both generate and chat tools
            assert "generate" in tool_names
            assert "chat" in tool_names
            
            # Tools should have proper schema
            for tool in tools:
                assert "name" in tool
                assert "description" in tool
                assert "parameters" in tool
                assert "returns" in tool
    
    class DescribeTextGeneration:
        """When generating text"""
        
        @pytest.mark.asyncio
        async def it_should_stream_responses(self, server):
            """Then it should stream chunks of generated text"""
            message = {
                "jsonrpc": "2.0",
                "id": "test_generate",
                "method": "generate",
                "params": {
                    "prompt": "Hello, how are you?",
                    "temperature": 0.7
                }
            }
            
            responses = []
            async for response in server.handle_message(message):
                responses.append(response)
                
                # Each streaming response should have proper format
                if "method" in response:
                    assert response["method"] == "stream"
                    assert "chunk" in response["params"]
                    assert isinstance(response["params"]["chunk"], str)
                    assert "done" in response["params"]
                    assert isinstance(response["params"]["done"], bool)
            
            # Should receive multiple chunks
            assert len(responses) > 1
            # Last response should be marked as done
            assert responses[-1]["params"]["done"] == True
    
    class DescribeChatInteraction:
        """When having a chat conversation"""
        
        @pytest.mark.asyncio
        async def it_should_maintain_conversation_context(self, server):
            """Then it should maintain context across messages"""
            messages = [
                {"role": "user", "content": "My name is Alice."},
                {"role": "assistant", "content": "Hello Alice, nice to meet you!"},
                {"role": "user", "content": "What's my name?"}
            ]
            
            message = {
                "jsonrpc": "2.0",
                "id": "test_chat",
                "method": "chat",
                "params": {"messages": messages}
            }
            
            responses = []
            async for response in server.handle_message(message):
                responses.append(response)
                if "method" in response:
                    content = response["params"]["chunk"].lower()
                    # Response should contain the name from context
                    if "alice" in content:
                        break
            
            assert any("alice" in r["params"]["chunk"].lower() 
                      for r in responses if "method" in r)
    
    class DescribeErrorHandling:
        """When handling errors"""
        
        @pytest.mark.asyncio
        async def it_should_handle_invalid_methods(self, server):
            """Then it should return proper error for invalid methods"""
            message = {
                "jsonrpc": "2.0",
                "id": "test_error",
                "method": "invalid_method"
            }
            
            responses = [r async for r in server.handle_message(message)]
            assert len(responses) == 1
            
            error = responses[0]["error"]
            assert error["code"] == -32601  # Method not found
            assert "message" in error
        
        @pytest.mark.asyncio
        async def it_should_handle_invalid_parameters(self, server):
            """Then it should return proper error for invalid parameters"""
            message = {
                "jsonrpc": "2.0",
                "id": "test_error",
                "method": "generate",
                "params": {}  # Missing required prompt
            }
            
            responses = [r async for r in server.handle_message(message)]
            assert len(responses) == 1
            
            error = responses[0]["error"]
            assert "message" in error
            assert "prompt" in error["message"].lower()  # Error about missing prompt
    
    class DescribeResourceManagement:
        """When managing server resources"""
        
        @pytest.mark.asyncio
        async def it_should_cleanup_properly(self, server):
            """Then it should clean up resources on close"""
            # Start some operations
            message = {
                "jsonrpc": "2.0",
                "id": "test_cleanup",
                "method": "generate",
                "params": {"prompt": "test"}
            }
            
            # Cancel mid-generation
            task = asyncio.create_task(server.handle_message(message).__anext__())
            await asyncio.sleep(0.1)
            task.cancel()
            
            # Should close cleanly
            try:
                await server.close()
            except Exception as e:
                pytest.fail(f"Failed to clean up: {e}")
