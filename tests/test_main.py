import os
import pytest
import sys
from pathlib import Path

# set the path to one folder level above this file's location
sys.path.append(str(Path(__file__).parent.parent))
import src.run_object_detection as run_object_detection


WEIGHTS = 'weights/best.pt'
IMAGE = 'data/images/mspc-naip-lax-airport.png'
TIFF = 'https://naipeuwest.blob.core.windows.net/naip/v002/ca/2022/ca_060cm_2022/33118/m_3311823_nw_11_060_20220511.tif'


def _ensure_resources_available():
    if not os.path.exists(WEIGHTS):
        pytest.skip(f"Weights not available at {WEIGHTS}")
    if not os.path.exists(IMAGE):
        pytest.skip(f"Test image not available at {IMAGE}")


def test_detections_produced():
    """Verify that running inference with the real YOLO model produces at least one detection."""
    _ensure_resources_available()

    detections = run_object_detection.run_inference(weights=WEIGHTS, image_path=IMAGE, confidence_threshold=0.0)

    assert isinstance(detections, list)
    assert len(detections) > 0, "Expected at least one detection from the model"


def test_output_arg_creates_annotated_image(tmp_path):
    """Verify that the CLI `--output` argument writes an annotated image to disk."""
    _ensure_resources_available()

    out_path = tmp_path / 'annotated.png'

    # Call the CLI entrypoint; it should save an annotated image if boxes contain coordinates
    ret = run_object_detection.main(['--weights', WEIGHTS, '--image', IMAGE, '--output', str(out_path)])
    assert ret == 0

    assert out_path.exists(), "Annotated output file was not created"
    assert out_path.stat().st_size > 0, "Annotated output file appears to be empty"


def test_confidence_levels_produce_distinct_results():
    """Verify that different confidence thresholds produce different numbers of detections."""
    _ensure_resources_available()

    low_thresh = 0.0
    high_thresh = 0.9

    low_dets = run_object_detection.run_inference(weights=WEIGHTS, image_path=IMAGE, confidence_threshold=low_thresh)
    high_dets = run_object_detection.run_inference(weights=WEIGHTS, image_path=IMAGE, confidence_threshold=high_thresh)

    low_count = len(low_dets)
    high_count = len(high_dets)

    # Sanity checks
    assert low_count >= 0
    assert high_count >= 0

    # Expect stricter threshold to produce fewer (or equal) detections, but we require a difference
    assert low_count >= high_count, "Lower threshold should not produce fewer detections than a higher threshold"
    assert low_count != high_count, f"Expected different detection counts for thresholds {low_thresh} vs {high_thresh} (got {low_count} vs {high_count})"
