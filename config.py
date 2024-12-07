# config.py
import json
import logging
from typing import Union, List
from transport.stdio.stdio_server_parameters import StdioServerParameters
from config_types import MCPConfig

async def load_config(config_path: str, server_name: str = None) -> Union[StdioServerParameters, List[StdioServerParameters]]:
    """Load the server configuration from a JSON file.
    
    Args:
        config_path: Path to the configuration file
        server_name: Optional server name. If None, returns all active servers
    
    Returns:
        Either a single StdioServerParameters or a list of them, depending on server_name
    """
    try:
        # Read and parse configuration
        logging.debug(f"Loading config from {config_path}")
        with open(config_path, "r") as config_file:
            config_dict = json.load(config_file)

        # Convert to MCPConfig object
        config = MCPConfig.from_dict(config_dict)

        # Return either single server or all active servers
        if server_name:
            return config.get_server_params(server_name)
        else:
            return config.get_active_server_params()

    except FileNotFoundError:
        error_msg = f"Configuration file not found: {config_path}"
        logging.error(error_msg)
        raise FileNotFoundError(error_msg)
    except json.JSONDecodeError as e:
        error_msg = f"Invalid JSON in configuration file: {e.msg}"
        logging.error(error_msg)
        raise json.JSONDecodeError(error_msg, e.doc, e.pos)
    except ValueError as e:
        logging.error(str(e))
        raise
