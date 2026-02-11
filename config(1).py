import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_FILE = os.path.join(BASE_DIR, "active_qrcodes.json")
MAP_FILE = os.path.join(BASE_DIR, "grundriss.png")

# Kamera
CAM_WIDTH = 2560
CAM_HEIGHT = 1440
CAM_FPS = 17

# Logik
MEMORY_TOLERANCE = 15       # Frames (Kurzzeitgedächtnis für flackern)
BORDER_MARGIN = 100         # Pixel (Kill Zone)
SCALE_FACTOR = 0.5      

# Tracking Parameter
MAX_TRACKING_DISTANCE = 300 # Pixel (Frame zu Frame Sprung)

# NEU: Wiederbelebung
HISTORY_DURATION = 10.0     # Sekunden (Wie lange merken wir uns verschwundene Objekte?)
RECOVERY_DISTANCE = 500     # Pixel (Darf größer sein als Tracking Distanz, da Zeit vergangen ist)


