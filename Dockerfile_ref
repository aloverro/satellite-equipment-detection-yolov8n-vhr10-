# Dockerfile for satellite-equipment-detection-yolov8n-vhr10-
# Builds an amd64 Linux container with Python 3.12.
# Uses a slim base image and installs system dependencies required by
# rasterio, ultralytics and OpenCV (headless). The image installs
# Python requirements from requirements.txt and copies the application.

FROM --platform=linux/amd64 python:3.12-slim

# Keep Python output unbuffered (useful for logs) and tell pip not to cache packages
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

# Install system packages needed by some Python packages (rasterio, gdal, headless opencv, etc.)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       gcc \
       gdal-bin \
       libgdal-dev \
       libgl1 \
       libglib2.0-0 \
       libsm6 \
       libxrender1 \
       libxext6 \
       ca-certificates \
       curl \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Upgrade pip and wheel first to improve wheel installs
RUN pip install --upgrade pip setuptools wheel

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . /app

# Default command runs the CLI. Override at runtime with additional args.
CMD ["python", "main.py"]
