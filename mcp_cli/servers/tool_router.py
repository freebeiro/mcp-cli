import json
from typing import Dict, Any, Optional
from . import puppeteer, sqlite

class ToolRouter:
    """Routes tool calls to appropriate handlers"""
    
    @staticmethod
    async def handle_tool(tool_response: str) -> Optional[Dict[str, Any]]:
        """Handle a tool response from the LLM"""
        try:
            # Parse the tool response
            tool_data = json.loads(tool_response)
            tool_name = tool_data.get("tool")
            parameters = tool_data.get("parameters", {})
            
            if not tool_name:
                return None
                
            # Route to appropriate tool handler
            if tool_name == "web_scrape":
                # Get match data from web scraping
                match_data = await puppeteer.scrape_scores(**parameters)
                
                # Store results in database
                if match_data and "matches" in match_data:
                    db_result = await sqlite.execute_query(
                        query="INSERT INTO matches (data) VALUES (?)",
                        params=[json.dumps(match_data)]
                    )
                    return {
                        "scrape_result": match_data,
                        "db_result": db_result
                    }
                return match_data
                
            elif tool_name == "database":
                return await sqlite.execute_query(**parameters)
            else:
                return None
                
        except json.JSONDecodeError:
            return None
        except Exception as e:
            raise Exception(f"Tool execution failed: {str(e)}")
