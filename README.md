# 🏫 AI Smart Classroom Monitoring System

An AI-powered Smart Classroom Monitoring System built for Smart India Hackathon (SIH).

This project uses:

* 📱 Old Android phone as wireless classroom camera
* 🧠 Artificial Intelligence for classroom analysis
* 🎥 OpenCV + MediaPipe for real-time computer vision
* 🌐 Futuristic frontend dashboard for teachers
* ⚡ Real-time classroom attention analytics

The system helps teachers understand:

* student attention,
* distraction,
* engagement,
* classroom activity,
* classroom intelligence insights.

---

# 🚀 Features

## ✅ Current Working Features

### 🎥 Live Classroom Streaming

* Android phone used as wireless IP camera
* Real-time classroom feed
* Low-latency streaming

### 👨‍🎓 Multi-Student Face Detection

* Detects multiple students simultaneously
* Real-time face bounding boxes
* Confidence percentage display

### 🧠 Attention Tracking

The AI classifies students as:

* ATTENTIVE
* DISTRACTED
* LOOKING AWAY
* DROWSY
* INACTIVE

### 📊 Real-Time Analytics

* Student count
* Attention percentage
* Classroom engagement metrics
* FPS monitor
* AI classroom insights

### 🌐 Futuristic Frontend Dashboard

* Large cinematic classroom feed
* Glassmorphism UI
* Neon AI theme
* Dropdown module system
* Dynamic pinned widgets
* Real-time heatmap

### 🗺️ Classroom Heatmap

Visual classroom layout showing:

* Green → attentive
* Yellow → distracted
* Orange → looking away
* Red → drowsy
* Blue → inactive

### 📸 Screenshot System

Save classroom screenshots during live sessions.

### ⚡ Performance Optimizations

* Frame skipping
* Downscaled detection
* Buffer optimization
* Lightweight processing

---

# 🛠️ Tech Stack

## Backend

* Python 3.11
* OpenCV
* MediaPipe
* FastAPI
* NumPy

## Frontend

* HTML
* CSS
* JavaScript

## AI / Computer Vision

* MediaPipe Face Detection
* MediaPipe Face Mesh
* Head Pose Estimation
* Eye Tracking Logic

---

# 📁 Project Structure

```text
AI_Classroom_System/
│
├── index.html
├── style.css
├── script.js
│
├── main.py
├── config.py
├── camera.py
├── display.py
├── stream.py
├── backend_api.py
├── heatmap_system.py
├── analytics_engine.py
├── requirements.txt
│
├── ai_engine/
│   ├── __init__.py
│   ├── face_detector.py
│   └── attention_tracker.py
│
├── screenshots/
│
└── README.md
```

---

# 📦 Stable Library Versions

IMPORTANT:
This project uses stable compatible versions.

```txt
Python==3.11
opencv-python==4.10.0.84
mediapipe==0.10.14
numpy==1.26.4
```

DO NOT use latest MediaPipe versions.

This project uses:

```python
mp.solutions
```

The newer MediaPipe Tasks API is NOT compatible with this project.

---

# ⚙️ Installation Guide

# Step 1 — Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/AI-Classroom-System.git
```

---

# Step 2 — Open Project

Open the project folder in:

* VS Code
* Windsurf

---

# Step 3 — Create Virtual Environment

```bash
python -m venv venv
```

---

# Step 4 — Activate Virtual Environment

## Windows

```powershell
.\venv\Scripts\activate
```

## macOS/Linux

```bash
source venv/bin/activate
```

---

# Step 5 — Install Requirements

```bash
pip install -r requirements.txt
```

---

# 📱 Android Camera Setup

This project uses an old Android phone as wireless classroom camera.

## Install App

Install:

* IP Webcam app from Play Store

---

# Start Streaming

1. Open IP Webcam app
2. Scroll down
3. Tap:

```text
Start Server
```

You will see something like:

```text
http://192.168.1.5:8080
```

---

# Update config.py

Open:

```text
config.py
```

Update:

```python
CAMERA_URL = "http://YOUR_PHONE_IP:8080/video"
```

Example:

```python
CAMERA_URL = "http://192.168.1.5:8080/video"
```

IMPORTANT:
Phone and laptop MUST be on same WiFi.

---

# ▶️ Run Project

## Start AI Backend

```bash
python main.py
```

---

# 🌐 Frontend Dashboard

The frontend dashboard can be:

* run locally,
* or deployed using Vercel.

---

# 🎮 Controls

| Key | Action                 |
| --- | ---------------------- |
| Q   | Quit program           |
| S   | Save screenshot        |
| P   | Pause/resume detection |

---

# 🧠 Attention Tracking Logic

The system analyzes:

* head direction,
* facial orientation,
* eye landmarks,
* movement patterns.

Student states:

| State        | Meaning               |
| ------------ | --------------------- |
| ATTENTIVE    | Looking forward       |
| DISTRACTED   | Excessive movement    |
| LOOKING AWAY | Head turned sideways  |
| DROWSY       | Eyes closed/head down |
| INACTIVE     | Very low movement     |

---

# 🗺️ Heatmap System

Each student represented as colored node:

| Color  | Meaning      |
| ------ | ------------ |
| Green  | Attentive    |
| Yellow | Distracted   |
| Orange | Looking Away |
| Red    | Drowsy       |
| Blue   | Inactive     |

---

# 📊 Dashboard Features

The dashboard includes:

* Live classroom feed
* Classroom intelligence insights
* Student count
* Classroom attention score
* Heatmap visualization
* AI analytics
* FPS monitor
* Engagement trends
* Dropdown-based widget system

---

# 🐛 Troubleshooting

## ❌ Could not connect to stream

Check:

* IP Webcam running?
* Same WiFi?
* Correct IP in config.py?

Test in browser:

```text
http://YOUR_PHONE_IP:8080
```

---

## ❌ No module named 'mediapipe'

Activate venv first:

```powershell
.\venv\Scripts\activate
```

Then:

```bash
pip install -r requirements.txt
```

---

## ❌ PowerShell blocks venv activation

Run:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

---

## ❌ Face detection not working

Try:

* better lighting
* face toward camera
* lower detection confidence

---

## ❌ Video laggy

Lower resolution in IP Webcam:

```text
640x480
15 FPS
```

Also:

* reduce detection scale
* increase frame skip count

---

# 📡 Hotspot Mode

If campus WiFi blocks local connections:

1. Turn on phone hotspot
2. Connect laptop to hotspot
3. Start IP Webcam
4. Update config.py IP

This works very reliably during hackathon demos.

---

# 🔮 Future Upgrades

Possible future improvements:

* Emotion detection
* Voice analysis
* Attendance system
* Face recognition
* AI-generated lecture insights
* Multi-classroom support
* Cloud dashboard
* Mobile app integration
* Teacher recommendation engine

---

# 🎯 Smart India Hackathon Vision

This project demonstrates:

* Artificial Intelligence
* Computer Vision
* Smart Education
* Real-Time Analytics
* Human Attention Analysis
* Classroom Intelligence Systems

The goal is to create:

> A low-cost AI-powered smart classroom platform that improves teaching effectiveness and classroom engagement.



