"""
Output data models for MCP tools.
These models correspond 1:1 to the tools defined in tools.py.
"""

from typing import Dict, List
from pydantic import BaseModel, Field

class IntelligenceAgentChatOutput(BaseModel):
    """Output model for the intelligence_agent_chat tool."""
    response: str = Field(description="The chat response from the Intelligence Agent")

class DetectObjectsOutput(BaseModel):
    """Output model for the detect_objects tool."""
    found_objects: Dict[str,int] = Field(description="A Dictionary mapping the type of object and the number of those objects detected.")