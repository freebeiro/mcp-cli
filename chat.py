#!/usr/bin/env python3
import asyncio
import json
import os
from llm_client import LLMClient
from rich import print
from rich.console import Console
from typing import List, Dict, Set, Optional
from server_manager import ServerManager
from config_types import MCPConfig
from asyncio import AsyncExitStack
import logging
from dataclasses import dataclass
from mcp_utils import (
    load_mcp_config,
    verify_mcp_compatibility,
    validate_mcp_tool_schemas,
    create_mcp_aware_llm
)
from chat_session import handle_mcp_chat_session

@dataclass
class MCPServerConnection:
    """Represents a connection to an MCP server with its capabilities"""
    name: str
    type: str
    tools: Dict
    status: str
    connection: Any

async def handle_mcp_messages(server_manager: ServerManager, console: Console):
    """Handle incoming messages from all MCP servers"""
    while True:
        for conn in server_manager.connections.values():
            try:
                async for message in conn.read_stream:
                    if message.get("method") == "notification":
                        console.print(f"\n[bold yellow]{conn.name}:[/bold yellow] {message.get('params', {}).get('message')}")
            except Exception as e:
                console.print(f"\n[bold red]Error reading from {conn.name}: {str(e)}[/bold red]")

async def send_mcp_message(server_manager: ServerManager, message: Dict):
    """Send a message to all connected MCP servers"""
    for conn in server_manager.connections.values():
        try:
            await conn.write_stream.asend(message)
        except Exception as e:
            print(f"[bold red]Error sending to {conn.name}: {str(e)}[/bold red]")

async def chat():
    """Main chat function with MCP-compliant server handling."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("mcp-cli")
    
    # Initialize console
    console = Console()
    
    try:
        # Load and validate MCP configuration
        config = await load_mcp_config()
        
        # Initialize server manager with MCP support
        server_manager = ServerManager(config)
        
        # Connect to MCP servers with proper protocol handling
        async with AsyncExitStack() as stack:
            # Connect to all configured servers
            connections = await connect_mcp_servers(server_manager, console)
            
            if not connections:
                raise RuntimeError("No MCP servers available")
                
            # Discover and validate tools across all servers
            tools = await discover_mcp_tools(connections, console)
            
            # Initialize LLM with MCP tool awareness
            llm_client = create_mcp_aware_llm(tools)
            
            # Set up MCP message handler
            message_handler = await stack.enter_async_context(
                handle_mcp_messages(server_manager, console)
            )
            
            # Start chat session
            await handle_mcp_chat_session(
                llm_client=llm_client,
                server_manager=server_manager,
                console=console
            )
            
    except Exception as e:
        logger.error(f"MCP chat error: {str(e)}")
        console.print(f"[bold red]Error in MCP chat: {str(e)}[/bold red]")
    finally:
        await cleanup_mcp_connections(server_manager)

async def connect_mcp_servers(
    server_manager: ServerManager,
    console: Console
) -> List[MCPServerConnection]:
    """Connect to MCP servers with proper protocol handling."""
    connections = []
    
    for server_name, server_config in server_manager.config.servers.items():
        try:
            # Establish MCP-compliant connection
            connection = await server_manager.connect_server(
                server_name,
                server_config,
                timeout=30
            )
            
            # Verify MCP compatibility
            if await verify_mcp_compatibility(connection):
                conn_info = MCPServerConnection(
                    name=server_name,
                    type=server_config.type,
                    tools={},  # Will be populated during tool discovery
                    status="connected",
                    connection=connection
                )
                connections.append(conn_info)
                console.print(f"[green]Connected to MCP server: {server_name}[/green]")
            else:
                console.print(f"[yellow]Warning: Server {server_name} is not MCP-compatible[/yellow]")
                
        except Exception as e:
            console.print(f"[yellow]Failed to connect to {server_name}: {str(e)}[/yellow]")
            
    return connections

async def discover_mcp_tools(
    connections: List[MCPServerConnection],
    console: Console
) -> Dict:
    """Discover and validate tools from MCP servers."""
    tools = {}
    
    for conn in connections:
        try:
            # Fetch tool schemas
            server_tools = await conn.connection.get_tools()
            
            # Validate against MCP tool schema
            validated_tools = validate_mcp_tool_schemas(server_tools)
            
            # Update connection's tool information
            conn.tools = validated_tools
            tools.update(validated_tools)
            
            console.print(f"[green]Discovered {len(validated_tools)} tools from {conn.name}[/green]")
            
        except Exception as e:
            console.print(f"[yellow]Error discovering tools from {conn.name}: {str(e)}[/yellow]")
            
    return tools

def validate_mcp_tool_schemas(tools: Dict) -> Dict:
    """Validate tool schemas against MCP specification."""
    validated_tools = {}
    
    for tool_name, tool_schema in tools.items():
        try:
            # Verify required MCP schema fields
            if validate_tool_schema(tool_schema):
                validated_tools[tool_name] = tool_schema
        except Exception as e:
            logging.warning(f"Invalid tool schema for {tool_name}: {str(e)}")
            
    return validated_tools

async def cleanup_mcp_connections(server_manager: ServerManager):
    """Ensure proper cleanup of MCP connections."""
    try:
        await server_manager.cleanup()
    except Exception as e:
        logging.error(f"Error during MCP connection cleanup: {str(e)}")
