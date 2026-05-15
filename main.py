# ============================================================
#  main.py  (v3 — Full Platform with Dashboard + Analytics)
#  AI Smart Classroom Monitoring System — SIH Project
#
#  HOW v3 WORKS:
#    Thread 1 (main thread):
#      - Reads frames from IP Webcam
#      - Runs face detection + attention tracking
#      - Feeds results to AnalyticsEngine + HeatmapSystem
#      - Writes latest frame + data to shared_state dict
#      - Shows OpenCV window (optional — can be minimised)
#
#    Thread 2 (background daemon):
#      - Runs FastAPI / uvicorn web server
#      - Serves the HTML dashboard at http://localhost:8000
#      - Streams live MJPEG video to the browser
#      - Pushes analytics via WebSocket every second
#
#  Both threads share data through backend_api.shared_state.
#
#  TO RUN:
#      python main.py
#  Then open: http://localhost:8000
# ============================================================

import threading
import time
import cv2

# Our modules
import config
from camera                      import ClassroomCamera
from ai_engine.face_detector     import FaceDetector
from ai_engine.attention_tracker import AttentionTracker
from display                     import draw_detections, draw_stats, save_screenshot
from analytics_engine            import AnalyticsEngine
from heatmap_system              import HeatmapSystem
from backend_api                 import start_server, shared_state


def print_banner():
    print("=" * 62)
    print("    AI SMART CLASSROOM MONITORING SYSTEM  —  v3")
    print("    Smart India Hackathon (SIH) Project")
    print("=" * 62)
    print()
    print("  CAMERA  :", config.CAMERA_URL)
    print("  DASHBOARD: http://localhost:8000")
    print()
    print("  AI MODELS:")
    print("    · MediaPipe Face Detection (BlazeFace)")
    print("    · MediaPipe Face Mesh (468 landmarks)")
    print()
    print("  ATTENTION THRESHOLDS:")
    print(f"    Pitch threshold  : {config.PITCH_THRESHOLD}°")
    print(f"    Yaw threshold    : {config.YAW_THRESHOLD}°")
    print(f"    EAR threshold    : {config.EAR_THRESHOLD}")
    print(f"    Inactive timeout : {config.INACTIVE_TIMEOUT}s")
    print()
    print("  CONTROLS (OpenCV window):")
    print("    Q → Quit   S → Screenshot   P → Pause")
    print()
    print("  Starting system...")
    print("=" * 62)


def main():
    print_banner()

    # ── Step 1: Start the web server in a background thread ───
    # daemon=True means the thread dies automatically when main exits
    server_thread = threading.Thread(
        target=start_server,
        kwargs={"host": "0.0.0.0", "port": 8000},
        daemon=True
    )
    server_thread.start()

    # Give uvicorn a moment to start before connecting camera
    time.sleep(1.5)

    # ── Step 2: Load AI models ─────────────────────────────
    cam      = ClassroomCamera()
    cam.connect()

    detector = FaceDetector()
    tracker  = AttentionTracker()
    analytics = AnalyticsEngine()
    heatmap   = HeatmapSystem(
        rows=config.HEATMAP_ROWS,
        cols=config.HEATMAP_COLS
    )

    print("\n[Main] All systems online. Open http://localhost:8000\n")

    # ── Step 3: State variables ────────────────────────────
    fps_timer     = time.time()
    frame_count   = 0
    fps_display   = 0.0
    loop_count    = 0

    face_detections   = []
    attention_results = []
    detection_paused  = False

    # ── Step 4: Main loop ──────────────────────────────────
    while True:
        success, frame = cam.read()
        if not success or frame is None:
            continue

        loop_count += 1
        frame_h, frame_w = frame.shape[:2]

        if not detection_paused:
            # Run face detection every N frames
            if loop_count % config.DETECT_EVERY_N_FRAMES == 0:
                face_detections = detector.detect(frame)

            # Run attention tracking every N frames
            if loop_count % config.ATTENTION_EVERY_N_FRAMES == 0:
                if face_detections:
                    attention_results = tracker.analyse(frame, face_detections)
                else:
                    attention_results = []

        else:
            attention_results = []

        # Update analytics and heatmap
        analytics.update(attention_results)
        heatmap_data = heatmap.update(frame_w, frame_h, attention_results)

        # FPS
        frame_count += 1
        elapsed = time.time() - fps_timer
        if elapsed >= 1.0:
            fps_display = frame_count / elapsed
            fps_timer   = time.time()
            frame_count = 0

        # Annotate frame for OpenCV window AND dashboard stream
        annotated = draw_detections(frame.copy(), attention_results)
        final     = draw_stats(
            annotated,
            fps=fps_display,
            results=attention_results,
            detection_paused=detection_paused
        )

        # ── Write to shared_state (read by the API) ────────
        with shared_state["frame_lock"]:
            shared_state["frame"]             = final.copy()
            shared_state["fps"]               = fps_display
            shared_state["analytics"]         = analytics.get_snapshot()
            shared_state["heatmap"]           = heatmap_data
            shared_state["attention_results"] = attention_results

        # ── Show OpenCV window ─────────────────────────────
        cv2.imshow(config.WINDOW_TITLE, final)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == ord('Q'):
            print("\n[Main] Shutting down...")
            break
        elif key == ord('s') or key == ord('S'):
            save_screenshot(final)
        elif key == ord('p') or key == ord('P'):
            detection_paused = not detection_paused
            print(f"[Main] Detection {'PAUSED' if detection_paused else 'RESUMED'}")

    # ── Cleanup ────────────────────────────────────────────
    cam.release()
    detector.close()
    tracker.close()
    cv2.destroyAllWindows()
    print("[Main] Cleanup complete.")


if __name__ == "__main__":
    main()