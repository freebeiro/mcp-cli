import sys
import json
import logging
import asyncio
import os
from typing import Optional, Dict, Any, List
from command_router import CommandTarget, CommandRouter
from server_manager import ServerManager

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_config(config_path=None):
    """Load server configuration."""
    if config_path is None:
        config_path = os.path.join(os.path.dirname(__file__), "server_config.json")
    with open(config_path) as f:
        return json.load(f)

class MCPRouter:
    def __init__(self, name: str, config_path=None):
        self.name = name
        self.running = False
        config = load_config(config_path)
        self.server_manager = ServerManager(config)
        self.command_router = CommandRouter(self.server_manager)
        
    async def read_message(self) -> Optional[dict]:
        """Read a JSON message from stdin."""
        try:
            line = await asyncio.get_event_loop().run_in_executor(
                None, sys.stdin.buffer.readline
            )
            if not line:
                return None
                
            return json.loads(line.decode('utf-8'))
        except Exception as e:
            logger.error(f"Failed to read message: {e}")
            return None
            
    async def write_message(self, message: dict) -> bool:
        """Write a JSON message to stdout."""
        try:
            logger.debug(f"Writing message: {message}")
            line = json.dumps(message).encode('utf-8') + b'\n'
            await asyncio.get_event_loop().run_in_executor(
                None, sys.stdout.buffer.write, line
            )
            await asyncio.get_event_loop().run_in_executor(
                None, sys.stdout.buffer.flush
            )
            logger.debug("Message written and flushed")
            return True
        except Exception as e:
            logger.error(f"Failed to write message: {e}")
            return False
            
    async def handle_command(self, request: dict) -> dict:
        """Handle an incoming command request."""
        try:
            if request['method'] == 'ready':
                return {
                    'jsonrpc': '2.0',
                    'method': 'ready',
                    'id': request['id'],
                    'params': {'server': self.name}
                }
                
            if request['method'] == 'tools/list':
                # Get tools from all active servers
                tools = []
                active_servers = self.server_manager.config.get('activeServers', [])
                
                for server in active_servers:
                    try:
                        response = await self.command_router.send_command(
                            command='tools/list',
                            target_type=CommandTarget.SINGLE,
                            target=server
                        )
                        if isinstance(response, dict) and 'tools' in response:
                            tools.extend(response['tools'])
                        elif isinstance(response, list):
                            tools.extend(response)
                    except Exception as e:
                        logger.error(f"Error getting tools from {server}: {e}")
                
                return {
                    'jsonrpc': '2.0',
                    'id': request['id'],
                    'result': tools
                }
                
            if request['method'] == 'tools/call':
                # Route tool call to appropriate server
                tool_name = request['params']['name']
                tool_args = request['params']['arguments']
                
                # Find server that has this tool
                target_server = None
                for server in self.server_manager.config.get('activeServers', []):
                    try:
                        tools = await self.command_router.send_command(
                            command='tools/list',
                            target_type=CommandTarget.SINGLE,
                            target=server
                        )
                        if isinstance(tools, dict):
                            tools = tools.get('tools', [])
                        if any(t['name'] == tool_name for t in tools):
                            target_server = server
                            break
                    except Exception:
                        continue
                
                if not target_server:
                    raise Exception(f"No server found for tool: {tool_name}")
                
                # Send command to target server
                response = await self.command_router.send_command(
                    command='tools/call',
                    target_type=CommandTarget.SINGLE,
                    target=target_server,
                    params={'name': tool_name, 'arguments': tool_args}
                )
                
                return {
                    'jsonrpc': '2.0',
                    'id': request['id'],
                    'result': response
                }
            
            raise Exception(f"Unknown method: {request['method']}")
            
        except Exception as e:
            logger.error(f"Error handling command: {e}")
            return {
                'jsonrpc': '2.0',
                'id': request['id'],
                'error': {
                    'code': -32000,
                    'message': str(e)
                }
            }
            
    async def run(self):
        """Run the router."""
        self.running = True
        
        logger.debug("Router starting, sending ready message...")
        # Send ready message
        await self.write_message({
            'jsonrpc': '2.0',
            'method': 'ready',
            'id': 'init',
            'params': {'server': self.name}
        })
        logger.debug("Ready message sent")
        
        while self.running:
            logger.debug("Waiting for next message...")
            request = await self.read_message()
            if not request:
                logger.debug("No message received, breaking loop")
                break
                
            logger.debug(f"Handling request: {request}")
            response = await self.handle_command(request)
            logger.debug(f"Sending response: {response}")
            if not await self.write_message(response):
                logger.debug("Failed to write response, breaking loop")
                break

async def main():
    if len(sys.argv) < 2:
        print("Usage: python example.py <server_name> [config_path]")
        return

    server_name = sys.argv[1]
    config_path = sys.argv[2] if len(sys.argv) > 2 else None
    router = MCPRouter(server_name, config_path)
    await router.run()

if __name__ == '__main__':
    asyncio.run(main())
