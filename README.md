---
language: en
license: mit
tags:
- computer-vision
- object-detection
- yolov8
- satellite-imagery
- remote-sensing
- vhr-10
- geospatial
- equipment-detection
datasets:
- VHR-10
pipeline_tag: object-detection
---

# YOLOv8n Fine-tuned on VHR-10 Remote Sensing Dataset

This model is a fine-tuned YOLOv8n (nano) model trained on the NWPU VHR-10 (Very High Resolution) remote sensing dataset for detecting ground equipment and vehicles in satellite imagery.

## Model Description

This model demonstrates the feasibility of using YOLOv8 for detecting various pieces of ground equipment through satellite imagery, serving as a proof-of-concept for commercial applications in competitive intelligence, fleet monitoring, and automated equipment detection.

### Model Details

- **Model Type**: YOLOv8n (nano) - Object Detection
- **Training Dataset**: NWPU VHR-10 Remote Sensing Dataset
- **Model Size**: ~6MB (3M parameters)
- **Input Resolution**: 640x640 pixels
- **Training Duration**: 50 epochs
- **Framework**: Ultralytics YOLOv8

### Detected Classes

The model can detect 10 classes of objects commonly found in satellite imagery:

1. **airplane** - Aircraft on airfields and airports
2. **ship** - Naval vessels and boats
3. **storage_tank** - Industrial storage tanks
4. **baseball_diamond** - Baseball fields and diamonds
5. **tennis_court** - Tennis courts and facilities
6. **basketball_court** - Basketball courts
7. **ground_track_field** - Athletic tracks and fields
8. **harbor** - Harbor facilities and ports
9. **bridge** - Bridges and overpasses
10. **vehicle** - Ground vehicles and equipment

## Performance Metrics

### Overall Performance
- **mAP@0.5**: 98.0% (exceptional)
- **mAP@0.5:0.95**: 68.2% (good across IoU thresholds)
- **Overall Precision**: 94.1%
- **Overall Recall**: 96.5%
- **Inference Speed**: 9.9ms per image

### Vehicle Detection Performance (Primary Focus)
- **Vehicle F1 Score**: 79.2%
- **Vehicle Precision**: 87.5%
- **Vehicle Recall**: 81.5%
- **Vehicle mAP@0.5**: 88.8%

### Class-wise Performance (F1 Scores)
1. Ground Track Field: 100.0%
2. Airplane: 98.0%
3. Ship: 95.8%
4. Baseball Diamond: 94.3%
5. Tennis Court: 91.7%
6. Basketball Court: 90.9%
7. Bridge: 87.0%
8. Storage Tank: 84.2%
9. Harbor: 81.8%
10. Vehicle: 79.2%

## Intended Use

### Primary Applications
- **Proof-of-concept** for satellite-based equipment detection
- **Competitive intelligence** and market analysis
- **Fleet monitoring** and logistics optimization
- **Infrastructure inventory** management
- **Automated lead generation** based on equipment detection

### Commercial Potential
This model demonstrates that AI can reliably detect vehicles and equipment in satellite imagery, laying the groundwork for specialized commercial applications such as:
- Hostler detection for logistics companies
- Construction equipment monitoring
- Fleet tracking and analysis
- Market research and competitive analysis

## Usage

### Loading the Model

```python
from ultralytics import YOLO

# Load the model
model = YOLO('best.pt')

# Run inference
results = model('satellite_image.jpg')

# Process results
for result in results:
    boxes = result.boxes
    for box in boxes:
        class_id = int(box.cls)
        confidence = float(box.conf)
        print(f"Detected: {model.names[class_id]} (confidence: {confidence:.3f})")
```
### Command Line Inference (Project Script)

After cloning the repository and installing requirements:

```bash
python -m src.run_object_detection --weights weights/best.pt --image data/images/mspc-naip-lax-airport.png --output annotated.png --confidence 0.25
```

Key arguments:
- `--weights`: path to the YOLO weights (default `weights/best.pt`)
- `--image`: local path or URL (GeoTIFF requires `--force-download` for remote reading)
- `--output`: optional path to save a fully annotated image
- `--confidence` / `--threshold`: confidence threshold filter
- `--force-download`: force download when the image is a URL (required for non-TIFF URLs)
- `--max-side-size`: maximum chip side length for tiling large images (default 512)
- `--downsample-factor`: integer factor to downsample before chipping (e.g. 4, 8) to speed up inference
- `--annotate-chips`: also output per-chip annotated PNGs

You can also launch via VS Code using the provided debug configurations in `.vscode/launch.json`.


### HuggingFace Usage

```python
from huggingface_hub import hf_hub_download
from ultralytics import YOLO

# Download model from HuggingFace
model_path = hf_hub_download(
    repo_id="omgbobbyg/satellite-equipment-detection-yolov8n-vhr10",
    filename="best.pt"
)

# Load and use model
model = YOLO(model_path)
results = model('your_satellite_image.jpg')
```

## Training Details

### Dataset
- **NWPU VHR-10 Dataset**: 800 very high-resolution remote sensing images
- **Training Split**: 70% (559 images)
- **Validation Split**: 20% (160 images)  
- **Test Split**: 10% (81 images)
- **Image Sources**: Google Earth and Vaihingen dataset

### Training Configuration
- **Model**: YOLOv8n (nano)
- **Epochs**: 50
- **Batch Size**: 8 (memory optimized)
- **Image Size**: 640x640
- **Optimizer**: AdamW (auto-selected)
- **Learning Rate**: 0.000714 (auto-selected)
- **GPU**: NVIDIA RTX 4090

## Limitations and Considerations

### Strengths
- Excellent overall detection performance (98% mAP@0.5)
- High recall rate ensures minimal missed detections
- Fast inference suitable for real-time applications
- Good generalization across different object types

### Limitations
- Vehicle detection shows 49% over-prediction rate (false positives)
- Performance varies with object size and complexity
- Generic model - specialized training could significantly improve accuracy
- Limited to 10 predefined classes

### Recommendations for Production Use
- Implement post-processing filtering for specific use cases
- Consider ensemble methods for higher accuracy
- Use larger YOLOv8 variants (s/m/l) for better precision
- Develop specialized models for specific equipment types

## Citation

If you use this model in your research, please cite the original VHR-10 dataset:

```bibtex
@article{cheng2014multi,
  title={Multi-class geospatial object detection and geographic image classification based on collection of part detectors},
  author={Cheng, Gong and Han, Junwei and Zhou, Peicheng and Guo, Lei},
  journal={ISPRS Journal of Photogrammetry and Remote Sensing},
  volume={98},
  pages={119--132},
  year={2014},
  publisher={Elsevier}
}
```

## License

This model is released under the MIT License. The underlying YOLOv8 framework is licensed under GPL-3.0.
