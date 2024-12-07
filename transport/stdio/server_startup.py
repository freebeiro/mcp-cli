"""Server startup utilities for stdio-based servers."""

import asyncio
import logging
from typing import Tuple, Optional, Dict, Any
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from .stdio_client import stdio_client
from .stdio_server_parameters import StdioServerParameters

logger = logging.getLogger(__name__)

async def wait_for_server_ready(
    read_stream: MemoryObjectReceiveStream,
    timeout: float = 10.0,
    retry_count: int = 3,
    retry_delay: float = 2.0
) -> Optional[Dict[str, Any]]:
    """
    Wait for server ready message with retries.
    
    Args:
        read_stream: Stream to read messages from
        timeout: Timeout in seconds for each attempt
        retry_count: Number of retry attempts
        retry_delay: Delay between retries in seconds
        
    Returns:
        The ready message if successful, None otherwise
    """
    for attempt in range(retry_count):
        try:
            logger.debug(f"Waiting for ready message (attempt {attempt + 1}/{retry_count})")
            message = await asyncio.wait_for(read_stream.receive(), timeout=timeout)
            
            if not isinstance(message, dict):
                logger.error(f"Invalid message format: {message}")
                continue
                
            if message.get('method') != 'ready' or message.get('id') != 'init':
                logger.error(f"Unexpected message type: {message}")
                continue
                
            logger.info(f"Server ready: {message.get('params', {}).get('server')}")
            return message
            
        except asyncio.TimeoutError:
            logger.warning(f"Server initialization timeout (attempt {attempt + 1}/{retry_count})")
            if attempt < retry_count - 1:
                await asyncio.sleep(retry_delay)
            continue
            
        except Exception as e:
            logger.error(f"Error waiting for server: {e}")
            if attempt < retry_count - 1:
                await asyncio.sleep(retry_delay)
            continue
            
    return None

async def start_server_with_retry(
    server: StdioServerParameters,
    timeout: float = 10.0,
    retry_count: int = 3,
    retry_delay: float = 2.0
) -> Tuple[Any, MemoryObjectReceiveStream, MemoryObjectSendStream]:
    """
    Start a server with retry logic.
    
    Args:
        server: Server parameters
        timeout: Timeout in seconds for each attempt
        retry_count: Number of retry attempts
        retry_delay: Delay between retries in seconds
        
    Returns:
        Tuple of (client, read_stream, write_stream)
        
    Raises:
        RuntimeError if server fails to start after all retries
    """
    for attempt in range(retry_count):
        try:
            async with stdio_client(server) as (read_stream, write_stream):
                # Wait for ready message
                ready_message = await wait_for_server_ready(
                    read_stream,
                    timeout=timeout,
                    retry_count=1  # Only one retry per client attempt
                )
                
                if ready_message:
                    return read_stream, write_stream
                    
        except Exception as e:
            logger.error(f"Failed to start server (attempt {attempt + 1}/{retry_count}): {e}")
            if attempt < retry_count - 1:
                await asyncio.sleep(retry_delay)
            continue
            
    raise RuntimeError(f"Failed to start server after {retry_count} attempts")
