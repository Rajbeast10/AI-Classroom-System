# ============================================================
#  stream.py  (UPDATED — v2 with Attention Tracking)
#  AI Smart Classroom Monitoring System — SIH Project
#
#  PURPOSE:
#    The core processing loop.
#    v2 changes:
#      - AttentionTracker runs after FaceDetector
#      - Results passed to updated display functions
#      - Attention tracking has its own frame-skip counter
#      - Both detectors share the same frame skip philosophy
#
#  PROCESSING PIPELINE PER FRAME:
#    Read frame → (every N frames) Run FaceDetector
#              → (every N frames) Run AttentionTracker
#              → Draw boxes + labels → Draw stats → Show
# ============================================================

import cv2
import time

from camera                      import ClassroomCamera
from ai_engine.face_detector     import FaceDetector
from ai_engine.attention_tracker import AttentionTracker
from display                     import draw_detections, draw_stats, save_screenshot
import config


# ============================================================
#  run_stream()
# ============================================================

def run_stream():
    """
    Main loop: reads frames, runs face detection + attention
    tracking, draws all overlays, shows the result.

    Keyboard:
        Q — quit
        S — screenshot
        P — pause/resume both detection and attention tracking
    """

    # ── Step 1: Connect to camera ──────────────────────────
    cam = ClassroomCamera()
    cam.connect()

    # ── Step 2: Load AI models ─────────────────────────────
    # Load FaceDetector (MediaPipe face detection)
    detector = FaceDetector()

    # Load AttentionTracker (MediaPipe Face Mesh)
    tracker = AttentionTracker()

    print("\n[Stream] Both AI models loaded successfully.")

    # ── Step 3: State variables ────────────────────────────

    fps_timer    = time.time()
    frame_count  = 0
    fps_display  = 0.0

    loop_count   = 0   # increments every iteration

    # Last known results — reused on skipped frames
    # Starting as empty list means no boxes shown until first detection
    face_detections = []   # raw face boxes from FaceDetector
    attention_results = [] # enriched results from AttentionTracker

    detection_paused = False

    print("[Stream] Starting live feed. Press Q to quit.\n")

    # ──────────────────────────────────────────────────────
    #  MAIN LOOP
    # ──────────────────────────────────────────────────────
    while True:

        success, frame = cam.read()
        if not success or frame is None:
            print("[Stream] Dropped frame — retrying ...")
            continue

        loop_count += 1

        if not detection_paused:

            # ── Face Detection (every DETECT_EVERY_N_FRAMES) ──
            # Runs the lighter MediaPipe BlazeFace model.
            if loop_count % config.DETECT_EVERY_N_FRAMES == 0:
                face_detections = detector.detect(frame)

            # ── Attention Tracking (every ATTENTION_EVERY_N_FRAMES) ──
            # Runs the heavier MediaPipe Face Mesh model.
            # Uses the face_detections from above as its input.
            if loop_count % config.ATTENTION_EVERY_N_FRAMES == 0:
                if face_detections:
                    # analyse() enriches each detection with status/angles
                    attention_results = tracker.analyse(frame, face_detections)
                else:
                    attention_results = []

        else:
            # Paused — clear results so no stale boxes linger
            attention_results = []

        # ── Draw bounding boxes + status labels ────────────
        # draw_detections() now uses the richer attention_results
        # (which include status, color, pitch, yaw, ear)
        annotated = draw_detections(frame.copy(), attention_results)

        # ── FPS calculation ────────────────────────────────
        frame_count += 1
        elapsed = time.time() - fps_timer
        if elapsed >= 1.0:
            fps_display = frame_count / elapsed
            fps_timer   = time.time()
            frame_count = 0

        # ── Draw stats panel ───────────────────────────────
        # v2: pass attention_results (not just face count)
        final = draw_stats(
            annotated,
            fps=fps_display,
            results=attention_results,
            detection_paused=detection_paused
        )

        # ── Show the frame ─────────────────────────────────
        cv2.imshow(config.WINDOW_TITLE, final)

        # ── Keyboard input ─────────────────────────────────
        key = cv2.waitKey(1) & 0xFF

        if key == ord('q') or key == ord('Q'):
            print("\n[Stream] Q pressed. Shutting down ...")
            break

        elif key == ord('s') or key == ord('S'):
            save_screenshot(final)

        elif key == ord('p') or key == ord('P'):
            detection_paused = not detection_paused
            state = "PAUSED" if detection_paused else "RESUMED"
            print(f"[Stream] Detection {state}.")

    # ── Cleanup ────────────────────────────────────────────
    cam.release()
    detector.close()
    tracker.close()
    cv2.destroyAllWindows()
    print("[Stream] All resources released. Goodbye!")
    