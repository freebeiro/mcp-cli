# chat_handler.py
from llm_client import LLMClient
from tools_handler import handle_tool_call, convert_to_openai_tools, fetch_tools
from system_prompt_generator import SystemPromptGenerator

from rich import print
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
import json
import logging
import asyncio
import uuid
from typing import Dict
from rich.console import Console

async def handle_chat_mode(read_stream, write_stream, provider="openai", model="gpt-4o-mini"):
    """Enter chat mode with multi-call support for autonomous tool chaining."""
    try:
        tools = await fetch_tools(read_stream, write_stream)
        if not tools:
            print("[red]No tools available. Exiting chat mode.[/red]")
            return

        system_prompt = generate_system_prompt(tools)
        openai_tools = convert_to_openai_tools(tools)
        client = LLMClient(provider=provider, model=model)
        conversation_history = [{"role": "system", "content": system_prompt}]

        while True:
            try:
                # Change prompt to yellow
                user_message = Prompt.ask("[bold yellow]>[/bold yellow]").strip()
                if user_message.lower() in ["exit", "quit"]:
                    print(Panel("Exiting chat mode.", style="bold red"))
                    break

                # User panel in bold yellow
                user_panel_text = user_message if user_message else "[No Message]"
                print(Panel(user_panel_text, style="bold yellow", title="You"))

                conversation_history.append({"role": "user", "content": user_message})
                await process_conversation(client, conversation_history, openai_tools, read_stream, write_stream)

            except Exception as e:
                print(f"[red]Error processing message:[/red] {e}")
                continue
    except Exception as e:
        print(f"[red]Error in chat mode:[/red] {e}")


async def process_conversation(client, conversation_history, openai_tools, read_stream, write_stream):
    """Process the conversation loop with improved stream management and error handling."""
    try:
        # Set up logging for stream lifecycle events
        logging.info("Starting conversation processing")
        
        completion = await client.create_completion(
            messages=conversation_history,
            tools=openai_tools,
            stream=True,
            timeout=30  # Add configurable timeout
        )

        current_content = []
        current_tool_calls = []
        
        async with completion as stream:
            try:
                async for chunk in stream:
                    if chunk.choices[0].delta.content:
                        content_delta = chunk.choices[0].delta.content
                        current_content.append(content_delta)
                        print(content_delta, end="", flush=True)
                    
                    if chunk.choices[0].delta.tool_calls:
                        await handle_tool_call_chunk(
                            chunk.choices[0].delta.tool_calls,
                            current_tool_calls
                        )
            except asyncio.TimeoutError:
                logging.error("Stream timeout occurred")
                print("\n[red]Error: Stream timeout[/red]")
                raise
            except Exception as e:
                logging.error(f"Stream processing error: {str(e)}")
                print(f"\n[red]Error processing stream: {str(e)}[/red]")
                raise

        print()  # New line after streaming

        # Process any collected tool calls
        if current_tool_calls:
            await process_tool_calls(
                current_tool_calls,
                conversation_history,
                read_stream,
                write_stream
            )

        # Add final response to history
        if current_content:
            conversation_history.append({
                "role": "assistant",
                "content": "".join(current_content)
            })

    except Exception as e:
        logging.error(f"Conversation processing error: {str(e)}")
        print(f"\n[red]Error in conversation: {str(e)}[/red]")
        # Add error handling response to history
        conversation_history.append({
            "role": "system",
            "content": f"Error occurred: {str(e)}"
        })

async def handle_tool_call_chunk(tool_call_chunks, current_tool_calls):
    """Handle incoming tool call chunks with proper error handling."""
    for tool_call in tool_call_chunks:
        try:
            if len(current_tool_calls) <= tool_call.index:
                current_tool_calls.append({
                    "id": tool_call.id or str(uuid.uuid4()),
                    "type": tool_call.type or "function",
                    "function": {
                        "name": "",
                        "arguments": ""
                    }
                })
            
            if tool_call.function:
                current_call = current_tool_calls[tool_call.index]["function"]
                if tool_call.function.name:
                    current_call["name"] = tool_call.function.name
                if tool_call.function.arguments:
                    current_call["arguments"] += tool_call.function.arguments
                    
        except Exception as e:
            logging.error(f"Error processing tool call chunk: {str(e)}")
            raise

async def process_tool_calls(tool_calls, conversation_history, read_stream, write_stream):
    """Process collected tool calls with proper error handling and logging."""
    for tool_call in tool_calls:
        try:
            logging.info(f"Executing tool: {tool_call['function']['name']}")
            
            tool_result = await handle_tool_call(
                tool_call,
                conversation_history,
                read_stream,
                write_stream
            )
            
            conversation_history.append({
                "role": "tool",
                "content": str(tool_result),
                "tool_call_id": tool_call["id"]
            })
            
            logging.info(f"Tool execution completed: {tool_call['function']['name']}")
            
        except Exception as e:
            error_msg = f"Error executing tool {tool_call['function']['name']}: {str(e)}"
            logging.error(error_msg)
            print(f"[red]{error_msg}[/red]")
            
            # Add error to conversation history
            conversation_history.append({
                "role": "system",
                "content": f"Tool execution error: {error_msg}"
            })




def generate_system_prompt(tools):
    """
    Generate a concise system prompt for the assistant.

    This prompt is internal and not displayed to the user.
    """
    prompt_generator = SystemPromptGenerator()
    tools_json = {"tools": tools}

    system_prompt = prompt_generator.generate_prompt(tools_json)
    system_prompt += """

**GENERAL GUIDELINES:**

1. Step-by-step reasoning:
   - Analyze tasks systematically.
   - Break down complex problems into smaller, manageable parts.
   - Verify assumptions at each step to avoid errors.
   - Reflect on results to improve subsequent actions.

2. Effective tool usage:
   - Explore:
     - Identify available information and verify its structure.
     - Check assumptions and understand data relationships.
   - Iterate:
     - Start with simple queries or actions.
     - Build upon successes, adjusting based on observations.
   - Handle errors:
     - Carefully analyze error messages.
     - Use errors as a guide to refine your approach.
     - Document what went wrong and suggest fixes.

3. Clear communication:
   - Explain your reasoning and decisions at each step.
   - Share discoveries transparently with the user.
   - Outline next steps or ask clarifying questions as needed.

EXAMPLES OF BEST PRACTICES:

- Working with databases:
  - Check schema before writing queries.
  - Verify the existence of columns or tables.
  - Start with basic queries and refine based on results.

- Processing data:
  - Validate data formats and handle edge cases.
  - Ensure integrity and correctness of results.

- Accessing resources:
  - Confirm resource availability and permissions.
  - Handle missing or incomplete data gracefully.

REMEMBER:
- Be thorough and systematic.
- Each tool call should have a clear and well-explained purpose.
- Make reasonable assumptions if ambiguous.
- Minimize unnecessary user interactions by providing actionable insights.

EXAMPLES OF ASSUMPTIONS:
- Default sorting (e.g., descending order) if not specified.
- Assume basic user intentions, such as fetching top results by a common metric.
"""
    return system_prompt

async def handle_mcp_chat_mode(read_stream, write_stream, provider="ollama", model="llama3.2"):
    """MCP-compliant chat mode implementation."""
    try:
        # Discover MCP tools
        tools = await discover_mcp_tools(read_stream, write_stream)
        if not tools:
            print("[red]No MCP tools available. Exiting chat mode.[/red]")
            return

        # Generate MCP-aware system prompt
        system_prompt = generate_mcp_system_prompt(tools)
        
        # Convert to OpenAI format while preserving MCP compatibility
        openai_tools = convert_to_mcp_compatible_tools(tools)
        
        # Initialize LLM client with MCP awareness
        client = LLMClient(
            provider=provider,
            model=model,
            mcp_compatible=True
        )
        
        conversation_history = [{"role": "system", "content": system_prompt}]

        while True:
            try:
                user_message = Prompt.ask("[bold yellow]>[/bold yellow]").strip()
                if user_message.lower() in ["exit", "quit"]:
                    print(Panel("Exiting MCP chat mode.", style="bold red"))
                    break

                print(Panel(user_message, style="bold yellow", title="You"))

                conversation_history.append({"role": "user", "content": user_message})
                await process_mcp_conversation(
                    client,
                    conversation_history,
                    openai_tools,
                    read_stream,
                    write_stream
                )

            except Exception as e:
                logging.error(f"MCP chat error: {str(e)}")
                print(f"[red]Error in MCP chat: {str(e)}[/red]")
                continue

    except Exception as e:
        logging.error(f"MCP chat mode error: {str(e)}")
        print(f"[red]Error in MCP chat mode: {str(e)}[/red]")

def generate_mcp_system_prompt(tools: Dict) -> str:
    """Generate MCP-aware system prompt."""
    prompt_generator = SystemPromptGenerator()
    
    # Add MCP-specific context
    mcp_context = """
    You are an MCP-compatible assistant with access to the following servers and tools:
    
    Available MCP Servers:
    {server_list}
    
    Tool Categories:
    {tool_categories}
    
    Each tool follows the MCP protocol for:
    - Parameter validation
    - Error handling
    - Response formatting
    - Context management
    
    When using tools:
    1. Verify server availability
    2. Validate parameters against schema
    3. Handle errors according to MCP spec
    4. Process responses in MCP format
    """
    
    # Generate server and tool information
    server_list = format_server_list(tools)
    tool_categories = categorize_mcp_tools(tools)
    
    return prompt_generator.generate_prompt({
        "tools": tools,
        "mcp_context": mcp_context.format(
            server_list=server_list,
            tool_categories=tool_categories
        )
    })

def show_mcp_help(console: Console):
    """Show MCP-specific help information."""
    help_text = """
# MCP Chat Commands

## Basic Commands
- exit/quit: Exit chat mode
- help: Show this help message
- clear: Clear the screen

## Server Commands
- servers: List connected MCP servers
- tools: List available tools
- status: Show server status

## Tool Usage
Tools can be used by describing what you want to do.
The assistant will automatically select and use appropriate tools.

## Examples
- "List files in the current directory"
- "Search for TODO comments in the codebase"
- "Query the database for recent entries"
    """
    console.print(Panel(Markdown(help_text), title="MCP Help"))
