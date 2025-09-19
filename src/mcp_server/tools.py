"""
MCP tools for Object Detection.
"""

import logging
import os, sys
from pathlib import Path
from typing import Optional, Annotated, Literal
from pydantic import Field

from mcp.server.fastmcp import FastMCP

from src.inference import run as run_inference
from src import processors
import shutil

from .data_models.output import DetectObjectsOutput

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
        description="""Detect objects in satellite imagery using a YOLOv8 model.

        This tool allows you to analyze satellite images to identify and locate objects of interest.
        This tool is particularly useful for detecing airplanes, and ships.

        Use this tool if you are looking to measure the level of activity at a location as measured by
        the presence of airplanes at an airport, or ships at sea or in port. 
        
        Provide this tool with the signed URL of the satellite image you wish to analyze, and the object type
        you wish to search for. The only acceptable object types are 'airplane' or 'ship'.

        The output of this model is metadata that includes a mapping between object type and the number of objects found.
        """)
    def detect_objects(
        url: Annotated[str, Field(description="The signed URL of the image to analyze")],
        object_type: Annotated[str, Field(description="The label for the object types to analyze")]
    ) -> DetectObjectsOutput:
        """
        Detect objects in satellite imagery 
        """



        WEIGHTS = 'weights/best.pt'

        ACCEPTED_OBJECT_TYPES = ['airplane', 'ship']

        if object_type not in ACCEPTED_OBJECT_TYPES:
            raise ValueError(f"Invalid object_type '{object_type}'. Must be one of {ACCEPTED_OBJECT_TYPES}")

        # Update settings based on object type:
        downsample_factor = 6 if object_type == 'ship' else 2 #6 for ship, 2 for airplanes

        # Run preprocessor
        try:
            pre = processors.preprocess_image(url, max_side_size=512, force_download=False, downsample_factor=downsample_factor)
        except Exception as e:
            logger.error(f"Preprocessing failed: {e}")
            raise RuntimeError(f"Preprocessing failed: {e}") from e

        chips = pre['chips']
        chip_boxes = pre['chip_boxes']
        temp_dir = pre.get('temp_dir')

        all_detections = []

        # Run inference sequentially on each chip
        for idx, chip in enumerate(chips):
            logger.info(f"Processing chip {idx + 1}/{len(chips)} at original position {chip_boxes[idx]}")
            detections = run_inference(weights=WEIGHTS, image_input=chip, confidence_threshold=0.2)
            for det in detections:
                det['_chip_index'] = idx
                det['_chip_box'] = chip_boxes[idx]
            all_detections.extend(detections)

        # Post-process detections: aggregate, NMS
        aggregated = processors.postprocess_detections(
            all_detections, chips, chip_boxes, pre['original_size'], pre['padded_size'], annotate_chips=False, output_path=None
        )
        logger.info(f"Post-processed detections (after NMS): {len(aggregated)} entries")

        # Count objects by type
        num_objects = 0
        for det in aggregated:
            label = det.get('name')
            if label in object_type:
                num_objects += 1
        found_objects = {object_type: num_objects}
        logger.info(f"Detected objects: {found_objects}")
        
        # Clean up temporary directory if images were downloaded
        if temp_dir is not None and os.path.isdir(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                logger.info(f"Cleaned up temporary directory: {temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary directory {temp_dir}: {e}")

        return DetectObjectsOutput(found_objects=found_objects)



        