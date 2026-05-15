# ============================================================
#  heatmap_system.py
#  AI Smart Classroom Monitoring System — SIH Project
#
#  PURPOSE:
#    Maintains a virtual classroom grid and maps detected
#    students to seats. Provides heatmap data for the
#    frontend dashboard to render as coloured circles.
#
#  HOW IT WORKS:
#    We define a classroom layout as a grid of ROWS × COLS seats.
#    When students are detected, we assign each bounding box to
#    the nearest seat using normalised (0–1) screen coordinates.
#    The frontend draws each seat as a coloured circle based
#    on the student's attention status.
#
#    The heatmap data is a list of seat dicts sent as JSON:
#    [
#      { "row": 0, "col": 2, "status": "ATTENTIVE",
#        "color": "#00ff88", "label": "S1", "active": true },
#      ...
#    ]
# ============================================================


# Map status strings to hex colours matching the frontend theme
STATUS_HEX_COLORS = {
    "ATTENTIVE":    "#00ff88",   # neon green
    "DISTRACTED":   "#ffe600",   # neon yellow
    "LOOKING AWAY": "#ff8800",   # neon orange
    "DROWSY":       "#ff2244",   # neon red
    "INACTIVE":     "#3388ff",   # neon blue
    "EMPTY":        "#1a2a3a",   # dark slate (no student)
}


class HeatmapSystem:
    """
    Converts attention tracking results into a classroom seat
    heatmap that the frontend can render.

    Usage:
        hm = HeatmapSystem(rows=4, cols=6)
        heatmap_data = hm.update(frame_w, frame_h, attention_results)
    """

    def __init__(self, rows=4, cols=6):
        """
        Args:
            rows: Number of seat rows in the classroom.
            cols: Number of seats per row.
        """
        self.rows = rows
        self.cols = cols

        # Build the initial empty seat grid
        # Each seat is a dict with its grid position and current status
        self.seats = self._build_empty_grid()

        print(f"[Heatmap] Classroom grid: {rows} rows × {cols} cols "
              f"= {rows * cols} seats.")

    # ──────────────────────────────────────────────────────
    #  _build_empty_grid()
    # ──────────────────────────────────────────────────────
    def _build_empty_grid(self):
        """
        Creates a list of empty seat dicts covering the full grid.
        """
        seats = []
        for r in range(self.rows):
            for c in range(self.cols):
                seats.append({
                    "row":    r,
                    "col":    c,
                    "status": "EMPTY",
                    "color":  STATUS_HEX_COLORS["EMPTY"],
                    "label":  "",
                    "active": False,
                    # Normalised position (0.0–1.0) of this seat
                    # in the classroom layout.
                    # row 0 = front of class, row N = back
                    "nx":     (c + 0.5) / self.cols,
                    "ny":     (r + 0.5) / self.rows,
                })
        return seats

    # ──────────────────────────────────────────────────────
    #  update()
    # ──────────────────────────────────────────────────────
    def update(self, frame_w, frame_h, attention_results):
        """
        Maps detected students to classroom seats and returns
        the updated heatmap as a list of seat dicts.

        Args:
            frame_w, frame_h:  Video frame dimensions (pixels).
            attention_results: List of dicts from AttentionTracker.

        Returns:
            List of seat dicts (serialisable to JSON).
        """

        # Reset all seats to empty at the start of each update
        for seat in self.seats:
            seat["status"] = "EMPTY"
            seat["color"]  = STATUS_HEX_COLORS["EMPTY"]
            seat["label"]  = ""
            seat["active"] = False

        if not attention_results or frame_w == 0 or frame_h == 0:
            return self._serialise()

        # For each detected student, find the nearest empty seat
        assigned = set()  # seat indices already assigned this frame

        for i, res in enumerate(attention_results):
            x, y, w, h = res["box"]

            # Normalise the face centre to 0.0–1.0 range
            nx = (x + w / 2) / frame_w
            ny = (y + h / 2) / frame_h

            # Find the closest unassigned seat
            best_idx  = None
            best_dist = float("inf")

            for j, seat in enumerate(self.seats):
                if j in assigned:
                    continue
                dx   = seat["nx"] - nx
                dy   = seat["ny"] - ny
                dist = dx * dx + dy * dy
                if dist < best_dist:
                    best_dist = dist
                    best_idx  = j

            if best_idx is None:
                continue   # more students than seats — skip

            assigned.add(best_idx)
            status = res.get("status", "INACTIVE")

            self.seats[best_idx]["status"] = status
            self.seats[best_idx]["color"]  = STATUS_HEX_COLORS.get(
                status, STATUS_HEX_COLORS["INACTIVE"]
            )
            self.seats[best_idx]["label"]  = f"S{i + 1}"
            self.seats[best_idx]["active"] = True

        return self._serialise()

    # ──────────────────────────────────────────────────────
    #  _serialise()
    # ──────────────────────────────────────────────────────
    def _serialise(self):
        """
        Returns a JSON-safe copy of the seat list.
        We exclude the internal nx/ny fields from the output.
        """
        return [
            {
                "row":    s["row"],
                "col":    s["col"],
                "status": s["status"],
                "color":  s["color"],
                "label":  s["label"],
                "active": s["active"],
            }
            for s in self.seats
        ]
    