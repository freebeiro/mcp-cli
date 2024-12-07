import sys
import json
import logging
import asyncio
import os
from typing import Optional, Dict, Any, List
from transport.stdio.stdio_client import stdio_client
from transport.stdio.stdio_server_parameters import StdioServerParameters
from transport.stdio.server_startup import start_server_with_retry
from messages.tools import send_tools_list, send_call_tool

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_config():
    """Load server configuration."""
    config_path = os.path.join(os.path.dirname(__file__), "server_config.json")
    with open(config_path) as f:
        return json.load(f)

async def start_server(name: str, params: Dict[str, Any]):
    """Start a single server and return its streams."""
    logger.info(f"Starting {name}...")
    try:
        read_stream, write_stream = await start_server_with_retry(
            StdioServerParameters(**params),
            timeout=10.0,  # Increased timeout
            retry_count=3,  # Add retries
            retry_delay=2.0  # Delay between retries
        )
        logger.info(f"Connected to {name}")
        return read_stream, write_stream
    except Exception as e:
        logger.error(f"Failed to start {name}: {e}")
        raise

async def test_tools_list(read_stream, write_stream):
    """Test fetching tools list from server."""
    logger.info("\nTesting tools/list...")
    try:
        tools = await send_tools_list(read_stream, write_stream)
        
        if isinstance(tools, list) and tools:
            logger.info("Available tools:")
            for tool in tools:
                logger.info(f"- {tool['name']}: {tool.get('description', 'No description')}")
                logger.info(f"  Parameters: {json.dumps(tool.get('inputSchema', {}), indent=2)}")
        else:
            logger.warning("No tools available")
            
        return tools
    except Exception as e:
        logger.error(f"Error fetching tools: {e}")
        return None

async def test_filesystem_tools(read_stream, write_stream):
    """Test filesystem-related tools."""
    logger.info("\nTesting filesystem tools...")
    try:
        response = await send_call_tool(
            "list_files",
            {"path": "/Users/freebeiro/Documents/fcr/claudefiles/mcp-cli"},
            read_stream,
            write_stream
        )
        logger.info(f"Filesystem response: {json.dumps(response, indent=2)}")
    except Exception as e:
        logger.error(f"Error testing filesystem: {e}")

async def test_sqlite_tools(read_stream, write_stream):
    """Test SQLite-related tools."""
    logger.info("\nTesting SQLite tools...")
    try:
        # Try to list tables
        response = await send_call_tool(
            "sqlite_query",
            {"query": "SELECT name FROM sqlite_master WHERE type='table';"},
            read_stream,
            write_stream
        )
        logger.info(f"SQLite tables: {json.dumps(response, indent=2)}")
    except Exception as e:
        logger.error(f"Error testing SQLite: {e}")

async def test_github_tools(read_stream, write_stream):
    """Test GitHub-related tools."""
    logger.info("\nTesting GitHub tools...")
    try:
        response = await send_call_tool(
            "list_repositories",
            {},
            read_stream,
            write_stream
        )
        logger.info(f"GitHub repos: {json.dumps(response, indent=2)}")
    except Exception as e:
        logger.error(f"Error testing GitHub: {e}")

async def main():
    """Main test function."""
    try:
        config = load_config()
        servers = {}
        
        # Start all servers
        active_servers = config.get('activeServers', [])
        for server_name in active_servers:
            if server_name in config['mcpServers']:
                try:
                    read, write = await start_server(server_name, config['mcpServers'][server_name])
                    servers[server_name] = (read, write)
                except Exception as e:
                    logger.error(f"Failed to start {server_name}: {e}")
        
        # Start the router server
        router_params = config['mcpServers']['router']
        router_read, router_write = await start_server('router', router_params)
        
        try:
            # Test 1: Get available tools
            tools = await test_tools_list(router_read, router_write)
            if not tools:
                logger.error("Failed to fetch tools")
                return

            # Test 2: Test filesystem tools
            await test_filesystem_tools(router_read, router_write)

            # Test 3: Test SQLite tools
            await test_sqlite_tools(router_read, router_write)

            # Test 4: Test GitHub tools
            await test_github_tools(router_read, router_write)

        finally:
            # Clean up
            for server_name, (read, write) in servers.items():
                logger.info(f"\nClosing connection to {server_name}...")
                # await client.__aexit__(None, None, None)
                
            logger.info("\nClosing connection to router...")
            # await router_client.__aexit__(None, None, None)
            
    except Exception as e:
        logger.error(f"Error in main: {e}")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
