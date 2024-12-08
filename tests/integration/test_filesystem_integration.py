import pytest
import os
import tempfile
from pathlib import Path
from mcp_cli.servers.filesystem_server import FilesystemServer

@pytest.fixture
def test_dir():
    """Create a temporary directory for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create some test files
        Path(tmpdir, "test1.txt").write_text("Hello World")
        Path(tmpdir, "test2.py").write_text("print('Hello')")
        Path(tmpdir, "subdir").mkdir()
        Path(tmpdir, "subdir", "test3.txt").write_text("In subdirectory")
        yield tmpdir

@pytest.fixture
def server(test_dir):
    config = {
        "root_paths": [test_dir],
        "max_file_size": 1024 * 1024,  # 1MB
        "allowed_extensions": ["txt", "py"]
    }
    return FilesystemServer(config)

@pytest.mark.asyncio
async def test_search_files(server):
    """Test searching for files"""
    message = {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "search",
        "params": {
            "query": "*.txt",
            "max_results": 10
        }
    }
    
    handler = await server.handle_message(message)
    async with handler as agen:
        async for response in agen:
            assert response["jsonrpc"] == "2.0"
            assert response["id"] == "1"
            assert "result" in response
            results = response["result"]
            assert len(results) == 2  # test1.txt and subdir/test3.txt
            assert any(r["path"].endswith("test1.txt") for r in results)
            assert any(r["path"].endswith("test3.txt") for r in results)
            break

@pytest.mark.asyncio
async def test_read_file(server):
    """Test reading file contents"""
    message = {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "read",
        "params": {
            "path": "test1.txt"
        }
    }
    
    handler = await server.handle_message(message)
    async with handler as agen:
        async for response in agen:
            assert response["jsonrpc"] == "2.0"
            assert response["id"] == "1"
            assert "result" in response
            result = response["result"]
            assert result["content"] == "Hello World"
            assert result["total_lines"] == 1
            assert result["read_lines"]["start"] == 0
            assert result["read_lines"]["end"] == 1
            break

@pytest.mark.asyncio
async def test_write_file(server, test_dir):
    """Test writing to a file"""
    message = {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "write",
        "params": {
            "path": "new_file.txt",
            "content": "New content\n"
        }
    }
    
    handler = await server.handle_message(message)
    async with handler as agen:
        async for response in agen:
            assert response["jsonrpc"] == "2.0"
            assert response["id"] == "1"
            assert "result" in response
            result = response["result"]
            assert result["success"] is True
            assert result["bytes_written"] == 12
            break
    
    # Verify file was written
    file_path = Path(test_dir) / "new_file.txt"
    assert file_path.exists()
    assert file_path.read_text() == "New content\n"

@pytest.mark.asyncio
async def test_append_to_file(server, test_dir):
    """Test appending to a file"""
    # First write
    message1 = {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "write",
        "params": {
            "path": "append_test.txt",
            "content": "First line\n"
        }
    }
    
    handler = await server.handle_message(message1)
    async with handler as agen:
        async for response in agen:
            assert response["jsonrpc"] == "2.0"
            assert response["id"] == "1"
            assert "result" in response
            assert response["result"]["success"] is True
            break
    
    # Then append
    message2 = {
        "jsonrpc": "2.0",
        "id": "2",
        "method": "write",
        "params": {
            "path": "append_test.txt",
            "content": "Second line\n",
            "append": True
        }
    }
    
    handler = await server.handle_message(message2)
    async with handler as agen:
        async for response in agen:
            assert response["jsonrpc"] == "2.0"
            assert response["id"] == "2"
            assert "result" in response
            assert response["result"]["success"] is True
            break
    
    # Verify content
    file_path = Path(test_dir) / "append_test.txt"
    content = file_path.read_text()
    assert content == "First line\nSecond line\n"
