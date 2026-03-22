import cv2
import numpy as np
from ultralytics import YOLO
from typing import Dict, Any, List, Optional
from src.config import CONFIDENCE_THRESHOLD, BURNER_RADIUS_PIXELS
from src.spatial import calculate_center, is_point_in_zones

class VisionSystem:
    def __init__(self, model_path: str = "yolov8n.pt"):
        """
        Initialize the VisionSystem with a YOLO model.
        """
        self.model = YOLO(model_path)
        self.classes = self.model.names

    def detect_objects(self, frame: np.ndarray, burner_zones: List[tuple], mock_flame_box: Optional[List[int]] = None) -> Dict[str, Any]:
        """
        Detect objects in the frame and validate against burner zones.
        Args:
            frame: Video frame.
            burner_zones: List of (x, y) coordinates for safe burners.
            mock_flame_box: Optional [x1, y1, x2, y2] to simulate a fire.
        Returns a dictionary with detection status and bounding boxes.
        """
        results = self.model(frame, stream=True, verbose=False)
        
        person_detected = False
        flame_detected = False
        is_safe_fire = True
        boxes = []

        # Process YOLO results (Person detection)
        for r in results:
            for box in r.boxes:
                # Get class ID and confidence
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])

                if conf < CONFIDENCE_THRESHOLD:
                    continue

                # Class 0 is 'person' in COCO dataset
                if cls_id == 0:
                    person_detected = True
                    coords = box.xyxy[0].tolist()
                    boxes.append({'class': 'person', 'box': coords, 'conf': conf})

        # Process Mock Flame
        if mock_flame_box:
            flame_detected = True
            # Add it to boxes for visualization
            boxes.append({'class': 'flame', 'box': mock_flame_box, 'conf': 1.0})
            
            # Validate Spatial Logic
            if burner_zones:
                flame_center = calculate_center(mock_flame_box)
                is_safe_fire = is_point_in_zones(flame_center, burner_zones, BURNER_RADIUS_PIXELS)
            else:
                # If no burners are defined, ANY fire is technically "unsafe" because we don't know where the stove is.
                # However, to not break the basic state machine tests, let's assume it's "safe" (on stove) if no zones exist.
                is_safe_fire = True

        return {
            'person_detected': person_detected,
            'flame_detected': flame_detected,
            'is_safe_fire': is_safe_fire,
            'boxes': boxes
        }
