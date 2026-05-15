# ============================================================
#  ai_engine/attention_tracker.py  (FIXED — v2.1)
#  AI Smart Classroom Monitoring System — SIH Project
#
#  FIX: Removed cv2.decomposeHomographyMat() which caused:
#       "Assertion failed: H.cols==3 && H.rows==3"
#       because it expects a 3x3 matrix, not 3x4.
#
#  REPLACED WITH: Direct Rodrigues → rotation matrix → Euler
#  angles using np.arctan2. Simpler, faster, and crash-free.
#
#  Everything else is IDENTICAL to the previous version.
# ============================================================

import cv2
import numpy as np
import mediapipe as mp
import time
import config


# ============================================================
#  LANDMARK INDICES
# ============================================================

# 6 key face points for head pose estimation via solvePnP
POSE_LANDMARK_IDS = [
    1,    # Nose tip
    152,  # Chin
    33,   # Left eye left corner
    263,  # Right eye right corner
    61,   # Left mouth corner
    291   # Right mouth corner
]

# Eye landmarks for EAR (drowsiness) calculation
LEFT_EYE_IDS  = [362, 385, 387, 263, 373, 380]
RIGHT_EYE_IDS = [33,  160, 158, 133, 153, 144]

# Real-world 3D coordinates (mm) matching the 6 landmarks above.
# Based on average human face measurements.
MODEL_3D_POINTS = np.array([
    [  0.0,    0.0,    0.0 ],   # Nose tip
    [  0.0,  -63.6,  -12.5 ],   # Chin
    [-43.3,   32.7,  -26.0 ],   # Left eye corner
    [ 43.3,   32.7,  -26.0 ],   # Right eye corner
    [-28.9,  -28.9,  -24.1 ],   # Left mouth corner
    [ 28.9,  -28.9,  -24.1 ]    # Right mouth corner
], dtype=np.float64)


# ============================================================
#  STATUS LABELS AND COLOURS  (BGR format for OpenCV)
# ============================================================

STATUS_ATTENTIVE    = "ATTENTIVE"
STATUS_DISTRACTED   = "DISTRACTED"
STATUS_LOOKING_AWAY = "LOOKING AWAY"
STATUS_DROWSY       = "DROWSY"
STATUS_INACTIVE     = "INACTIVE"

STATUS_COLORS = {
    STATUS_ATTENTIVE:    (  0, 255,   0),   # Green
    STATUS_DISTRACTED:   (  0, 255, 255),   # Yellow
    STATUS_LOOKING_AWAY: (  0, 165, 255),   # Orange
    STATUS_DROWSY:       (  0,   0, 255),   # Red
    STATUS_INACTIVE:     (255,   0,   0),   # Blue
}


# ============================================================
#  AttentionTracker
# ============================================================

class AttentionTracker:
    """
    Analyses student faces and determines their attention status.

    Usage:
        tracker = AttentionTracker()
        results = tracker.analyse(frame, face_detections)
        tracker.close()

    Each result dict contains:
        "box"        : (x, y, w, h)
        "confidence" : float
        "status"     : one of the STATUS_* strings
        "pitch"      : float  (head up/down degrees)
        "yaw"        : float  (head left/right degrees)
        "ear"        : float  (eye openness 0.0-0.35)
        "color"      : (B, G, R) tuple for drawing
    """

    def __init__(self):
        # Classic MediaPipe Face Mesh API  (NOT Tasks API)
        self.mp_face_mesh = mp.solutions.face_mesh

        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=10,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        # Per-face inactivity tracking
        self._last_active_time = {}   # face_idx → last-moved timestamp
        self._last_positions   = {}   # face_idx → last (cx, cy)

        print("[AttentionTracker] Face Mesh model loaded.")
        print(f"[AttentionTracker] Thresholds: "
              f"pitch±{config.PITCH_THRESHOLD}° "
              f"yaw±{config.YAW_THRESHOLD}° "
              f"EAR<{config.EAR_THRESHOLD} "
              f"inactive>{config.INACTIVE_TIMEOUT}s")

    # ──────────────────────────────────────────────────────
    #  analyse()
    # ──────────────────────────────────────────────────────
    def analyse(self, frame, face_detections):
        """
        Runs the full attention pipeline on every detected face.

        Args:
            frame:           BGR image (NumPy array) from OpenCV.
            face_detections: List of dicts from FaceDetector.detect().

        Returns:
            List of enriched result dicts (one per face).
        """

        if not face_detections:
            return []

        frame_h, frame_w = frame.shape[:2]

        # Convert BGR → RGB for MediaPipe
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        mesh_results = self.face_mesh.process(rgb)
        rgb.flags.writeable = True

        # If Face Mesh found no landmarks, mark everyone as INACTIVE
        if not mesh_results.multi_face_landmarks:
            return [
                {**det,
                 "status": STATUS_INACTIVE,
                 "pitch": 0.0, "yaw": 0.0, "ear": 0.0,
                 "color": STATUS_COLORS[STATUS_INACTIVE]}
                for det in face_detections
            ]

        results        = []
        num_mesh_faces = len(mesh_results.multi_face_landmarks)

        for i, det in enumerate(face_detections):

            if i >= num_mesh_faces:
                # More detections than mesh faces — mark as inactive
                results.append({
                    **det,
                    "status": STATUS_INACTIVE,
                    "pitch": 0.0, "yaw": 0.0, "ear": 0.0,
                    "color": STATUS_COLORS[STATUS_INACTIVE]
                })
                continue

            landmarks = mesh_results.multi_face_landmarks[i].landmark

            # 1. Head pose angles
            pitch, yaw, roll = self._get_head_pose(landmarks, frame_w, frame_h)

            # 2. Eye Aspect Ratio
            ear = self._get_ear(landmarks, frame_w, frame_h)

            # 3. Inactivity check
            x, y, w, h = det["box"]
            self._update_activity(i, (x + w // 2, y + h // 2))

            # 4. Classify into a status
            status = self._classify(i, pitch, yaw, ear)

            results.append({
                **det,
                "status": status,
                "pitch":  round(pitch, 1),
                "yaw":    round(yaw,   1),
                "ear":    round(ear,   3),
                "color":  STATUS_COLORS[status]
            })

        return results

    # ──────────────────────────────────────────────────────
    #  _get_head_pose()  — THE FIXED FUNCTION
    # ──────────────────────────────────────────────────────
    def _get_head_pose(self, landmarks, frame_w, frame_h):
        """
        Estimates 3D head rotation angles.

        METHOD:
          1. Read 6 landmark 2D positions from the frame.
          2. Use solvePnP to find the rotation vector (rvec)
             that maps our 3D face model onto those 2D points.
          3. Convert rvec → 3x3 rotation matrix via Rodrigues.
          4. Extract pitch/yaw/roll from the rotation matrix
             using standard arctan2 Euler decomposition.

        WHY THIS IS FIXED:
          The old code called cv2.decomposeHomographyMat() with
          a 3x4 matrix — that function requires a 3x3 matrix and
          crashed with "Assertion failed: H.cols==3 && H.rows==3".
          We now use direct arctan2 math on the rotation matrix —
          no extra OpenCV function needed at all.

        Returns:
            pitch : float — positive = head tilted DOWN
            yaw   : float — positive = head turned RIGHT
            roll  : float — head tilt (not used for classification)
        """

        # Get 2D pixel positions of our 6 chosen landmarks
        image_2d_points = np.array(
            [[landmarks[idx].x * frame_w,
              landmarks[idx].y * frame_h]
             for idx in POSE_LANDMARK_IDS],
            dtype=np.float64
        )

        # Approximate camera intrinsic matrix
        # (focal length ≈ frame width is a well-known approximation)
        f  = float(frame_w)
        cx = frame_w / 2.0
        cy = frame_h / 2.0

        camera_matrix = np.array(
            [[f,   0.0, cx],
             [0.0, f,   cy],
             [0.0, 0.0, 1.0]],
            dtype=np.float64
        )

        dist_coeffs = np.zeros((4, 1), dtype=np.float64)

        # solvePnP: find rotation (rvec) and translation (tvec)
        # that aligns 3D model points with the 2D image points
        success, rvec, tvec = cv2.solvePnP(
            MODEL_3D_POINTS,
            image_2d_points,
            camera_matrix,
            dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE
        )

        if not success:
            return 0.0, 0.0, 0.0

        # Convert rotation vector → 3x3 rotation matrix
        # cv2.Rodrigues converts compact axis-angle representation
        # to a full rotation matrix
        rot_matrix, _ = cv2.Rodrigues(rvec)

        # ── Extract Euler angles from rotation matrix ────────
        #
        # Standard ZYX Euler angle decomposition:
        #
        #   sy = sqrt(R[0,0]^2 + R[1,0]^2)  ("cos of pitch")
        #
        #   If sy > threshold (no gimbal lock):
        #     pitch = arctan2( R[2,1],  R[2,2])
        #     yaw   = arctan2(-R[2,0],  sy    )
        #     roll  = arctan2( R[1,0],  R[0,0])
        #
        # This is numerically stable for all normal head orientations.
        # No extra OpenCV function needed — just numpy math.

        sy = float(np.sqrt(rot_matrix[0, 0]**2 + rot_matrix[1, 0]**2))

        if sy > 1e-6:
            pitch = np.degrees(np.arctan2( rot_matrix[2, 1],  rot_matrix[2, 2]))
            yaw   = np.degrees(np.arctan2(-rot_matrix[2, 0],  sy))
            roll  = np.degrees(np.arctan2( rot_matrix[1, 0],  rot_matrix[0, 0]))
        else:
            # Gimbal lock — head pointing nearly straight up/down
            # Very rare in a classroom setting
            pitch = np.degrees(np.arctan2(-rot_matrix[1, 2], rot_matrix[1, 1]))
            yaw   = np.degrees(np.arctan2(-rot_matrix[2, 0], sy))
            roll  = 0.0

        return float(pitch), float(yaw), float(roll)

    # ──────────────────────────────────────────────────────
    #  _get_ear()
    # ──────────────────────────────────────────────────────
    def _get_ear(self, landmarks, frame_w, frame_h):
        """
        Calculates Eye Aspect Ratio (EAR) — how open the eyes are.

        EAR formula (Soukupova & Cech, 2016):
            EAR = (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||)

        p1,p4 = horizontal eye corners
        p2,p3,p5,p6 = vertical eye edge points

        Open eyes  → EAR ≈ 0.25-0.35
        Closed eyes → EAR ≈ 0.0-0.15
        """

        def single_eye_ear(ids):
            pts = np.array(
                [[landmarks[i].x * frame_w,
                  landmarks[i].y * frame_h]
                 for i in ids],
                dtype=np.float64
            )
            A = np.linalg.norm(pts[1] - pts[5])
            B = np.linalg.norm(pts[2] - pts[4])
            C = np.linalg.norm(pts[0] - pts[3])
            if C < 1e-6:
                return 0.30
            return (A + B) / (2.0 * C)

        return (single_eye_ear(LEFT_EYE_IDS) + single_eye_ear(RIGHT_EYE_IDS)) / 2.0

    # ──────────────────────────────────────────────────────
    #  _update_activity()
    # ──────────────────────────────────────────────────────
    def _update_activity(self, face_idx, current_center):
        """
        Resets the last-active timestamp when the face moves.
        Used to detect students who have been perfectly still
        for longer than INACTIVE_TIMEOUT seconds.
        """
        MOVE_THRESHOLD = 8   # pixels

        prev = self._last_positions.get(face_idx)

        if prev is None:
            self._last_positions[face_idx]   = current_center
            self._last_active_time[face_idx] = time.time()
            return

        dx   = current_center[0] - prev[0]
        dy   = current_center[1] - prev[1]
        dist = (dx**2 + dy**2) ** 0.5

        if dist > MOVE_THRESHOLD:
            self._last_active_time[face_idx] = time.time()
            self._last_positions[face_idx]   = current_center

    # ──────────────────────────────────────────────────────
    #  _classify()
    # ──────────────────────────────────────────────────────
    def _classify(self, face_idx, pitch, yaw, ear):
        """
        Applies threshold rules in priority order.

        1. DROWSY       — EAR too low (eyes nearly closed)
        2. INACTIVE     — no face movement for INACTIVE_TIMEOUT s
        3. LOOKING AWAY — |yaw| exceeds YAW_THRESHOLD
        4. DISTRACTED   — pitch exceeds PITCH_THRESHOLD (head down)
        5. ATTENTIVE    — all checks passed
        """

        if ear < config.EAR_THRESHOLD:
            return STATUS_DROWSY

        last_t = self._last_active_time.get(face_idx, time.time())
        if (time.time() - last_t) > config.INACTIVE_TIMEOUT:
            return STATUS_INACTIVE

        if abs(yaw) > config.YAW_THRESHOLD:
            return STATUS_LOOKING_AWAY

        if pitch > config.PITCH_THRESHOLD:
            return STATUS_DISTRACTED

        return STATUS_ATTENTIVE

    # ──────────────────────────────────────────────────────
    #  close()
    # ──────────────────────────────────────────────────────
    def close(self):
        """Releases MediaPipe Face Mesh resources."""
        self.face_mesh.close()
        print("[AttentionTracker] Face Mesh model released.")