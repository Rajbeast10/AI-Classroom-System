# ============================================================
#  ai_engine/face_detector.py  (UNCHANGED from v1)
#  AI Smart Classroom Monitoring System — SIH Project
#
#  PURPOSE: Detects multiple student faces using MediaPipe's
#           CLASSIC API:  mp.solutions.face_detection
#           DO NOT change to Tasks API.
# ============================================================

import cv2
import mediapipe as mp
import config


class FaceDetector:
    """
    Wraps MediaPipe Face Detection in a simple, reusable class.

    Usage:
        detector = FaceDetector()
        detections = detector.detect(frame)
        detector.close()
    """

    def __init__(self):
        self.mp_face = mp.solutions.face_detection
        self.detector = self.mp_face.FaceDetection(
            model_selection=config.MODEL_SELECTION,
            min_detection_confidence=config.MIN_DETECTION_CONFIDENCE
        )
        print("[FaceDetector] MediaPipe face detection model loaded.")
        print(f"[FaceDetector] Model: "
              f"{'Full-range (1)' if config.MODEL_SELECTION == 1 else 'Short-range (0)'}")
        print(f"[FaceDetector] Min confidence: {config.MIN_DETECTION_CONFIDENCE}")

    def detect(self, frame):
        """
        Detects all faces in a single BGR video frame.

        Returns:
            List of dicts: [{"box": (x,y,w,h), "confidence": 0.94}, ...]
            Empty list [] if no faces found.
        """
        frame_h, frame_w, _ = frame.shape

        # Scale down for faster detection
        scale = config.DETECTION_SCALE
        if scale < 1.0:
            small_w     = int(frame_w * scale)
            small_h     = int(frame_h * scale)
            small_frame = cv2.resize(frame, (small_w, small_h))
        else:
            small_frame = frame

        # Convert BGR → RGB (MediaPipe requirement)
        rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        rgb_frame.flags.writeable = False
        results = self.detector.process(rgb_frame)
        rgb_frame.flags.writeable = True

        if not results.detections:
            return []

        detections = []
        for detection in results.detections:
            confidence = detection.score[0]
            bboxC      = detection.location_data.relative_bounding_box

            # Relative → pixel coords on small frame
            x = int(bboxC.xmin  * small_frame.shape[1])
            y = int(bboxC.ymin  * small_frame.shape[0])
            w = int(bboxC.width  * small_frame.shape[1])
            h = int(bboxC.height * small_frame.shape[0])

            # Scale back to full frame size
            if scale < 1.0:
                inv = 1.0 / scale
                x = int(x * inv)
                y = int(y * inv)
                w = int(w * inv)
                h = int(h * inv)

            # Clamp to frame boundaries
            x = max(0, x)
            y = max(0, y)
            w = min(frame_w - x, w)
            h = min(frame_h - y, h)

            detections.append({
                "box":        (x, y, w, h),
                "confidence": round(confidence, 2)
            })

        return detections

    def close(self):
        """Releases MediaPipe model resources."""
        self.detector.close()
        print("[FaceDetector] Model released.")