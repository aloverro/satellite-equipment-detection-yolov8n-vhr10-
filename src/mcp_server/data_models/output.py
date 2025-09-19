"""
Output data models for MCP tools.
These models correspond 1:1 to the tools defined in tools.py.
"""

from typing import Dict, List
from pydantic import BaseModel, Field

class IntelligenceAgentChatOutput(BaseModel):
    """Output model for the intelligence_agent_chat tool."""
    response: str = Field(description="The chat response from the Intelligence Agent")