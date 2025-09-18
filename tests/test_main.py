import sys
import types
import pytest

import main


class DummyBox:
    def __init__(self, cls, conf):
        self.cls = cls
        self.conf = conf


class DummyResult:
    def __init__(self, boxes):
        self.boxes = boxes


class DummyModel:
    def __init__(self, weights):
        # expose names like the real model
        self.names = {0: 'truck', 1: 'car'}
        self.loaded_weights = weights

    def __call__(self, image_path):
        # Return a list with one DummyResult containing two boxes
        return [
            DummyResult([
                DummyBox(0, 0.9234),
                DummyBox(1, 0.4567),
            ])
        ]


def test_run_inference_monkeypatched(monkeypatch, capsys):
    # Replace the YOLO class in the main module with DummyModel
    monkeypatch.setattr(main, 'YOLO', DummyModel)

    detections = main.run_inference(weights='weights/mock.pt', image_path='images/mock.png')

    captured = capsys.readouterr()
    stdout = captured.out.strip().splitlines()

    assert any('Detected: truck (confidence: 0.923)' in line for line in stdout)
    assert any('Detected: car (confidence: 0.457)' in line for line in stdout)

    # Verify structured return value
    assert len(detections) == 2
    assert detections[0]['name'] == 'truck'
    assert pytest.approx(detections[0]['confidence'], rel=1e-3) == 0.9234
    assert detections[1]['name'] == 'car'


def test_cli_entrypoint_parses_args(monkeypatch, capsys):
    monkeypatch.setattr(main, 'YOLO', DummyModel)

    # Simulate CLI invocation with custom args
    ret = main.main(['--weights', 'weights/foo.pt', '--image', 'images/foo.png'])

    # main() should return an int exit code
    assert ret == 0

    captured = capsys.readouterr()
    stdout = captured.out.strip()
    assert 'Detected: truck (confidence: 0.923)' in stdout
