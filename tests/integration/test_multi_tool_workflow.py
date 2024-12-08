import pytest
import json
from unittest.mock import AsyncMock, Mock, patch
from mcp_cli.servers.server_manager import ServerManager, CommandTarget
from mcp_cli.servers.command_router import CommandRouter
from mcp_cli.servers.ollama_server import OllamaChat
from mcp_cli.servers import puppeteer, sqlite

@pytest.fixture
def server_manager():
    manager = Mock(spec=ServerManager)
    manager.connect_all = AsyncMock()
    
    # Create a mock OllamaChat instance with process_request method
    mock_ollama = Mock(spec=OllamaChat)
    mock_ollama.process_request = AsyncMock(return_value=json.dumps({
        "tool": "web_scrape",
        "parameters": {
            "url": "https://www.premierleague.com/results",
            "selector": ".matchDetails"
        }
    }))
    
    # Mock both get_server and connections attribute
    manager.get_server = Mock(return_value=mock_ollama)
    manager.connections = {"ollama": mock_ollama}
    
    return manager

@pytest.fixture
def command_router(server_manager):
    router = CommandRouter(server_manager)
    return router

@pytest.mark.asyncio
async def test_multi_tool_workflow(command_router, server_manager):
    """Test a workflow that involves multiple tools"""
    # Step 1: Send chat request about Premier League scores
    chat_request = {
        "method": "chat",
        "params": {
            "message": "Who scored in today's Premier League games? Add the results to the database."
        }
    }
    
    # Get the mock OllamaChat instance
    mock_ollama = server_manager.get_server("ollama")
    
    # Mock the expected tool responses
    with patch("mcp_cli.servers.puppeteer.scrape_scores", AsyncMock()) as mock_scrape, \
         patch("mcp_cli.servers.sqlite.execute_query", AsyncMock()) as mock_db:
        
        # Mock web scraping results
        mock_scrape.return_value = {
            "matches": [
                {
                    "home": "Team A",
                    "away": "Team B",
                    "score": "2-1",
                    "scorers": ["Player 1", "Player 2", "Player 3"]
                }
            ]
        }
        
        # Mock database operation
        mock_db.return_value = {"status": "success", "rows_affected": 1}
        
        # Send the request
        response = await command_router.send_command(
            command=chat_request["params"]["message"],
            target_type=CommandTarget.SINGLE,
            target="ollama"
        )
        
        # Verify the workflow
        assert response.success
        mock_ollama.process_request.assert_called_once_with({
            "method": "chat",
            "params": {
                "message": chat_request["params"]["message"]
            }
        })
        assert mock_scrape.called  # Web scraping was performed
        assert mock_db.called  # Database was updated

@pytest.mark.asyncio
async def test_error_handling(command_router, server_manager):
    """Test error handling in multi-tool workflow"""
    chat_request = {
        "method": "chat",
        "params": {
            "message": "Show me today's scores"
        }
    }
    
    # Get the mock OllamaChat instance
    mock_ollama = server_manager.get_server("ollama")
    
    # Simulate a scraping error
    with patch("mcp_cli.servers.puppeteer.scrape_scores", AsyncMock()) as mock_scrape:
        mock_scrape.side_effect = Exception("Failed to scrape data")
        
        # Send the request
        response = await command_router.send_command(
            command=chat_request["params"]["message"],
            target_type=CommandTarget.SINGLE,
            target="ollama"
        )
        
        # Verify error handling
        assert not response.success
        mock_ollama.process_request.assert_called_once_with({
            "method": "chat",
            "params": {
                "message": chat_request["params"]["message"]
            }
        })
