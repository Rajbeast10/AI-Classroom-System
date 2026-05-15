# ============================================================
#  display.py  (UPDATED — v2 with Attention Tracking overlays)
#  AI Smart Classroom Monitoring System — SIH Project
#
#  PURPOSE:
#    All drawing functions for the video window.
#    v2 adds:
#      - Colour-coded bounding boxes per attention status
#      - Status label above each face (ATTENTIVE / DROWSY etc.)
#      - Head angle display (pitch / yaw) below each box
#      - Classroom engagement score (% attentive)
#      - Distracted + drowsy student counts in stats panel
#
#  NOTE: display.py has NO AI logic — it only draws things.
#        All decisions happen in ai_engine/attention_tracker.py
# ============================================================

import cv2
import os
import time
import config


# ============================================================
#  draw_detections()
#  Draws a colour-coded box + status label for every face
# ============================================================

def draw_detections(frame, results):
    """
    Draws bounding boxes and attention status labels.

    In v1, results were simple face dicts with just box + confidence.
    In v2, results come from AttentionTracker and include:
        "box", "confidence", "status", "pitch", "yaw", "ear", "color"

    The function handles BOTH formats (v1 fallback included).

    Args:
        frame:   BGR image from OpenCV.
        results: List of dicts from AttentionTracker.analyse()
                 (or FaceDetector.detect() as fallback).

    Returns:
        Frame with boxes and labels drawn on it.
    """

    for i, res in enumerate(results):

        x, y, w, h = res["box"]
        confidence  = res["confidence"]

        # ── Determine box colour ───────────────────────────
        # v2: use the status colour from AttentionTracker
        # v1 fallback: use plain green
        color = res.get("color", (0, 255, 0))

        # ── Draw bounding box ──────────────────────────────
        cv2.rectangle(
            frame,
            (x, y),
            (x + w, y + h),
            color,
            config.BOX_THICKNESS
        )

        # ── Build label line 1: Student N | STATUS | confidence% ──
        status = res.get("status", "")
        if status:
            label = f"S{i+1} | {status} | {int(confidence * 100)}%"
        else:
            label = f"Student {i+1} | {int(confidence * 100)}%"

        # ── Measure label text size ────────────────────────
        (lw, lh), baseline = cv2.getTextSize(
            label,
            cv2.FONT_HERSHEY_SIMPLEX,
            config.LABEL_FONT_SCALE,
            config.LABEL_THICKNESS
        )

        # Position label ABOVE the bounding box
        label_y = max(y - 6, lh + 4)

        # Dark background rectangle behind label for readability
        cv2.rectangle(
            frame,
            (x, label_y - lh - 4),
            (x + lw + 6, label_y + baseline + 1),
            (0, 0, 0),
            cv2.FILLED
        )

        # Draw label text
        cv2.putText(
            frame,
            label,
            (x + 3, label_y - 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            config.LABEL_FONT_SCALE,
            color,
            config.LABEL_THICKNESS
        )

        # ── Draw head angle info BELOW the bounding box ────
        # Only draw if we have angle data (v2 only)
        pitch = res.get("pitch")
        yaw   = res.get("yaw")
        ear   = res.get("ear")

        if pitch is not None and yaw is not None:
            angle_text = f"P:{pitch:+.0f} Y:{yaw:+.0f} EAR:{ear:.2f}"

            (aw, ah), _ = cv2.getTextSize(
                angle_text,
                cv2.FONT_HERSHEY_SIMPLEX,
                0.42,
                1
            )

            # Position below the bounding box
            angle_y = y + h + ah + 6

            # Dark background
            cv2.rectangle(
                frame,
                (x, y + h + 2),
                (x + aw + 6, angle_y + 3),
                (0, 0, 0),
                cv2.FILLED
            )

            cv2.putText(
                frame,
                angle_text,
                (x + 3, angle_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.42,
                (200, 200, 200),   # Light grey
                1
            )

    return frame


# ============================================================
#  draw_stats()
#  Top-left stats panel: FPS, counts, engagement score
# ============================================================

def draw_stats(frame, fps, results, detection_paused=False):
    """
    Draws the stats overlay panel in the top-left corner.

    v2 adds: attentive count, distracted count, engagement %.

    Args:
        frame:             BGR image to draw on.
        fps:               Current FPS (float).
        results:           List of attention result dicts.
        detection_paused:  True if user pressed P.

    Returns:
        Frame with stats drawn.
    """

    # ── Count statuses ─────────────────────────────────────
    total      = len(results)
    attentive  = sum(1 for r in results if r.get("status") == "ATTENTIVE")
    distracted = sum(1 for r in results if r.get("status") == "DISTRACTED")
    looking_away = sum(1 for r in results if r.get("status") == "LOOKING AWAY")
    drowsy     = sum(1 for r in results if r.get("status") == "DROWSY")
    inactive   = sum(1 for r in results if r.get("status") == "INACTIVE")

    # ── Engagement score ───────────────────────────────────
    # Percentage of detected students who are ATTENTIVE
    if total > 0:
        engagement = int((attentive / total) * 100)
    else:
        engagement = 0

    # Choose engagement colour
    if engagement >= 70:
        eng_color = (0, 255, 0)     # Green — good
    elif engagement >= 40:
        eng_color = (0, 255, 255)   # Yellow — okay
    else:
        eng_color = (0, 0, 255)     # Red — poor

    # ── Background panel ───────────────────────────────────
    # Draw a dark rectangle behind all the text
    panel_h = 230 if total > 0 else 120
    cv2.rectangle(frame, (0, 0), (275, panel_h), (0, 0, 0), cv2.FILLED)

    # Draw a subtle border on the panel
    cv2.rectangle(frame, (0, 0), (275, panel_h), (50, 50, 50), 1)

    font       = cv2.FONT_HERSHEY_SIMPLEX
    fscale     = config.STATS_FONT_SCALE
    fthick     = config.STATS_THICKNESS
    text_color = config.STATS_COLOR   # Yellow

    # ── Line 1: FPS ────────────────────────────────────────
    cv2.putText(frame, f"FPS: {fps:.1f}", (10, 28),
                font, fscale, text_color, fthick)

    # ── Line 2: Total students ─────────────────────────────
    cv2.putText(frame, f"Students: {total}", (10, 54),
                font, fscale, text_color, fthick)

    if total > 0:
        # ── Line 3: Engagement score ───────────────────────
        cv2.putText(frame, f"Engagement: {engagement}%", (10, 80),
                    font, fscale, eng_color, fthick)

        # ── Lines 4–8: Per-status counts ──────────────────
        status_lines = [
            (f"  Attentive  : {attentive}",  (0, 220,  0  )),
            (f"  Distracted : {distracted}", (0, 220, 220 )),
            (f"  Looking Away: {looking_away}", (0, 140, 255)),
            (f"  Drowsy     : {drowsy}",     (0,   0, 220 )),
            (f"  Inactive   : {inactive}",   (200,  0,   0)),
        ]

        y_pos = 106
        for text, color in status_lines:
            cv2.putText(frame, text, (10, y_pos),
                        font, 0.50, color, 1)
            y_pos += 22

    # ── Detection status ───────────────────────────────────
    if detection_paused:
        status_text  = "Detection: PAUSED (P)"
        status_color = (0, 140, 255)
    else:
        status_text  = "Detection: ACTIVE"
        status_color = (0, 255, 0)

    cv2.putText(frame, status_text, (10, panel_h - 10),
                font, 0.50, status_color, 1)

    # ── Keyboard hint at very bottom of frame ──────────────
    cv2.putText(
        frame,
        "Q=Quit  S=Screenshot  P=Pause",
        (10, frame.shape[0] - 10),
        font, 0.42, (160, 160, 160), 1
    )

    return frame


# ============================================================
#  save_screenshot()  (unchanged from v1)
# ============================================================

def save_screenshot(frame):
    """Saves the current frame as a timestamped PNG."""
    os.makedirs(config.SCREENSHOT_DIR, exist_ok=True)
    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    filename  = os.path.join(config.SCREENSHOT_DIR,
                             f"classroom_{timestamp}.png")
    cv2.imwrite(filename, frame)
    print(f"[Display] Screenshot saved: {filename}")