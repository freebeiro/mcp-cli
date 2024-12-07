import sys
import json
import logging
import asyncio
import subprocess
from typing import Optional, Tuple
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

@asynccontextmanager
async def stdio_client(server: StdioServerParameters):
    """Create a connection to a stdio-based server."""
    if not server.command:
        raise ValueError("Server command must not be empty")
    
    if not isinstance(server.args, (list, tuple)):
        raise ValueError("Server arguments must be a list or tuple")
    
    # Create the read and write streams
    read_stream_writer, read_stream = anyio.create_memory_object_stream(100)  # Increased buffer size
    write_stream, write_stream_reader = anyio.create_memory_object_stream(100)  # Increased buffer size

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
    stdout_reader_task = None
    stdin_writer_task = None
    
    async def stdout_reader():
        """Read JSON-RPC messages from stdout."""
        try:
            while True:
                if process.returncode is not None:
                    logger.debug(f"Process terminated with code {process.returncode}, stopping reader")
                    break
                    
                message = await read_message(process.stdout)
                if message is None:
                    if process.returncode is None:
                        logger.warning("Received None message but process is still running")
                        continue
                    logger.debug("End of stream, stopping reader")
                    break
                    
                logger.debug(f"Received message: {message}")
                try:
                    await read_stream_writer.send(message)
                except Exception as e:
                    logger.error(f"Failed to send message to stream: {e}")
                    break
        except Exception as e:
            logger.error(f"Error in stdout reader: {e}")
        finally:
            logger.debug("Closing read stream")
            await read_stream_writer.aclose()

    async def stdin_writer():
        """Write JSON-RPC messages to stdin."""
        try:
            async for message in write_stream_reader:
                if process.returncode is not None:
                    logger.debug("Process terminated, stopping writer")
                    break
                    
                if not await write_message(process.stdin, message):
                    logger.debug("Failed to write message, stopping writer")
                    break
        except Exception as e:
            logger.error(f"Error in stdin writer: {e}")
        finally:
            logger.debug("Closing write stream")
            await write_stream_reader.aclose()
            if process.stdin:
                await process.stdin.aclose()

    async def cleanup_process():
        """Clean up the subprocess."""
        try:
            # Cancel reader/writer tasks
            if stdout_reader_task and not stdout_reader_task.done():
                stdout_reader_task.cancel()
                try:
                    await stdout_reader_task
                except asyncio.CancelledError:
                    pass
                    
            if stdin_writer_task and not stdin_writer_task.done():
                stdin_writer_task.cancel()
                try:
                    await stdin_writer_task
                except asyncio.CancelledError:
                    pass
                    
            # Terminate process
            if process.returncode is None:
                logger.debug("Terminating process")
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=30.0)  # Increased timeout
                except asyncio.TimeoutError:
                    logger.debug("Force killing process")
                    process.kill()
                    await process.wait()
                    
        except Exception as e:
            logger.error(f"Error cleaning up process: {e}")

    try:
        # Start reader/writer tasks
        stdout_reader_task = asyncio.create_task(stdout_reader())
        stdin_writer_task = asyncio.create_task(stdin_writer())
        
        # Wait for ready message with timeout
        try:
            logger.debug("Waiting for ready message")
            message = await asyncio.wait_for(read_stream.receive(), timeout=30.0)  # Increased timeout
            logger.debug(f"Got initialization message: {message}")
            
            if not isinstance(message, dict):
                raise RuntimeError("Invalid message format")
                
            if message.get('method') != 'ready' or message.get('id') != 'init':
                raise RuntimeError("Unexpected message type")
                
            logger.info(f"Server ready: {message.get('params', {}).get('server')}")
            
            # Yield streams for client use
            yield read_stream, write_stream
            
        except asyncio.TimeoutError:
            raise RuntimeError("Server initialization timeout")
        except Exception as e:
            raise RuntimeError(f"Server initialization failed: {e}")
            
    except Exception as e:
        logger.error(f"Server connection failed: {e}")
        raise
        
    finally:
        await cleanup_process()
