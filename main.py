from ultralytics import YOLO
import argparse
import sys
from typing import List, Dict, Optional

try:
    from PIL import Image, ImageDraw, ImageFont
except Exception:
    Image = None
    ImageDraw = None
    ImageFont = None


def run_inference(weights: str = 'weights/best.pt', image_path: str = 'data/images/mspc-naip-lax-airport.png', output_path: Optional[str] = None) -> List[Dict]:
    """Load a YOLO model from `weights`, run inference on `image_path`,
    print detections, return a list of detection dicts for testing, and
    optionally save an annotated image to `output_path`.
    """
    model = YOLO(weights)

    results = model(image_path)

    detections = []

    # We'll collect drawable boxes if coordinates are available
    drawable_boxes = []  # list of (xyxy_tuple, label_string)

    for result in results:
        boxes = result.boxes
        for box in boxes:
            class_id = int(box.cls)
            confidence = float(box.conf)
            name = model.names[class_id] if hasattr(model, 'names') else str(class_id)
            line = f"Detected: {name} (confidence: {confidence:.3f})"
            print(line)
            detections.append({"name": name, "confidence": confidence})

            # Try to extract xyxy coordinates if available for annotation
            xyxy = None
            if hasattr(box, 'xyxy'):
                try:
                    coords = box.xyxy
                    # If tensor or numpy array, try to convert to Python list
                    if hasattr(coords, 'tolist'):
                        coords = coords.tolist()
                    # coords may be nested like [[x1,y1,x2,y2]]
                    if isinstance(coords, (list, tuple)):
                        if len(coords) == 4 and all(isinstance(v, (int, float)) for v in coords):
                            xyxy = tuple(map(float, coords))
                        elif len(coords) >= 1 and isinstance(coords[0], (list, tuple)) and len(coords[0]) == 4:
                            xyxy = tuple(map(float, coords[0]))
                except Exception:
                    xyxy = None

            if xyxy is not None:
                drawable_boxes.append((xyxy, f"{name} {confidence:.2f}"))

    # If requested, try to annotate and save the image using Pillow
    if output_path is not None:
        if Image is None or ImageDraw is None:
            print("Pillow not installed; cannot save annotated image. Install pillow to enable this feature.")
        else:
            try:
                img = Image.open(image_path).convert('RGB')
                draw = ImageDraw.Draw(img)
                # optional font; fall back to default
                try:
                    font = ImageFont.load_default()
                except Exception:
                    font = None

                for xyxy, label in drawable_boxes:
                    x1, y1, x2, y2 = map(int, xyxy)
                    # draw rectangle
                    draw.rectangle([x1, y1, x2, y2], outline='red', width=3)
                    # draw label background
                    text_size = draw.textsize(label, font=font) if hasattr(draw, 'textsize') else (0, 0)
                    text_bg = [x1, max(y1 - text_size[1] - 4, 0), x1 + text_size[0] + 4, y1]
                    draw.rectangle(text_bg, fill='red')
                    # draw label text
                    draw.text((x1 + 2, max(y1 - text_size[1] - 3, 0)), label, fill='white', font=font)

                img.save(output_path)
                print(f"Annotated image saved to {output_path}")
            except Exception as e:
                print(f"Failed to save annotated image: {e}")

    return detections


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description='Run YOLO inference on a single image.')
    parser.add_argument('--weights', type=str, default='weights/best.pt', help='Path to model weights')
    parser.add_argument('--image', type=str, default='data/images/mspc-naip-lax-airport.png', help='Path to input image')
    parser.add_argument('--output', type=str, default=None, help='Optional path to save annotated image')
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    run_inference(weights=args.weights, image_path=args.image, output_path=args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())