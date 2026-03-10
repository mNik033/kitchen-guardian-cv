import cv2
import time
import json
import os
from src.config import CAMERA_INDEX, BURNER_RADIUS_PIXELS, BURNERS_FILE
from src.detectors import VisionSystem
from src.state_machine import SafetyGuardian
from src.temporal import FlameTracker

burner_zones = []
mock_flame_pos = None

def load_burners():
    global burner_zones
    if os.path.exists(BURNERS_FILE):
        try:
            with open(BURNERS_FILE, 'r') as f:
                burner_zones = json.load(f)
            print(f"Loaded {len(burner_zones)} burner zones.")
        except Exception as e:
            print(f"Failed to load burners: {e}")

def save_burners():
    try:
        with open(BURNERS_FILE, 'w') as f:
            json.dump(burner_zones, f)
        print(f"Saved {len(burner_zones)} burner zones to {BURNERS_FILE}.")
    except Exception as e:
        print(f"Failed to save burners: {e}")

def handle_mouse_events(event, x, y, flags, param):
    global burner_zones, mock_flame_pos
    
    if event == cv2.EVENT_LBUTTONDOWN:
        # Add a new burner zone
        burner_zones.append((x, y))
        print(f"Added Burner Zone at ({x}, {y})")
        
    elif event == cv2.EVENT_RBUTTONDOWN:
        # Clear all burner zones
        burner_zones = []
        print("Cleared all Burner Zones.")
        
    elif event == cv2.EVENT_MOUSEMOVE:
        # Track mouse for mock flame if active
        mock_flame_pos = (x, y)

def main():
    # Initialize Camera
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print(f"Error: Could not open camera with index {CAMERA_INDEX}.")
        return

    # Initialize Systems
    print("Initializing Vision System...")
    vision_system = VisionSystem()
    print("Initializing Safety Guardian...")
    guardian = SafetyGuardian()
    print("Initializing Flame Tracker...")
    flame_tracker = FlameTracker()

    # Load previously saved burners
    load_burners()

    # Mock flame state
    mock_flame_active = False

    print("System detection started.")
    print("UI Controls:")
    print(" - Left Click: Add Burner Center")
    print(" - Right Click: Clear All Burners")
    print(" - Press 's': Save Burners to File")
    print(" - Press 'f': Toggle Mock Flame (follows mouse)")
    print(" - Press 'q': Quit")

    cv2.namedWindow('Kitchen Guardian')
    cv2.setMouseCallback('Kitchen Guardian', handle_mouse_events)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Error: Failed to capture frame.")
                break

            # Generate the mock flame box if active
            current_mock_box = None
            if mock_flame_active and mock_flame_pos:
                mx, my = mock_flame_pos
                # Create a 50x50 box around the mouse cursor
                current_mock_box = [mx - 25, my - 25, mx + 25, my + 25]

            # 1. Detect Objects & Validate Zones
            detection_result = vision_system.detect_objects(
                frame=frame, 
                burner_zones=burner_zones, 
                mock_flame_box=current_mock_box
            )

            # Filter boxes to only contain flames
            flame_boxes = [box for box in detection_result['boxes'] if box['class'] == 'flame']
            
            # Update temporal logic (Growth tracking)
            growth_status = flame_tracker.update(flame_boxes)
            # If the fire is NOT safe spatially, we override the temporal state machine
            is_safe_fire = detection_result['is_safe_fire']
            
            if detection_result['flame_detected'] and not is_safe_fire:
                # Immediate danger branch
                status = "CRITICAL_SHUTOFF"
                guardian.update_status(flame_on=True, person_present=detection_result['person_detected'], growth_status=growth_status) 
                # Override the returned status because spatial logic supersedes temporal logic
            else:
                # Normal temporal logic
                status = guardian.update_status(
                    flame_on=detection_result['flame_detected'],
                    person_present=detection_result['person_detected'],
                    growth_status=growth_status
                )

            # 3. Visualization
            # Draw Bounding Boxes
            for item in detection_result['boxes']:
                box = item['box']
                x1, y1, x2, y2 = map(int, box)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, f"{item['class']} {item['conf']:.2f}", (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            # Draw Burner Zones
            for (zx, zy) in burner_zones:
                # Draw the radius
                cv2.circle(frame, (zx, zy), BURNER_RADIUS_PIXELS, (255, 150, 0), 2)
                # Draw the center point
                cv2.circle(frame, (zx, zy), 4, (255, 150, 0), -1)

            # Draw Status Info
            # Top Left: System Status
            status_color = (0, 255, 0) # Green for SAFE
            if status == "WARNING":
                status_color = (0, 255, 255) # Yellow
            elif status == "CRITICAL_SHUTOFF":
                status_color = (0, 0, 255) # Red

            warning_text = ""
            if detection_result['flame_detected'] and not is_safe_fire:
                warning_text = " (FIRE OUTSIDE SAFE ZONE)"

            cv2.putText(frame, f"STATUS: {status}{warning_text}", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)
            
            # Draw Flame Status
            flame_text = "FLAME: ON" if mock_flame_active else "FLAME: OFF"
            flame_color = (0, 0, 255) if mock_flame_active else (255, 255, 255)
            cv2.putText(frame, flame_text, (20, 80),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, flame_color, 2)
            
            # Draw Person Status
            person_text = "PERSON: YES" if detection_result['person_detected'] else "PERSON: NO"
            cv2.putText(frame, person_text, (20, 110),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            # Draw Flame Growth Stats
            stats = flame_tracker.get_stats()
            if stats['established']:
                # Calculate current area
                current_area = sum(flame_tracker._calculate_area(b['box']) for b in flame_boxes)
                stats_text = f"FLAME AREA: {current_area:.0f} (Base: {stats['baseline_area']:.0f})"
                if growth_status != "SAFE":
                    stats_text += f" [{growth_status}]"
                
                # Make text red if warning/critical
                stats_color = (0, 0, 255) if growth_status != "SAFE" else (255, 255, 255)
                cv2.putText(frame, stats_text, (20, 140),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, stats_color, 2)

            # Show Frame
            cv2.imshow('Kitchen Guardian', frame)

            # 4. Input Handling
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                save_burners()
            elif key == ord('f'):
                mock_flame_active = not mock_flame_active
                print(f"Mock Flame toggled: {mock_flame_active}")
                if not mock_flame_active:
                    flame_tracker.reset()

    except KeyboardInterrupt:
        print("Stopping system...")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("System shutdown.")

if __name__ == "__main__":
    main()
