# ============================================================
#  analytics_engine.py
#  AI Smart Classroom Monitoring System — SIH Project
#
#  PURPOSE:
#    Collects per-frame attention data and produces:
#      - Rolling engagement score (last 60 seconds)
#      - Attention timeline (for the chart)
#      - Smart AI-generated insight messages
#      - Session summary statistics
#      - Alert detection (sudden drops in attention)
#
#  This module is PURE PYTHON — no OpenCV, no MediaPipe.
#  It only does math and bookkeeping on the results that
#  attention_tracker.py already produced.
# ============================================================

import time
import collections
import random   # used to vary insight message phrasing slightly


# ============================================================
#  AnalyticsEngine
# ============================================================

class AnalyticsEngine:
    """
    Ingests per-frame attention results and maintains historical
    statistics used by the dashboard and API.

    Usage:
        engine = AnalyticsEngine()
        engine.update(attention_results)     # call every frame
        snapshot = engine.get_snapshot()     # call from API
    """

    def __init__(self):
        # ── Rolling window ──────────────────────────────────
        # We keep the last WINDOW_SIZE seconds of data.
        # Each entry is a dict: {timestamp, engagement_pct, counts}
        self.WINDOW_SECONDS = 60

        # deque automatically drops old entries when maxlen is set.
        # We store one entry per second (approximated).
        self.history = collections.deque(maxlen=self.WINDOW_SECONDS)

        # ── Session tracking ────────────────────────────────
        self.session_start  = time.time()
        self.total_frames   = 0
        self.peak_attention = 0.0    # highest engagement % seen
        self.low_attention  = 100.0  # lowest engagement % seen

        # ── Alert system ────────────────────────────────────
        # Store the last 5 alerts so the dashboard can display them
        self.alerts = collections.deque(maxlen=5)
        self._last_alert_time  = 0.0
        self._alert_cooldown   = 15.0  # seconds between same alert type
        self._prev_engagement  = None

        # ── Insight refresh ─────────────────────────────────
        self._last_insight_time = 0.0
        self._current_insights  = []

        print("[Analytics] Engine initialised.")

    # ──────────────────────────────────────────────────────
    #  update() — call every frame with current results
    # ──────────────────────────────────────────────────────
    def update(self, attention_results):
        """
        Processes one frame's worth of attention data.

        Args:
            attention_results: List of dicts from AttentionTracker.
                               Each has a "status" key.
        """
        self.total_frames += 1
        now = time.time()

        # Count statuses
        total      = len(attention_results)
        attentive  = sum(1 for r in attention_results if r.get("status") == "ATTENTIVE")
        distracted = sum(1 for r in attention_results if r.get("status") == "DISTRACTED")
        looking    = sum(1 for r in attention_results if r.get("status") == "LOOKING AWAY")
        drowsy     = sum(1 for r in attention_results if r.get("status") == "DROWSY")
        inactive   = sum(1 for r in attention_results if r.get("status") == "INACTIVE")

        # Engagement percentage
        engagement = round((attentive / total * 100), 1) if total > 0 else 0.0

        # Update peak / low
        if total > 0:
            self.peak_attention = max(self.peak_attention, engagement)
            self.low_attention  = min(self.low_attention,  engagement)

        # Store into rolling history (one record per second approx.)
        if not self.history or (now - self.history[-1]["ts"]) >= 1.0:
            self.history.append({
                "ts":         now,
                "engagement": engagement,
                "total":      total,
                "attentive":  attentive,
                "distracted": distracted,
                "looking":    looking,
                "drowsy":     drowsy,
                "inactive":   inactive,
            })

        # Check for alerts
        self._check_alerts(engagement, total, drowsy, distracted, now)

        # Refresh insights every 10 seconds
        if now - self._last_insight_time > 10.0:
            self._current_insights = self._generate_insights(
                engagement, total, attentive, distracted,
                drowsy, inactive, now
            )
            self._last_insight_time = now

        self._prev_engagement = engagement

    # ──────────────────────────────────────────────────────
    #  get_snapshot() — returns everything the API needs
    # ──────────────────────────────────────────────────────
    def get_snapshot(self):
        """
        Returns a dict containing all analytics data.
        This is serialised to JSON and sent to the dashboard.
        """
        now          = time.time()
        elapsed_sec  = int(now - self.session_start)
        elapsed_str  = f"{elapsed_sec // 60}m {elapsed_sec % 60}s"

        # Build timeline list for the chart (last 60 points)
        timeline = [
            {
                "t":   round(h["ts"] - self.session_start, 1),
                "eng": h["engagement"],
                "n":   h["total"]
            }
            for h in self.history
        ]

        # Latest values (from most recent history entry)
        latest = self.history[-1] if self.history else {
            "engagement": 0, "total": 0, "attentive": 0,
            "distracted": 0, "looking": 0, "drowsy": 0, "inactive": 0
        }

        # Average engagement over the window
        avg_eng = 0.0
        if self.history:
            avg_eng = round(
                sum(h["engagement"] for h in self.history) / len(self.history), 1
            )

        return {
            "engagement":   latest["engagement"],
            "avg_engagement": avg_eng,
            "peak":         self.peak_attention,
            "low":          self.low_attention,
            "total":        latest["total"],
            "attentive":    latest["attentive"],
            "distracted":   latest["distracted"],
            "looking_away": latest["looking"],
            "drowsy":       latest["drowsy"],
            "inactive":     latest["inactive"],
            "session_time": elapsed_str,
            "total_frames": self.total_frames,
            "timeline":     timeline,
            "alerts":       list(self.alerts),
            "insights":     self._current_insights,
            "classroom_score": self._compute_classroom_score(avg_eng),
        }

    # ──────────────────────────────────────────────────────
    #  _compute_classroom_score()
    # ──────────────────────────────────────────────────────
    def _compute_classroom_score(self, avg_engagement):
        """
        Maps average engagement to a 0–100 classroom performance score.
        Also returns a letter grade and a colour indicator.
        """
        score = round(avg_engagement)

        if score >= 80:
            grade, color = "A", "green"
        elif score >= 65:
            grade, color = "B", "cyan"
        elif score >= 50:
            grade, color = "C", "yellow"
        elif score >= 35:
            grade, color = "D", "orange"
        else:
            grade, color = "F", "red"

        return {"score": score, "grade": grade, "color": color}

    # ──────────────────────────────────────────────────────
    #  _check_alerts()
    # ──────────────────────────────────────────────────────
    def _check_alerts(self, engagement, total, drowsy, distracted, now):
        """
        Generates alert messages when attention thresholds are crossed.
        Alerts are rate-limited to avoid spamming the dashboard.
        """

        if total == 0:
            return

        def add_alert(message, level="warning"):
            # level: "warning" | "danger" | "info"
            self.alerts.appendleft({
                "msg":   message,
                "level": level,
                "time":  time.strftime("%H:%M:%S")
            })

        cooldown_ok = (now - self._last_alert_time) > self._alert_cooldown

        # Alert: engagement drop
        if self._prev_engagement is not None and cooldown_ok:
            drop = self._prev_engagement - engagement
            if drop >= 20:
                add_alert(
                    f"⚠ Attention dropped {drop:.0f}% in 1 second!",
                    "danger"
                )
                self._last_alert_time = now

        # Alert: very low engagement
        if engagement < 30 and cooldown_ok:
            add_alert(
                f"🔴 Critical: Only {engagement:.0f}% students attentive!",
                "danger"
            )
            self._last_alert_time = now

        # Alert: drowsy students
        if drowsy >= 2 and cooldown_ok:
            add_alert(
                f"😴 {drowsy} student(s) showing drowsiness signs.",
                "warning"
            )
            self._last_alert_time = now

        # Alert: high engagement (positive)
        if engagement >= 90 and cooldown_ok:
            add_alert(
                f"✅ Excellent! {engagement:.0f}% class engagement.",
                "info"
            )
            self._last_alert_time = now

    # ──────────────────────────────────────────────────────
    #  _generate_insights()
    # ──────────────────────────────────────────────────────
    def _generate_insights(self, engagement, total, attentive,
                            distracted, drowsy, inactive, now):
        """
        Generates human-readable AI insight strings for the dashboard.
        These appear in the "AI Insights" panel.
        """
        insights = []
        elapsed  = now - self.session_start

        if total == 0:
            return ["No students detected. Waiting for classroom activity."]

        # Engagement-based insights
        if engagement >= 80:
            insights.append(f"🟢 Strong classroom engagement at {engagement:.0f}%.")
        elif engagement >= 55:
            insights.append(f"🟡 Moderate engagement. {distracted} student(s) distracted.")
        else:
            insights.append(f"🔴 Low engagement ({engagement:.0f}%). Consider a break or activity change.")

        # Drowsiness insight
        if drowsy >= 1:
            insights.append(f"😴 {drowsy} student(s) may be drowsy. Check lighting or room temperature.")

        # Inactivity insight
        if inactive >= 2:
            insights.append(f"💤 {inactive} students inactive for extended periods.")

        # Time-based insights
        if elapsed > 1200:   # 20 minutes
            insights.append("⏱ Session running 20+ min. Engagement tends to drop — consider a 2-minute break.")
        elif elapsed > 2400:  # 40 minutes
            insights.append("⏱ Session running 40+ min. High fatigue risk — interactive activity recommended.")

        # Distraction insight
        if distracted >= total // 2 and total >= 4:
            insights.append("📵 Over half the class is distracted. Check for distractions in the room.")

        # Peak vs current comparison
        if self.peak_attention - engagement > 25:
            insights.append(
                f"📉 Engagement fell from peak {self.peak_attention:.0f}% to {engagement:.0f}%."
            )

        # Positive insight
        if attentive == total and total >= 3:
            insights.append("🏆 Perfect attention! All detected students are focused.")

        return insights[:4]   # Return max 4 insights at a time
    