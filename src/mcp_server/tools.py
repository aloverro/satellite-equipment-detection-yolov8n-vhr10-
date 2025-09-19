"""
MCP tools for Microsoft Planetary Computer STAC API access.
"""

import asyncio
import logging
import os, sys
from pathlib import Path
from typing import Optional
from mcp.server.fastmcp import FastMCP
sys.path.append(str(Path(__file__).parent.parent))
from agents.factory import AgentFactory

from .data_models.output import IntelligenceAgentChatOutput

logger = logging.getLogger(__name__)


def validate_auth() -> None:
    """Simple auth validation - just checks if we're in production without API key."""
    env = os.getenv("ENV", "local").lower()
    api_key = os.getenv("MCP_API_KEY")
    
    if not api_key and env not in ["local", "development"]:
        raise RuntimeError(f"MCP_API_KEY required for {env} environment")
    
    if api_key:
        logger.info("API key authentication configured")
    else:
        logger.warning("Running without authentication (local development mode)")


def register_tools(mcp: FastMCP) -> None:
    """Register MCP tools for the Intelligence Agent platform."""
    
    # Validate authentication setup
    validate_auth()
    

    @mcp.tool(
        description="""Engage in a conversational chat with the Intelligence Agent.
        
        This tool allows you to interact with the Intelligence Agent, an AI-powered assistant 
        designed to help analyze satellite imagery data in response to user-posed ingelligence questions.  
        The Intelligence agent is designed to answer questions regarding the level and type of activity at one or more 
        geographic locations around the world. It can also analyze how activity levels change over time, or how
        the activity level compares between two or more locations. The agent is able to assess activity at a location by
        searching for relevant satellite imagery, passes that imagery through one or more AI detection models, and directly
        measaures the number, location, and type of objects in a scene. The agent leverages advanced natural language processing 
        capabilities to understand and respond to your queries in a conversational manner.
        
        Use this tool when you need to:
        - Determine availability of satellite imagery for specific locations or time periods
        - Understand the types, or level of activities occurring at a location
        - Understand how activity level changes over time at a location
        - Understand how the activity level compares between two or more locations
        
        Simply provide your question as input, and the Intelligence Agent will respond accordingly."""
    )
    async def intelligence_agent_chat(
        question: str
    ) -> IntelligenceAgentChatOutput:
        """
        Engage in a chat with the Intelligence Agent.
        
        Args:
            question: User's question or prompt
            
        Returns:
            IntelligenceAgentChatOutput containing the agent's response to your question.
        """

        try:
            # Local import to avoid potential circular imports at module import time
            # from agents.factory import AgentFactory

            agent_factory = AgentFactory()

            # Await the async factory method to create the agent
            intelligence_agent = await agent_factory.create_intelligence_analysis_agent()

        except Exception:
            logger.exception("Error creating intelligence analysis agent")
            print("Error creating intelligence analysis agent"
                  " - returning placeholder response")
            # Fallback to a simple placeholder response on error
            response = f"Received your question: '{question}'. The Intelligence Agent is still under development."

            return IntelligenceAgentChatOutput(response=response)
        
        try:
            # Run the agent using its streaming API and collect all streamed chunks until
            # completion, then return the assembled final text.
            result = await intelligence_agent.run(task=question)

        except Exception:
            logger.exception("Error running intelligence agent chat")
            print("Error running intelligence agent chat"
                  " - returning placeholder response")
            # Fallback to the simple placeholder response on error
            response = f"Received your question: '{question}'. The Intelligence Agent is still under development."
            return IntelligenceAgentChatOutput(response=response)    

        # Extract final response text from the agent's result
        final_message = result.messages[-1]
        if final_message.source == "Intelligence_Analysis_Agent":
            final_response = final_message.content
        else:
            final_response = f"Received your question: '{question}'. The Intelligence Agent did not produce a textual response."

        print("Final response from Intelligence Agent:", final_response)

        return IntelligenceAgentChatOutput(response=final_response)

        