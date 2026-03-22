# Configuration constants

# Timeouts in seconds
TIMEOUT_SECONDS = 300
WARNING_SECONDS = 240
CRITICAL_SECONDS = 300

# Camera settings
CAMERA_INDEX = 0

# Detection settings
CONFIDENCE_THRESHOLD = 0.7

# Safe Zones Settings
BURNER_RADIUS_PIXELS = 100
BURNERS_FILE = "burner_zones.json"

# Temporal / Growth Settings
GROWTH_WARNING_MULTIPLIER = 1.5
GROWTH_CRITICAL_MULTIPLIER = 2.0
BASELINE_FRAMES = 300
CURRENT_AREA_FRAMES = 30
