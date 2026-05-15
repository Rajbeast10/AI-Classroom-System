# ============================================================
#  backend_api.py
#  AI Smart Classroom Monitoring System — SIH Project
#
#  PURPOSE:
#    FastAPI web server that:
#      1. Serves the frontend HTML dashboard
#      2. Streams live MJPEG video to the browser
#      3. Provides a REST endpoint for analytics snapshots
#      4. Provides a WebSocket endpoint for real-time updates
#
#  HOW TO RUN (in a second terminal, venv activated):
#      python backend_api.py
#
#  Then open your browser at:
#      http://localhost:8000
#
#  IMPORTANT:
#    This file shares data with main.py through the global
#    `shared_state` dict. main.py writes to it; this API reads it.
#    Both run in the same Python process — main.py starts
#    the API server in a background thread.
# ============================================================

import io
import time
import asyncio
import threading
import uvicorn
import cv2
import numpy as np

from fastapi                  import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses        import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles      import StaticFiles
from fastapi.middleware.cors  import CORSMiddleware


# ============================================================
#  SHARED STATE — written by main.py, read by this API
# ============================================================
#
#  This dict is the bridge between the AI pipeline (main.py)
#  and the web dashboard (frontend/index.html).
#
#  main.py imports this dict and writes to it every frame.
#  The API endpoints below read from it and send to the browser.

shared_state = {
    "frame":            None,   # Latest annotated BGR frame (NumPy array)
    "analytics":        {},     # Latest snapshot from AnalyticsEngine
    "heatmap":          [],     # Latest heatmap seat list
    "fps":              0.0,    # Current FPS
    "attention_results": [],    # Latest list from AttentionTracker
    "frame_lock":       threading.Lock(),  # Thread safety for frame access
}


# ============================================================
#  FastAPI app setup
# ============================================================

app = FastAPI(title="AI Classroom Dashboard API")

# Allow the browser (served from the same origin) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend/ folder as static files at /static
# index.html, style.css, script.js live here
app.mount("/static", StaticFiles(directory="frontend"), name="static")


# ============================================================
#  ROUTE: / — serve the dashboard HTML
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """
    Serves the main dashboard page.
    Reads frontend/index.html from disk and returns it.
    """
    try:
        with open("frontend/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(
            content="<h2>frontend/index.html not found.</h2>"
                    "<p>Make sure the frontend/ folder exists.</p>",
            status_code=404
        )


# ============================================================
#  ROUTE: /video_feed — MJPEG stream for the dashboard camera
# ============================================================

def generate_mjpeg():
    """
    Generator function that yields JPEG-encoded frames one by one.
    The browser treats this as a continuous video stream using
    multipart/x-mixed-replace MIME type.
    """
    while True:
        with shared_state["frame_lock"]:
            frame = shared_state["frame"]

        if frame is None:
            # No frame yet — yield a black placeholder
            placeholder = np.zeros((360, 640, 3), dtype=np.uint8)
            cv2.putText(placeholder, "Waiting for camera...",
                        (160, 180), cv2.FONT_HERSHEY_SIMPLEX,
                        0.8, (0, 200, 200), 2)
            frame = placeholder

        # Encode frame as JPEG
        _, buffer = cv2.imencode(
            ".jpg", frame,
            [cv2.IMWRITE_JPEG_QUALITY, 75]   # 75% quality = good balance
        )

        # Yield the MJPEG boundary + frame bytes
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n"
            + buffer.tobytes()
            + b"\r\n"
        )

        time.sleep(0.033)   # ~30 FPS cap for the stream


@app.get("/video_feed")
async def video_feed():
    """
    Streams live classroom video as MJPEG to the browser.
    Used as the <img src="/video_feed"> in the dashboard.
    """
    return StreamingResponse(
        generate_mjpeg(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


# ============================================================
#  ROUTE: /analytics — REST snapshot endpoint
# ============================================================

@app.get("/analytics")
async def get_analytics():
    """
    Returns the latest analytics snapshot as JSON.
    The frontend polls this every 2 seconds as a fallback
    if the WebSocket connection is not available.
    """
    return JSONResponse(content=shared_state.get("analytics", {}))


# ============================================================
#  ROUTE: /heatmap — heatmap data endpoint
# ============================================================

@app.get("/heatmap")
async def get_heatmap():
    """
    Returns the current classroom heatmap seat data as JSON.
    """
    return JSONResponse(content=shared_state.get("heatmap", []))


# ============================================================
#  ROUTE: /ws — WebSocket for real-time dashboard updates
# ============================================================

# Keep track of all connected WebSocket clients
connected_clients: list[WebSocket] = []


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket connection handler.
    Each browser tab that opens the dashboard connects here.
    We push analytics + heatmap updates every second.
    """
    await websocket.accept()
    connected_clients.append(websocket)
    print(f"[API] WebSocket client connected. Total: {len(connected_clients)}")

    try:
        while True:
            # Build the message payload
            payload = {
                "analytics": shared_state.get("analytics", {}),
                "heatmap":   shared_state.get("heatmap",   []),
                "fps":       round(shared_state.get("fps", 0.0), 1),
            }

            # Send as JSON text
            await websocket.send_json(payload)

            # Wait 1 second before next push
            await asyncio.sleep(1.0)

    except WebSocketDisconnect:
        connected_clients.remove(websocket)
        print(f"[API] WebSocket client disconnected. "
              f"Remaining: {len(connected_clients)}")
    except Exception as e:
        print(f"[API] WebSocket error: {e}")
        if websocket in connected_clients:
            connected_clients.remove(websocket)


# ============================================================
#  start_server() — called from main.py in a background thread
# ============================================================

def start_server(host="0.0.0.0", port=8000):
    """
    Starts the FastAPI/uvicorn server.
    Call this from main.py in a daemon thread so it runs
    alongside the OpenCV detection loop.

    Args:
        host: IP to bind to. "0.0.0.0" = accessible from any device on LAN.
        port: Port number. Default 8000.
    """
    print(f"\n[API] Starting dashboard server at http://localhost:{port}")
    print(f"[API] Open your browser and go to: http://localhost:{port}\n")

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="warning"   # suppress noisy uvicorn access logs
    )