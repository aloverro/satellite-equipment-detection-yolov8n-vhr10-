import io
import os
import tempfile
import shutil
import math
import urllib.request
from typing import List, Dict, Optional

from PIL import Image, ImageDraw, ImageFont

# Prefer requests if available for nicer handling, but fall back to urllib
import requests

import rasterio  # type: ignore
from rasterio.io import MemoryFile  # type: ignore


import numpy as np


def is_url(path: str) -> bool:
    return isinstance(path, str) and (path.startswith('http://') or path.startswith('https://'))


def _open_image_bytes(bytes_data: bytes):
    if Image is None:
        raise RuntimeError('Pillow is required to open images')
    return Image.open(io.BytesIO(bytes_data))


def _read_image_from_url(url: str, force_download: bool = False, temp_dir: Optional[str] = None):
    """Attempt to read an image directly from a URL into memory.

    If that fails and force_download is True, download the image into temp_dir
    and return the local path. Otherwise raise an exception.
    Returns a tuple (PIL.Image or None, downloaded_file_path or None)
    """
    # First, try to stream into memory
    try:
        if requests is not None:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            img = _open_image_bytes(resp.content)
            return img, None
        else:
            # urllib
            with urllib.request.urlopen(url, timeout=15) as r:
                data = r.read()
                img = _open_image_bytes(data)
                return img, None
    except Exception:
        # Could not read directly from URL into memory
        if not force_download:
            raise

    # If here, direct read failed and force_download is True -> attempt download to temp_dir
    if temp_dir is None:
        temp_dir = tempfile.mkdtemp(prefix='preproc_')
    else:
        os.makedirs(temp_dir, exist_ok=True)

    local_filename = os.path.join(temp_dir, os.path.basename(urllib.request.urlparse(url).path) or 'downloaded_image')
    try:
        if requests is not None:
            with requests.get(url, stream=True, timeout=15) as r:
                r.raise_for_status()
                with open(local_filename, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
        else:
            urllib.request.urlretrieve(url, local_filename)
        # Try opening the file from disk
        if Image is None:
            raise RuntimeError('Pillow is required to open images')
        img = Image.open(local_filename)
        return img, local_filename
    except Exception:
        # Clean up downloaded file if something went wrong
        try:
            if os.path.exists(local_filename):
                os.remove(local_filename)
        except Exception:
            pass
        raise


def preprocess_image(input_path_or_url: str, max_side_size: int = 512, force_download: bool = False):
    """Preprocess an input image (local path or URL) and return a dict containing:
       - chips: list of numpy uint8 arrays (H, W, 3) of equal size
       - chip_boxes: list of (x_min,y_min,x_max,y_max) in ORIGINAL image pixel coordinates
       - original_size: (width, height)
       - padded_size: (padded_width, padded_height)
       - temp_dir: path to temporary dir if a download occurred (caller should clean up)

    The function ensures the returned chips are 8-bit RGB images and does not attempt
    to process images with more than 4 bands.
    """
    temp_dir = None
    downloaded_path = None

    # Load image either from local path or from url
    # Detect GeoTIFF by file extension where possible and use rasterio when available
    if is_url(input_path_or_url):
        url_path = urllib.request.urlparse(input_path_or_url).path
        ext = os.path.splitext(url_path)[1].lower()
        is_tiff = ext in ('.tif', '.tiff')
        if is_tiff:
            # Try to stream into memory and open via MemoryFile
            try:
                if requests is not None:
                    resp = requests.get(input_path_or_url, timeout=15)
                    resp.raise_for_status()
                    with MemoryFile(resp.content) as mem:
                        with mem.open() as ds:
                            arr = ds.read()
                else:
                    with urllib.request.urlopen(input_path_or_url, timeout=15) as r:
                        data = r.read()
                        with MemoryFile(data) as mem:
                            with mem.open() as ds:
                                arr = ds.read()
            except Exception:
                # If direct streaming fails and force_download is False, raise
                if not force_download:
                    raise RuntimeError(f"Failed to read GeoTIFF from URL '{input_path_or_url}' directly into memory and --force-download not set.")
                # else download to temporary file then open with rasterio
                if temp_dir is None:
                    temp_dir = tempfile.mkdtemp(prefix='preproc_')
                local_filename = os.path.join(temp_dir, os.path.basename(url_path) or 'downloaded_image.tif')
                try:
                    if requests is not None:
                        with requests.get(input_path_or_url, stream=True, timeout=15) as r:
                            r.raise_for_status()
                            with open(local_filename, 'wb') as f:
                                for chunk in r.iter_content(chunk_size=8192):
                                    if chunk:
                                        f.write(chunk)
                    else:
                        urllib.request.urlretrieve(input_path_or_url, local_filename)
                    downloaded_path = local_filename
                    with rasterio.open(local_filename) as ds:
                        arr = ds.read()
                except Exception as e:
                    raise RuntimeError(f"Failed to download or open GeoTIFF URL '{input_path_or_url}': {e}")
        else:
            # Non-tiff URL -> fallback to PIL-based loader which may stream into memory
            try:
                img, downloaded_path = _read_image_from_url(input_path_or_url, force_download=force_download)
            except Exception as e:
                raise RuntimeError(f"Failed to read image from URL '{input_path_or_url}': {e}")
    else:
        # local file
        if not os.path.exists(input_path_or_url):
            raise FileNotFoundError(f"Input image not found: {input_path_or_url}")
        ext = os.path.splitext(input_path_or_url)[1].lower()
        is_tiff = ext in ('.tif', '.tiff')
        if is_tiff:
            with rasterio.open(input_path_or_url) as ds:
                arr = ds.read()
        else:
            img = Image.open(input_path_or_url)

    # At this point either `img` (Pillow Image) is defined, or `arr` (numpy from rasterio) is defined.
    # Convert Pillow image to numpy when needed
    if 'img' in locals():
        if Image is None:
            raise RuntimeError('Pillow is required to open images')
        arr = np.array(img)

    # If rasterio produced an array, it will be in CHW ordering (bands, rows, cols). Convert to HWC
    if arr.ndim == 3 and arr.shape[2] not in (1, 3, 4) and arr.shape[0] in (1, 2, 3, 4):
        # assume CHW -> transpose
        arr = np.transpose(arr, (1, 2, 0))

    h, w = arr.shape[0], arr.shape[1]

    # Handle band counts
    if arr.shape[2] == 1:
        # Single band: scale to 0-255 and replicate to 3 channels
        band = arr[:, :, 0].astype(np.float64)
        mn, mx = np.nanmin(band), np.nanmax(band)
        if mx == mn:
            # constant image
            scaled = np.zeros_like(band, dtype=np.uint8)
        else:
            scaled = ((band - mn) / (mx - mn) * 255.0).clip(0, 255).astype(np.uint8)
        rgb = np.stack([scaled, scaled, scaled], axis=2)
    elif arr.shape[2] == 3 or arr.shape[2] == 4:
        # Use only first three bands for 4-band images
        rgb = arr[:, :, :3].astype(np.float64)
        # Rescale per-channel to 0-255 if needed (e.g., 16-bit input)
        out = np.zeros_like(rgb, dtype=np.uint8)
        for c in range(3):
            ch = rgb[:, :, c]
            mn, mx = np.nanmin(ch), np.nanmax(ch)
            if mx == mn:
                out[:, :, c] = np.zeros_like(ch, dtype=np.uint8)
            else:
                out[:, :, c] = ((ch - mn) / (mx - mn) * 255.0).clip(0, 255).astype(np.uint8)
        rgb = out
    else:
        raise RuntimeError(f'Unexpected image array shape encountered: {arr.shape}')

    # Now rgb is H x W x 3 uint8
    if rgb.dtype != np.uint8:
        rgb = rgb.astype(np.uint8)

    # Compute tiling (equal-sized, non-overlapping chips, with size <= max_side_size)
    if max_side_size <= 0:
        raise ValueError('max_side_size must be positive')

    # Number of tiles along each axis
    nx = 1 if w <= max_side_size else math.ceil(w / max_side_size)
    ny = 1 if h <= max_side_size else math.ceil(h / max_side_size)

    tile_w = math.ceil(w / nx)
    tile_h = math.ceil(h / ny)

    # Ensure tile sizes do not exceed max_side_size (they won't due to how nx/ny computed)
    tile_w = min(tile_w, max_side_size)
    tile_h = min(tile_h, max_side_size)

    padded_w = tile_w * nx
    padded_h = tile_h * ny

    # Pad to make exact multiple of tile size (pad on right and bottom)
    if padded_w != w or padded_h != h:
        pad_w = padded_w - w
        pad_h = padded_h - h
        padded = np.zeros((padded_h, padded_w, 3), dtype=np.uint8)
        padded[0:h, 0:w, :] = rgb
    else:
        padded = rgb

    chips = []
    chip_boxes = []

    for iy in range(ny):
        for ix in range(nx):
            x0 = ix * tile_w
            y0 = iy * tile_h
            x1 = x0 + tile_w
            y1 = y0 + tile_h
            chip = padded[y0:y1, x0:x1, :].copy()
            # The chip_box should be expressed in ORIGINAL image coordinates (clipped to original dimensions)
            box_x0 = x0
            box_y0 = y0
            box_x1 = min(x1, w)
            box_y1 = min(y1, h)
            chips.append(chip)
            chip_boxes.append((box_x0, box_y0, box_x1, box_y1))

    result = {
        'chips': chips,
        'chip_boxes': chip_boxes,
        'original_size': (w, h),
        'padded_size': (padded_w, padded_h),
        'temp_dir': temp_dir,
        'downloaded_path': downloaded_path,
    }
    return result


# Helpers for NMS and IoU

def _compute_iou(box_a, box_b):
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)
    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter_area
    if union <= 0:
        return 0.0
    return inter_area / union


def _nms_boxes(boxes, scores, iou_threshold=0.5):
    if len(boxes) == 0:
        return []
    idxs = list(range(len(boxes)))
    idxs.sort(key=lambda i: scores[i], reverse=True)
    keep = []
    while idxs:
        i = idxs.pop(0)
        keep.append(i)
        remove = []
        for j in idxs:
            if _compute_iou(boxes[i], boxes[j]) > iou_threshold:
                remove.append(j)
        idxs = [x for x in idxs if x not in remove]
    return keep


def postprocess_detections(all_detections: List[Dict], chips: List[np.ndarray], chip_boxes: List[tuple], original_size: tuple, padded_size: tuple, annotate_chips: bool = False, output_path: Optional[str] = None, nms_iou: float = 0.5) -> List[Dict]:
    """Aggregate per-chip detections into full-image detections in original pixel space,
    optionally run NMS per class, annotate full-size image and optionally per-chip annotations.
    Returns the aggregated detections (list of dicts with 'name','confidence','xyxy').
    """
    w, h = original_size[0], original_size[1]
    padded_w, padded_h = padded_size

    # Map detections into global coordinates
    mapped = []
    for det in all_detections:
        det_copy = det.copy()
        if 'xyxy' in det and '_chip_box' in det:
            x0_off, y0_off, _, _ = det['_chip_box']
            x1, y1, x2, y2 = det['xyxy']
            gx1 = float(x1) + float(x0_off)
            gy1 = float(y1) + float(y0_off)
            gx2 = float(x2) + float(x0_off)
            gy2 = float(y2) + float(y0_off)
            gx1 = max(0.0, min(gx1, w))
            gy1 = max(0.0, min(gy1, h))
            gx2 = max(0.0, min(gx2, w))
            gy2 = max(0.0, min(gy2, h))
            det_copy['xyxy_global'] = (gx1, gy1, gx2, gy2)
            mapped.append(det_copy)
        else:
            mapped.append(det_copy)

    # Run NMS per class (name)
    final = []
    by_name = {}
    for idx, d in enumerate(mapped):
        if 'xyxy_global' in d:
            by_name.setdefault(d['name'], []).append(idx)

    kept_indices = set()
    for name, indices in by_name.items():
        boxes = [mapped[i]['xyxy_global'] for i in indices]
        scores = [mapped[i]['confidence'] for i in indices]
        keep = _nms_boxes(boxes, scores, iou_threshold=nms_iou)
        for k in keep:
            kept_indices.add(indices[k])

    for i in range(len(mapped)):
        if 'xyxy_global' in mapped[i]:
            if i in kept_indices:
                final.append({
                    'name': mapped[i]['name'],
                    'confidence': mapped[i]['confidence'],
                    'xyxy': mapped[i]['xyxy_global']
                })
        else:
            final.append(mapped[i])

    # Reconstruct full-size RGB image from chips
    full_padded = np.zeros((padded_h, padded_w, 3), dtype=np.uint8)
    for idx, chip in enumerate(chips):
        x0, y0, x1, y1 = chip_boxes[idx]
        ch_h, ch_w = chip.shape[0], chip.shape[1]
        px0 = int(x0)
        py0 = int(y0)
        px1 = px0 + ch_w
        py1 = py0 + ch_h
        full_padded[py0:py1, px0:px1, :] = chip

    full_rgb = full_padded[0:h, 0:w, :]

    # Annotate full-size image if requested
    if output_path is not None and Image is not None and ImageDraw is not None:
        try:
            img = Image.fromarray(full_rgb.astype('uint8'), 'RGB')
            draw = ImageDraw.Draw(img)
            try:
                font = ImageFont.load_default()
            except Exception:
                font = None

            for d in final:
                if 'xyxy' not in d:
                    continue
                x1, y1, x2, y2 = map(int, d['xyxy'])
                label = f"{d['name']} {d['confidence']:.2f}"
                draw.rectangle([x1, y1, x2, y2], outline='red', width=3)
                try:
                    text_size = draw.textsize(label, font=font) if hasattr(draw, 'textsize') else (0, 0)
                except Exception:
                    text_size = (0, 0)
                text_bg = [x1, max(y1 - text_size[1] - 4, 0), x1 + text_size[0] + 4, y1]
                draw.rectangle(text_bg, fill='red')
                draw.text((x1 + 2, max(y1 - text_size[1] - 3, 0)), label, fill='white', font=font)

            img.save(output_path)
            print(f"Full-image annotated output saved to {output_path}")
        except Exception as e:
            print(f"Failed to annotate full image: {e}")

    # Optionally annotate chips
    if annotate_chips and Image is not None and ImageDraw is not None:
        per_chip = {}
        for d in mapped:
            if '_chip_index' in d and 'xyxy' in d:
                idx = d['_chip_index']
                per_chip.setdefault(idx, []).append(d)
        for idx, dets in per_chip.items():
            try:
                chip = chips[idx]
                img_chip = Image.fromarray(chip.astype('uint8'), 'RGB')
                draw = ImageDraw.Draw(img_chip)
                for d in dets:
                    x1, y1, x2, y2 = map(int, d['xyxy'])
                    label = f"{d['name']} {d['confidence']:.2f}"
                    draw.rectangle([x1, y1, x2, y2], outline='red', width=2)
                    try:
                        text_size = draw.textsize(label, font=font) if hasattr(draw, 'textsize') else (0, 0)
                    except Exception:
                        text_size = (0, 0)
                    text_bg = [x1, max(y1 - text_size[1] - 4, 0), x1 + text_size[0] + 4, y1]
                    draw.rectangle(text_bg, fill='red')
                    draw.text((x1 + 2, max(y1 - text_size[1] - 3, 0)), label, fill='white', font=font)
                outpath = f"chip_{idx+1}_annotated.png"
                img_chip.save(outpath)
                print(f"Saved annotated chip: {outpath}")
            except Exception as e:
                print(f"Failed to annotate chip {idx}: {e}")

    return final
