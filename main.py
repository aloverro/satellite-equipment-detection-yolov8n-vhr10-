from typing import Optional
import argparse
import sys
import os
import shutil

# Import the refactored modules
from inference import run as run_inference
import processors


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description='Run YOLO inference on a single image.')
    parser.add_argument('--weights', type=str, default='weights/best.pt', help='Path to model weights')
    parser.add_argument('--image', type=str, default='data/images/mspc-naip-lax-airport.png', help='Path to input image or URL')
    parser.add_argument('--output', type=str, default=None, help='Optional path to save annotated image (full-size annotation will be done by post-processor)')
    parser.add_argument('--confidence', '--threshold', '-t', type=float, dest='confidence', default=0.0, help='Confidence threshold: discard detections with confidence less than this value (default 0.0)')
    parser.add_argument('--force-download', action='store_true', help='Force download of image when input is a URL (store in a temporary folder)')
    parser.add_argument('--max-side-size', type=int, default=512, help='Maximum side size (pixels) for chips produced by the preprocessor (default 512)')
    parser.add_argument('--annotate-chips', action='store_true', help='(Optional) annotate individual chips as they are processed; defaults to False. Full-size annotation is performed by post-processor.')
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)

    # Run preprocessor
    try:
        pre = processors.preprocess_image(args.image, max_side_size=args.max_side_size, force_download=args.force_download)
    except Exception as e:
        print(f"Preprocessing failed: {e}")
        return 2

    chips = pre['chips']
    chip_boxes = pre['chip_boxes']
    temp_dir = pre.get('temp_dir')

    all_detections = []

    # Run inference sequentially on each chip
    for idx, chip in enumerate(chips):
        print(f"Processing chip {idx + 1}/{len(chips)} at original position {chip_boxes[idx]}")
        detections = run_inference(weights=args.weights, image_input=chip, confidence_threshold=args.confidence)
        for det in detections:
            det['_chip_index'] = idx
            det['_chip_box'] = chip_boxes[idx]
        all_detections.extend(detections)

    # Post-process detections: aggregate, NMS, annotate full image, optionally annotate chips
    aggregated = processors.postprocess_detections(all_detections, chips, chip_boxes, pre['original_size'], pre['padded_size'], annotate_chips=args.annotate_chips, output_path=args.output)
    print(f"Post-processed detections (after NMS): {len(aggregated)} entries")

    # Clean up temporary directory if images were downloaded
    if temp_dir is not None and os.path.isdir(temp_dir):
        try:
            shutil.rmtree(temp_dir)
            print(f"Cleaned up temporary directory: {temp_dir}")
        except Exception as e:
            print(f"Failed to clean up temporary directory {temp_dir}: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())