"""FastMCP server for Intelligence Agent"""
import os
import logging
from mcp.server.fastmcp import FastMCP  # Base import (just for type hints)

from src.mcp_server.tools import register_tools
from src.mcp_server.auth import APIKeyFastMCP

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_server() -> FastMCP:
    # Authentication config is initialized on import of src.auth
    api_key = os.getenv("MCP_API_KEY")
    
    # Get host and port from environment variables (only needed for Docker deployment)
    host = os.getenv("HOST", "127.0.0.1")  # Default to localhost for local dev
    port = int(os.getenv("PORT", "8000"))  # Default to 8000
    env = os.getenv("ENV", "local").lower()
    
    # Enable debug by default, only disable if explicitly set
    debug_enabled = os.getenv("DEBUG", "true").lower() != "false"
    
    mcp = APIKeyFastMCP(
        "intelligence-agent-mcp",
        stateless_http=True,
        json_response=True,
        host=host,  # Configure host for Docker compatibility
        port=port,  # Configure port for Docker compatibility
        debug=debug_enabled,  # Enable debug for hackathon, disable only if explicitly set
    )
    
    # Register MCP tools
    register_tools(mcp)

    logger.info(f"Server configured - Host: {host}, Port: {port}, Debug: {debug_enabled}, Environment: {env}")
    if api_key:
        logger.info(f"Authentication enabled with API key for {env} environment")
    
    return mcp

def main() -> None:
    server = create_server()
    server.run(transport="streamable-http")


if __name__ == "__main__":
    main()
