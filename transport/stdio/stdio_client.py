import sys
import json
import logging
import asyncio
import subprocess
from typing import Optional, Tuple, AsyncGenerator
from contextlib import asynccontextmanager
import anyio
from .stdio_server_parameters import StdioServerParameters, get_default_environment

logger = logging.getLogger(__name__)

async def write_message(stream, data: dict) -> bool:
    """Write a JSON message to the stream."""
    try:
        json_str = json.dumps(data)
        await stream.send(f"{json_str}\n".encode('utf-8'))
        return True
    except Exception as e:
        logger.error(f"Failed to write message: {e}")
        return False

async def read_message(stream) -> Optional[dict]:
    """Read a line from the stream and parse it as JSON."""
    try:
        buffer = bytearray()
        while True:
            chunk = await stream.receive(1)
            if not chunk:
                break
                
            if chunk == b'\n':
                break
                
            buffer.extend(chunk)
            
        if not buffer:
            return None
            
        try:
            return json.loads(buffer.decode('utf-8'))
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON: {e}")
            return None
            
    except anyio.EndOfStream:
        logger.debug("Stream closed")
        return None
    except Exception as e:
        logger.error(f"Failed to read message: {e}")
        return None

async def read_stream(stream) -> AsyncGenerator[dict, None]:
    """Read messages from a stream as an async generator."""
    while True:
        try:
            message = await stream.receive()
            yield message
        except (asyncio.CancelledError, anyio.EndOfStream):
            break

async def write_stream(stream, messages: AsyncGenerator[dict, None]):
    """Write messages to a stream from an async generator."""
    async for message in messages:
        if not await write_message(stream, message):
            break

async def stdio_client(server: StdioServerParameters) -> Tuple[AsyncGenerator[dict, None], AsyncGenerator[dict, None]]:
    """Create a connection to a stdio-based server."""
    if not server.command:
        raise ValueError("Server command must not be empty")
    
    if not isinstance(server.args, (list, tuple)):
        raise ValueError("Server arguments must be a list or tuple")
    
    # Create the read and write streams
    read_stream_writer, read_stream = anyio.create_memory_object_stream(100)
    write_stream, write_stream_reader = anyio.create_memory_object_stream(100)

    # Start the subprocess with unbuffered pipes
    try:
        process = await anyio.open_process(
            [server.command, *server.args],
            env=server.env or get_default_environment(),
            stderr=sys.stderr,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            start_new_session=True
        )
    except Exception as e:
        raise RuntimeError(f"Failed to start process: {e}")

    logger.info(f"Started subprocess with PID {process.pid}")
    
    # Create tasks for reading and writing
    stdout_reader_task = asyncio.create_task(read_stream(process.stdout))
    stdin_writer_task = asyncio.create_task(write_stream(process.stdin, write_stream_reader))
    
    # Wait for ready message
    try:
        message = await asyncio.wait_for(read_stream.receive(), timeout=30.0)
        if not isinstance(message, dict) or message.get('method') != 'ready' or message.get('id') != 'init':
            raise RuntimeError("Invalid initialization message")
        logger.info(f"Server ready: {message.get('params', {}).get('server')}")
    except Exception as e:
        process.terminate()
        await process.wait()
        raise RuntimeError(f"Server initialization failed: {e}")
    
    return read_stream, write_stream
