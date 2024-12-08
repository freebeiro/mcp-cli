import asyncio
from mcp_cli.servers.server_manager import ServerManager, CommandTarget
from mcp_cli.servers.command_router import CommandRouter

async def main():
    # Initialize server manager
    server_manager = ServerManager()
    
    # Connect to servers
    await server_manager.connect_all()
    
    # Create command router
    command_router = CommandRouter(server_manager)
    
    try:
        # Test multi-tool workflow
        response = await command_router.send_command(
            command="Who scored in today's Premier League games? Add the results to the database.",
            target_type=CommandTarget.SINGLE,
            target="ollama"
        )
        
        print("\nCommand Response:")
        print(f"Success: {response.success}")
        if response.result:
            print(f"Result: {response.result}")
        if response.error:
            print(f"Error: {response.error}")
            
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        # Clean up
        await server_manager.disconnect_all()

if __name__ == "__main__":
    asyncio.run(main())
