from typing import List
import logging
from rich.console import Console
from rich.prompt import Prompt
from rich.prompt import async_input
from llm_client import LLMClient
from server_manager import ServerManager

async def handle_mcp_chat_session(
    llm_client: LLMClient,
    server_manager: ServerManager,
    console: Console
):
    """Handle the MCP chat session with proper tool routing."""
    messages = []
    
    console.print("\n[bold green]MCP Chat Session Started[/bold green]")
    console.print("[dim]Type 'exit' to quit, 'help' for commands[/dim]\n")
    
    while True:
        try:
            user_input = await async_input(console, "[bold blue]You:[/bold blue] ")
            
            if user_input.lower() in ('exit', 'quit'):
                break
                
            if user_input.lower() == 'help':
                show_mcp_help(console)
                continue
                
            # Process through MCP chat handler
            await process_mcp_conversation(
                user_input=user_input,
                messages=messages,
                llm_client=llm_client,
                server_manager=server_manager,
                console=console
            )
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Chat interrupted. Type 'exit' to quit.[/yellow]")
        except Exception as e:
            console.print(f"\n[red]Error: {str(e)}[/red]")

async def process_mcp_conversation(
    user_input: str,
    messages: List,
    llm_client: LLMClient,
    server_manager: ServerManager,
    console: Console
):
    """Process MCP conversation with proper tool handling."""
    try:
        # Add user message to history
        messages.append({"role": "user", "content": user_input})
        
        # Get LLM response with tool calls
        response = await llm_client.create_completion(
            messages=messages,
            stream=True
        )
        
        # Process streaming response
        async for chunk in response:
            # Handle content streaming
            if chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content, end="", flush=True)
                
            # Handle tool calls
            if chunk.choices[0].delta.tool_calls:
                await handle_mcp_tool_calls(
                    chunk.choices[0].delta.tool_calls,
                    messages,
                    server_manager,
                    console
                )
                
    except Exception as e:
        logging.error(f"Error in MCP conversation: {str(e)}")
        raise 