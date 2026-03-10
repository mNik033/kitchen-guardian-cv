from typing import Literal, List, Optional
from src.config import GROWTH_WARNING_MULTIPLIER, GROWTH_CRITICAL_MULTIPLIER, BASELINE_FRAMES

class FlameTracker:
    def __init__(self):
        """
        Initialize the FlameTracker to monitor the size of detected flames.
        """
        self.baseline_areas = []
        self.baseline_area = 0.0
        self.is_baseline_established = False

    def _calculate_area(self, box: list) -> float:
        """
        Calculate the area of a bounding box [x1, y1, x2, y2].
        """
        x1, y1, x2, y2 = box
        width = x2 - x1
        height = y2 - y1
        return float(width * height)

    def update(self, flame_boxes: List[dict]) -> Literal["SAFE", "GROWTH_WARNING", "GROWTH_CRITICAL"]:
        """
        Track flame growth based on the bounding boxes.
        Aggregate all flame boxes (in case of multiple fires) into a total current area.
        """
        if not flame_boxes:
            # If no flames are detected, forget the baseline entirely.
            self.reset()
            return "SAFE"

        # Calculate total area of all detected flames in the current frame
        total_current_area = sum(self._calculate_area(item['box']) for item in flame_boxes)

        # Establish baseline if not done
        if not self.is_baseline_established:
            self.baseline_areas.append(total_current_area)
            if len(self.baseline_areas) >= BASELINE_FRAMES:
                # Average the collected areas to set the baseline
                self.baseline_area = sum(self.baseline_areas) / len(self.baseline_areas)
                self.is_baseline_established = True
            return "SAFE"

        # Baseline is established, check for dangerous growth
        if self.baseline_area <= 0:
            return "SAFE" # Avoid division by zero edge cases

        growth_ratio = total_current_area / self.baseline_area

        if growth_ratio >= GROWTH_CRITICAL_MULTIPLIER:
            return "GROWTH_CRITICAL"
        elif growth_ratio >= GROWTH_WARNING_MULTIPLIER:
            return "GROWTH_WARNING"
        
        return "SAFE"

    def reset(self):
        """
        Reset the tracker when no flame is detected.
        """
        self.baseline_areas.clear()
        self.baseline_area = 0.0
        self.is_baseline_established = False
        
    def get_stats(self) -> dict:
        """
        Return tracking statistics for debugging/UI.
        """
        return {
            "baseline_area": self.baseline_area,
            "established": self.is_baseline_established
        }
