import sys
import json
import logging
import asyncio
import os
from typing import Dict, List, Optional
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "llama2")

class OllamaChat:
    def __init__(self):
        self.conversation_history = []
        self.available_tools = {
            "sqlite_query": {
                "description": "Execute SQL queries on the claudefiles database",
                "parameters": {
                    "query": "SQL query to execute"
                }
            },
            "web_scrape": {
                "description": "Scrape data from a webpage using Puppeteer",
                "parameters": {
                    "url": "URL to scrape",
                    "selector": "CSS selector to extract data"
                }
            }
        }

    async def chat(self, message: str) -> str:
        # Add user message to history
        self.conversation_history.append({"role": "user", "content": message})
        
        # Create system prompt with tool descriptions
        system_prompt = f"""You are a helpful AI assistant with access to the following tools:
{json.dumps(self.available_tools, indent=2)}

When a user's request requires using these tools:
1. Identify which tool(s) to use
2. Format your response as a JSON object with:
   {{"tool": "tool_name", "parameters": {...}}}

Otherwise, respond conversationally as a helpful assistant.
"""
        
        # Build full prompt
        full_prompt = system_prompt + "\n\n" + "\n".join(
            f"{msg['role']}: {msg['content']}" 
            for msg in self.conversation_history
        )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f'{OLLAMA_HOST}/api/generate',
                json={
                    'model': MODEL_NAME,
                    'prompt': full_prompt,
                    'stream': False
                }
            )
            
            if response.status_code == 200:
                response_data = await response.json()
                ai_response = response_data['response']
                self.conversation_history.append({"role": "assistant", "content": ai_response})
                return ai_response
            else:
                raise Exception(f"Ollama API error: {response.text}")

async def process_request(request: Dict) -> Dict:
    """Process incoming JSON-RPC request."""
    method = request.get("method")
    params = request.get("params", {})
    
    chat = OllamaChat()
    
    if method == "chat":
        message = params.get("message", "")
        response = await chat.chat(message)
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": {"response": response}
        }
    else:
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "error": {"message": f"Unknown method: {method}"}
        }

async def main():
    """Main server loop."""
    while True:
        try:
            request = json.loads(await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline))
            response = await process_request(request)
            print(json.dumps(response), flush=True)
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            error_response = {
                "jsonrpc": "2.0",
                "id": request.get("id") if "request" in locals() else None,
                "error": {"message": str(e)}
            }
            print(json.dumps(error_response), flush=True)

if __name__ == '__main__':
    asyncio.run(main())
