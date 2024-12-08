# messages/tools.py
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from mcp_cli.messages.send_message import send_message

async def send_tools_list(
    read_stream: MemoryObjectReceiveStream,
    write_stream: MemoryObjectSendStream,
) -> list:
    """Send a 'tools/list' message and return the list of tools."""
    response = await send_message(
        read_stream=read_stream,
        write_stream=write_stream,
        method="tools/list",
    )
    
    # Handle both list and dict responses
    if isinstance(response, dict):
        return response.get("result", [])
    elif isinstance(response, list):
        return response
    else:
        return []


async def send_call_tool(
    tool_name: str,
    arguments: dict,
    read_stream: MemoryObjectReceiveStream,
    write_stream: MemoryObjectSendStream,
) -> dict:
    """Send a 'tools/call' request and return the tool's response."""
    try:
        response = await send_message(
            read_stream=read_stream,
            write_stream=write_stream,
            method="tools/call",
            params={"name": tool_name, "arguments": arguments},
        )
        
        # Handle both dict and list responses
        if isinstance(response, dict):
            return response.get("result", {})
        elif isinstance(response, list):
            return {"data": response}
        else:
            return {"error": f"Invalid response type: {type(response)}"}
            
    except Exception as e:
        return {"isError": True, "error": str(e)}
