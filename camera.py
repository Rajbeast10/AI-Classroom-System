# ============================================================
#  camera.py  (UNCHANGED from v1 — fully compatible with v2)
#  AI Smart Classroom Monitoring System — SIH Project
#  Purpose: Handles connecting to the Android IP Webcam stream,
#           reading frames reliably, and reconnecting if the
#           stream drops.
# ============================================================

import cv2
import time
import sys
import config


class ClassroomCamera:
    """
    Manages the connection to the Android IP Webcam stream.

    Usage:
        cam = ClassroomCamera()
        cam.connect()
        success, frame = cam.read()
        cam.release()
    """

    def __init__(self):
        self.cap               = None
        self.reconnect_attempts = 0
        self.is_connected      = False

    def connect(self):
        """
        Opens the IP Webcam stream.
        Retries up to MAX_RECONNECT_ATTEMPTS times if it fails.
        Exits the program if connection never succeeds.
        """
        print(f"\n[Camera] Connecting to: {config.CAMERA_URL}")
        print(f"[Camera] Make sure IP Webcam app is running on your phone!\n")

        for attempt in range(1, config.MAX_RECONNECT_ATTEMPTS + 1):
            print(f"[Camera] Attempt {attempt} of {config.MAX_RECONNECT_ATTEMPTS} ...")

            self.cap = cv2.VideoCapture(config.CAMERA_URL)

            if self.cap.isOpened():
                success, _ = self.cap.read()
                if success:
                    self._apply_optimizations()
                    self.is_connected = True
                    print(f"[Camera] ✓ Connected successfully on attempt {attempt}!\n")
                    return

            print(f"[Camera] ✗ Attempt {attempt} failed. "
                  f"Retrying in {config.RECONNECT_WAIT_SEC}s ...")
            if self.cap:
                self.cap.release()
            time.sleep(config.RECONNECT_WAIT_SEC)

        print("\n[Camera] ERROR: Could not connect after all attempts.")
        print("         Checklist:")
        print("         1. Is IP Webcam app open and 'Start server' tapped?")
        print(f"         2. Is PHONE_IP correct? (currently: {config.PHONE_IP})")
        print("         3. Are phone AND laptop on the SAME Wi-Fi?")
        print("         4. Test in browser:")
        print(f"            {config.CAMERA_URL}")
        sys.exit(1)

    def _apply_optimizations(self):
        """Sets buffer size to 1 so we always get the latest frame."""
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, config.BUFFER_SIZE)

    def read(self):
        """
        Reads one frame from the stream.
        Returns: (success: bool, frame: numpy array or None)
        """
        if self.cap is None or not self.cap.isOpened():
            print("[Camera] Stream lost. Attempting reconnect ...")
            self.connect()

        success, frame = self.cap.read()

        if not success:
            print("[Camera] Warning: empty frame received.")
            return False, None

        return True, frame

    def release(self):
        """Releases the video capture object."""
        if self.cap:
            self.cap.release()
            self.is_connected = False
            print("[Camera] Stream released cleanly.")