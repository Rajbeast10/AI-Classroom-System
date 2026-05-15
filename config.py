# ============================================================
#  config.py  (v3 — Full Platform)
#  AI Smart Classroom Monitoring System — SIH Project
#  All settings in one place. Edit only this file.
# ============================================================

# ── Camera ─────────────────────────────────────────────────
PHONE_IP   = "192.168.1.5"   # <── CHANGE THIS
PHONE_PORT = 8080
CAMERA_URL = f"http://{PHONE_IP}:{PHONE_PORT}/video"

STREAM_TIMEOUT_SEC     = 10
BUFFER_SIZE            = 1
MAX_RECONNECT_ATTEMPTS = 5
RECONNECT_WAIT_SEC     = 2

# ── Face Detection ──────────────────────────────────────────
MIN_DETECTION_CONFIDENCE = 0.5
MODEL_SELECTION          = 1     # 1 = full-range (2–5m, best for classroom)
DETECT_EVERY_N_FRAMES    = 2
DETECTION_SCALE          = 0.5

# ── Attention Tracking ──────────────────────────────────────
PITCH_THRESHOLD          = 20.0   # degrees — exceed = DISTRACTED
YAW_THRESHOLD            = 30.0   # degrees — exceed = LOOKING AWAY
EAR_THRESHOLD            = 0.20   # below = DROWSY
INACTIVE_TIMEOUT         = 12.0   # seconds still = INACTIVE
ATTENTION_EVERY_N_FRAMES = 2

# ── Heatmap Layout ──────────────────────────────────────────
# Set these to match your actual classroom seating arrangement
HEATMAP_ROWS = 4    # number of seat rows
HEATMAP_COLS = 6    # seats per row  (4×6 = 24 seats total)

# ── API Server ──────────────────────────────────────────────
API_HOST = "0.0.0.0"
API_PORT = 8000

# ── Display ─────────────────────────────────────────────────
WINDOW_TITLE      = "AI Classroom Monitor  |  Q=Quit  S=Screenshot  P=Pause"
BOX_THICKNESS     = 2
LABEL_FONT_SCALE  = 0.52
LABEL_THICKNESS   = 1
STATS_COLOR       = (0, 255, 255)
STATS_FONT_SCALE  = 0.62
STATS_THICKNESS   = 2
SCREENSHOT_DIR    = "screenshots"