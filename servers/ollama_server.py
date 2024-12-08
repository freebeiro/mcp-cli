from typing import Dict, Any, AsyncGenerator, Optional
import json
import logging
import ollama
from pydantic import BaseModel
from messages.json_rpc_message import JSONRPCMessage
from tools.tool_schema import ToolSchema, ToolParameter

logger = logging.getLogger(__name__)

class OllamaConfig(BaseModel):
    """Configuration for Ollama server"""
    model: str = "llama2"
    host: str = "http://localhost:11434"
    context_window: int = 4096
    temperature: float = 0.7

class OllamaServer:
    """MCP-compatible Ollama server implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = OllamaConfig(**config)
        self.client = ollama.Client(host=self.config.host)
        self._initialize_tools()
    
    def _initialize_tools(self):
        """Initialize available tools"""
        self.tools = {
            "generate": ToolSchema(
                name="generate",
                description="Generate text using the Ollama model",
                parameters=[
                    ToolParameter(
                        name="prompt",
                        description="The prompt to generate from",
                        type="string",
                        required=True
                    ),
                    ToolParameter(
                        name="system_prompt",
                        description="Optional system prompt",
                        type="string",
                        required=False
                    ),
                    ToolParameter(
                        name="temperature",
                        description="Sampling temperature",
                        type="number",
                        required=False,
                        default=0.7
                    )
                ],
                returns={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "usage": {
                            "type": "object",
                            "properties": {
                                "prompt_tokens": {"type": "integer"},
                                "completion_tokens": {"type": "integer"},
                                "total_tokens": {"type": "integer"}
                            }
                        }
                    }
                },
                server_name="ollama"
            ),
            "chat": ToolSchema(
                name="chat",
                description="Chat with the Ollama model",
                parameters=[
                    ToolParameter(
                        name="messages",
                        description="List of chat messages",
                        type="array",
                        required=True,
                        items={
                            "type": "object",
                            "properties": {
                                "role": {
                                    "type": "string",
                                    "enum": ["system", "user", "assistant"]
                                },
                                "content": {"type": "string"}
                            }
                        }
                    ),
                    ToolParameter(
                        name="temperature",
                        description="Sampling temperature",
                        type="number",
                        required=False,
                        default=0.7
                    )
                ],
                returns={
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "object",
                            "properties": {
                                "role": {"type": "string"},
                                "content": {"type": "string"}
                            }
                        },
                        "usage": {
                            "type": "object",
                            "properties": {
                                "prompt_tokens": {"type": "integer"},
                                "completion_tokens": {"type": "integer"},
                                "total_tokens": {"type": "integer"}
                            }
                        }
                    }
                },
                server_name="ollama"
            )
        }
    
    async def handle_message(self, message: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """Handle incoming JSON-RPC messages"""
        try:
            msg = JSONRPCMessage(**message)
            
            if msg.method == "discover_tools":
                # Return available tools
                yield {
                    "jsonrpc": "2.0",
                    "id": msg.id,
                    "result": {
                        "tools": [tool.dict() for tool in self.tools.values()]
                    }
                }
                return
                
            if msg.method in self.tools:
                tool = self.tools[msg.method]
                params = msg.params or {}
                
                if msg.method == "generate":
                    async for response in self._handle_generate(params):
                        yield response
                        
                elif msg.method == "chat":
                    async for response in self._handle_chat(params):
                        yield response
                        
            else:
                yield {
                    "jsonrpc": "2.0",
                    "id": msg.id,
                    "error": {
                        "code": -32601,
                        "message": f"Method {msg.method} not found"
                    }
                }
                
        except Exception as e:
            logger.error(f"Error handling message: {str(e)}")
            yield {
                "jsonrpc": "2.0",
                "id": msg.id if msg else None,
                "error": {
                    "code": -32000,
                    "message": str(e)
                }
            }
    
    async def _handle_generate(self, params: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """Handle generate requests"""
        try:
            prompt = params["prompt"]
            system = params.get("system_prompt")
            temperature = params.get("temperature", self.config.temperature)
            
            response = await self.client.generate(
                model=self.config.model,
                prompt=prompt,
                system=system,
                temperature=temperature,
                stream=True
            )
            
            async for chunk in response:
                yield {
                    "jsonrpc": "2.0",
                    "method": "stream",
                    "params": {
                        "chunk": chunk["response"],
                        "done": chunk["done"]
                    }
                }
                
        except Exception as e:
            logger.error(f"Error in generate: {str(e)}")
            yield {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32000,
                    "message": str(e)
                }
            }
    
    async def _handle_chat(self, params: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """Handle chat requests"""
        try:
            messages = params["messages"]
            temperature = params.get("temperature", self.config.temperature)
            
            response = await self.client.chat(
                model=self.config.model,
                messages=messages,
                temperature=temperature,
                stream=True
            )
            
            async for chunk in response:
                yield {
                    "jsonrpc": "2.0",
                    "method": "stream",
                    "params": {
                        "chunk": chunk["message"]["content"],
                        "done": chunk["done"]
                    }
                }
                
        except Exception as e:
            logger.error(f"Error in chat: {str(e)}")
            yield {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32000,
                    "message": str(e)
                }
            }
    
    async def close(self):
        """Clean up resources"""
        # Nothing to clean up for Ollama
        pass
