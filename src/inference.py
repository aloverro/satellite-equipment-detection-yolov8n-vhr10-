from typing import List, Dict, Optional

# simple model cache so repeated calls reuse loaded model weights
_model_cache = {}


def _extract_xyxy_from_box(box) -> Optional[tuple]:
    try:
        coords = box.xyxy
        if hasattr(coords, 'tolist'):
            coords = coords.tolist()
        if isinstance(coords, (list, tuple)):
            if len(coords) == 4 and all(isinstance(v, (int, float)) for v in coords):
                return tuple(map(float, coords))
            elif len(coords) >= 1 and isinstance(coords[0], (list, tuple)) and len(coords[0]) == 4:
                return tuple(map(float, coords[0]))
    except Exception:
        return None
    return None


def run(weights: str = 'weights/best.pt', image_input=None, image_path=None, confidence_threshold: float = 0.0) -> List[Dict]:
    """Run YOLO inference using `weights` on `image_input` (path, numpy array, or PIL.Image).
    Accepts legacy `image_path` keyword as an alias for `image_input`.
    Returns list of detections where each detection is a dict with at least 'name' and 'confidence'.
    When coordinates are available they are returned under the 'xyxy' key as (x1,y1,x2,y2).
    """
    # Accept legacy alias
    if image_input is None and image_path is not None:
        image_input = image_path

    # Import YOLO lazily to avoid pulling in cv2 (which requires system libs like libGL)
    model = _model_cache.get(weights)
    if model is None:
        try:
            from ultralytics import YOLO
        except Exception as e:
            # Provide a helpful error message for headless/test environments.
            raise RuntimeError(
                "Failed to import ultralytics/YOLO. This commonly happens in headless CI/test environments "
                "because OpenCV requires system libraries (e.g. libGL). Try installing 'opencv-python-headless' "
                "instead of 'opencv-python', or install the system package that provides libGL (for Debian/Ubuntu: "
                "'apt-get update && apt-get install -y libgl1'). Original error: " + str(e)
            ) from e

        model = YOLO(weights)
        _model_cache[weights] = model

    results = model(image_input, conf=confidence_threshold)

    detections = []
    for result in results:
        boxes = result.boxes
        for box in boxes:
            class_id = int(box.cls)
            confidence = float(box.conf)
            name = model.names[class_id] if hasattr(model, 'names') else str(class_id)
            det = {"name": name, "confidence": confidence}
            xyxy = _extract_xyxy_from_box(box)
            if xyxy is not None:
                det['xyxy'] = xyxy
            detections.append(det)

    return detections
