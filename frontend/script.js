// ============================================================
//  script.js — AI Classroom Monitor (Redesigned v3.1)
//
//  Responsibilities:
//    1. Clock updates
//    2. WebSocket connection + REST polling fallback
//    3. Updating all live data fields
//    4. Dropdown menu open/close
//    5. Module PIN system (only one at a time)
//    6. Canvas chart drawing (timeline, fps sparkline, trend)
//    7. Heatmap rendering
//    8. Engagement ring + meter animation
//    9. AI insights and suggestions rendering
// ============================================================

"use strict";

// ── CONFIG (must match heatmap_system.py) ─────────────────────
const HEATMAP_ROWS = 4;
const HEATMAP_COLS = 6;

// ── State ──────────────────────────────────────────────────────
let wsConnected   = false;
let socket        = null;
let pinnedModule  = null;       // currently pinned module key
let timelineData  = [];         // [{t, eng}, ...]
let fpsHistory    = [];         // rolling FPS values for sparkline
let lastAnalytics = {};
let lastHeatmap   = [];


// ══════════════════════════════════════════════════════════════
//  1. CLOCK
// ══════════════════════════════════════════════════════════════

function tickClock() {
  const t = new Date().toTimeString().slice(0, 8);
  document.getElementById("clock").textContent = t;
}
setInterval(tickClock, 1000);
tickClock();


// ══════════════════════════════════════════════════════════════
//  2. WEBSOCKET + POLLING FALLBACK
// ══════════════════════════════════════════════════════════════

function connectWS() {
  const url = `ws://${window.location.host}/ws`;
  socket = new WebSocket(url);

  socket.onopen = () => {
    wsConnected = true;
    setOnline(true);
  };

  socket.onmessage = ({ data }) => {
    try {
      const msg = JSON.parse(data);
      if (msg.analytics) ingest(msg.analytics, msg.fps || 0);
      if (msg.heatmap)   lastHeatmap = msg.heatmap;
      if (pinnedModule === "heatmap") renderHeatmap(lastHeatmap);
    } catch (e) { /* ignore parse errors */ }
  };

  socket.onclose = () => {
    wsConnected = false;
    setOnline(false);
    setTimeout(connectWS, 3000);
  };

  socket.onerror = () => socket.close();
}

async function pollFallback() {
  if (wsConnected) return;
  try {
    const [aRes, hRes] = await Promise.all([
      fetch("/analytics"), fetch("/heatmap")
    ]);
    const a = await aRes.json();
    const h = await hRes.json();
    ingest(a, a.fps || 0);
    lastHeatmap = h;
    if (pinnedModule === "heatmap") renderHeatmap(lastHeatmap);
  } catch (_) {}
}
setInterval(pollFallback, 2000);

function setOnline(on) {
  const chip  = document.getElementById("conn-chip");
  const label = chip.querySelector(".chip-label");
  if (on) {
    chip.classList.add("online");
    label.textContent = "LIVE";
  } else {
    chip.classList.remove("online");
    label.textContent = "RECONNECTING";
  }
}


// ══════════════════════════════════════════════════════════════
//  3. DATA INGESTION — updates all DOM elements
// ══════════════════════════════════════════════════════════════

function ingest(data, fps) {
  if (!data || !Object.keys(data).length) return;
  lastAnalytics = data;

  // ── Student counts ─────────────────────────────────────────
  set("ic-total",    data.total        ?? 0);
  set("ic-att",      data.attentive    ?? 0);
  set("ic-dis",      data.distracted   ?? 0);
  set("ic-look",     data.looking_away ?? 0);
  set("ic-drowsy",   data.drowsy       ?? 0);
  set("ic-inactive", data.inactive     ?? 0);

  // ── Engagement ring ─────────────────────────────────────────
  const eng = data.engagement ?? 0;
  updateRing(eng);

  // ── Grade pill ──────────────────────────────────────────────
  const cs    = data.classroom_score || {};
  const grade = cs.grade || "—";
  const gpill = document.getElementById("grade-pill");
  gpill.textContent = `GRADE  ${grade}`;
  gpill.className   = `grade-pill grade-${grade}`;

  // ── Meter ───────────────────────────────────────────────────
  updateMeter(eng, data.peak ?? 0, data.avg_engagement ?? 0);

  // ── FPS badge ───────────────────────────────────────────────
  const fpsVal = (fps || data.fps || 0).toFixed(1);
  set("vc-fps", `${fpsVal} FPS`);
  fpsHistory.push(parseFloat(fpsVal));
  if (fpsHistory.length > 60) fpsHistory.shift();

  // ── Timeline ────────────────────────────────────────────────
  if (data.timeline) timelineData = data.timeline;

  // ── Insights ────────────────────────────────────────────────
  if (data.insights) renderInsights(data.insights);

  // ── Pinned module refresh ───────────────────────────────────
  refreshPinnedModule(data);
}

function set(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}


// ══════════════════════════════════════════════════════════════
//  4. ENGAGEMENT RING
// ══════════════════════════════════════════════════════════════

function updateRing(pct) {
  const arc  = document.getElementById("eng-arc");
  const circ = 2 * Math.PI * 30;           // r=30 in SVG
  const fill = (pct / 100) * circ;
  arc.style.strokeDasharray = `${fill} ${circ - fill}`;

  // Colour by value
  let color = "var(--green)";
  if (pct < 40)       color = "var(--red)";
  else if (pct < 65)  color = "var(--yellow)";
  arc.style.stroke = color;
  arc.style.filter = `drop-shadow(0 0 5px ${color})`;

  set("eng-pct", `${Math.round(pct)}%`);
}


// ══════════════════════════════════════════════════════════════
//  5. ATTENTION METER
// ══════════════════════════════════════════════════════════════

function updateMeter(pct, peak, avg) {
  const fill = document.getElementById("meter-fill");
  const val  = document.getElementById("meter-val");

  fill.style.width = `${Math.min(100, pct)}%`;
  val.textContent  = `${Math.round(pct)}%`;

  if (pct >= 70)
    fill.style.background = "linear-gradient(90deg, #004433, var(--green))";
  else if (pct >= 40)
    fill.style.background = "linear-gradient(90deg, #554400, var(--yellow))";
  else
    fill.style.background = "linear-gradient(90deg, #440011, var(--red))";

  set("m-peak", `${Math.round(peak)}%`);
  set("m-avg",  `${Math.round(avg)}%`);
}


// ══════════════════════════════════════════════════════════════
//  6. INSIGHTS
// ══════════════════════════════════════════════════════════════

function renderInsights(insights) {
  const list = document.getElementById("insights-list");
  if (!list) return;
  if (!insights || !insights.length) return;

  list.innerHTML = insights
    .map(txt => `<div class="insight-row">${esc(txt)}</div>`)
    .join("");
}


// ══════════════════════════════════════════════════════════════
//  7. DROPDOWN MENU
// ══════════════════════════════════════════════════════════════

const menuBtn      = document.getElementById("menu-btn");
const menuEl       = document.getElementById("module-menu");
const backdropEl   = document.getElementById("backdrop");

function openMenu()  {
  menuEl.classList.add("open");
  backdropEl.classList.add("visible");
}
function closeMenu() {
  menuEl.classList.remove("open");
  backdropEl.classList.remove("visible");
}

menuBtn.addEventListener("click", (e) => {
  e.stopPropagation();
  menuEl.classList.contains("open") ? closeMenu() : openMenu();
});
backdropEl.addEventListener("click", closeMenu);

// Handle menu item clicks
document.querySelectorAll(".menu-item").forEach(btn => {
  btn.addEventListener("click", () => {
    const mod = btn.dataset.module;
    togglePin(mod);
    closeMenu();
  });
});


// ══════════════════════════════════════════════════════════════
//  8. PIN SYSTEM — only one module active at a time
// ══════════════════════════════════════════════════════════════

const moduleNames = {
  heatmap:     "CLASSROOM HEATMAP",
  analytics:   "ANALYTICS CHART",
  attention:   "ATTENTION TRENDS",
  session:     "SESSION STATS",
  fps:         "FPS MONITOR",
  suggestions: "AI SUGGESTIONS",
  timeline:    "ACTIVITY TIMELINE",
  mood:        "CLASSROOM MOOD",
};

function togglePin(mod) {
  if (pinnedModule === mod) {
    // Clicking the same module → unpin
    unpinModule();
  } else {
    pinModule(mod);
  }
}

function pinModule(mod) {
  // Remove active class from all menu items
  document.querySelectorAll(".menu-item").forEach(b => b.classList.remove("active"));

  // Set active on selected
  const btn = document.querySelector(`.menu-item[data-module="${mod}"]`);
  if (btn) btn.classList.add("active");

  pinnedModule = mod;

  // Clone template into panel body
  const tpl = document.getElementById(`tpl-${mod}`);
  if (!tpl) return;
  const clone = tpl.content.cloneNode(true);

  const ppBody  = document.getElementById("pp-body");
  const ppTitle = document.getElementById("pp-title");
  const ppPanel = document.getElementById("pinned-panel");

  ppBody.innerHTML = "";
  ppBody.appendChild(clone);
  ppTitle.textContent = moduleNames[mod] || mod.toUpperCase();
  ppPanel.classList.add("visible");

  // Immediately populate with latest data
  refreshPinnedModule(lastAnalytics);
  if (mod === "heatmap") renderHeatmap(lastHeatmap);
}

function unpinModule() {
  document.querySelectorAll(".menu-item").forEach(b => b.classList.remove("active"));
  const ppPanel = document.getElementById("pinned-panel");
  ppPanel.classList.remove("visible");
  pinnedModule = null;
}

// Close button
document.getElementById("pp-close").addEventListener("click", unpinModule);

// Refresh whatever module is currently pinned
function refreshPinnedModule(data) {
  if (!pinnedModule || !data) return;

  switch (pinnedModule) {
    case "analytics":
    case "attention":
    case "timeline":
      drawTimelineChart(pinnedModule === "timeline" ? "timeline-chart" : "attention-chart");
      break;
    case "fps":
      updateFpsModule(data);
      break;
    case "session":
      updateSessionModule(data);
      break;
    case "suggestions":
      updateSuggestionsModule(data);
      break;
    case "mood":
      updateMoodModule(data);
      break;
    // heatmap refreshed separately via renderHeatmap()
  }
}


// ══════════════════════════════════════════════════════════════
//  9. MODULE CONTENT RENDERERS
// ══════════════════════════════════════════════════════════════

// ── Heatmap ───────────────────────────────────────────────────
function renderHeatmap(seats) {
  const grid = document.getElementById("heatmap-grid");
  if (!grid || !seats) return;

  grid.style.gridTemplateColumns = `repeat(${HEATMAP_COLS}, 1fr)`;
  grid.innerHTML = "";

  const map = {};
  seats.forEach(s => { map[`${s.row}-${s.col}`] = s; });

  for (let r = 0; r < HEATMAP_ROWS; r++) {
    for (let c = 0; c < HEATMAP_COLS; c++) {
      const s   = map[`${r}-${c}`];
      const div = document.createElement("div");
      div.className = "seat";

      if (s && s.active) {
        div.classList.add("active");
        div.style.background  = s.color;
        div.style.borderColor = s.color;
        div.textContent       = s.label;
        div.title             = `${s.label}: ${s.status}`;
      } else {
        div.classList.add("empty");
      }
      grid.appendChild(div);
    }
  }
}

// ── Timeline / Attention / Analytics chart ────────────────────
function drawTimelineChart(canvasId) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || timelineData.length < 2) return;

  // Size canvas to fill container
  const wrap = canvas.parentElement;
  canvas.width  = wrap.clientWidth || 400;
  canvas.height = 130;

  const ctx = canvas.getContext("2d");
  const W = canvas.width, H = canvas.height;
  const P = { t: 8, r: 8, b: 22, l: 30 };
  const cW = W - P.l - P.r, cH = H - P.t - P.b;

  ctx.clearRect(0, 0, W, H);

  // Grid lines
  ctx.strokeStyle = "rgba(0,200,255,0.07)";
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const y = P.t + (cH / 4) * i;
    ctx.beginPath(); ctx.moveTo(P.l, y); ctx.lineTo(P.l + cW, y); ctx.stroke();
    ctx.fillStyle = "rgba(160,185,210,0.3)";
    ctx.font = "9px 'DM Mono'"; ctx.textAlign = "right";
    ctx.fillText(`${100 - i * 25}`, P.l - 4, y + 4);
  }

  const tMin  = timelineData[0].t;
  const tMax  = timelineData[timelineData.length - 1].t || (tMin + 1);
  const tRange = tMax - tMin || 1;

  const pts = timelineData.map(d => ({
    x: P.l + ((d.t - tMin) / tRange) * cW,
    y: P.t + cH - (d.eng / 100) * cH,
  }));

  // Fill gradient
  const grad = ctx.createLinearGradient(0, P.t, 0, P.t + cH);
  grad.addColorStop(0,   "rgba(0,232,122,0.3)");
  grad.addColorStop(1,   "rgba(0,0,0,0)");
  ctx.beginPath();
  ctx.moveTo(pts[0].x, P.t + cH);
  pts.forEach(p => ctx.lineTo(p.x, p.y));
  ctx.lineTo(pts[pts.length-1].x, P.t + cH);
  ctx.closePath();
  ctx.fillStyle = grad; ctx.fill();

  // Line
  ctx.beginPath();
  ctx.strokeStyle = "var(--green, #00e87a)";
  ctx.lineWidth = 1.8;
  ctx.shadowBlur = 7; ctx.shadowColor = "#00e87a";
  pts.forEach((p, i) => i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y));
  ctx.stroke(); ctx.shadowBlur = 0;

  // X labels
  ctx.fillStyle = "rgba(160,185,210,0.3)";
  ctx.font = "9px 'DM Mono'"; ctx.textAlign = "center";
  ctx.fillText("0s", P.l, H - 3);
  ctx.fillText(`${Math.round(tRange)}s`, P.l + cW, H - 3);
}

// ── FPS module ────────────────────────────────────────────────
function updateFpsModule(data) {
  const fps = (data.fps || 0).toFixed(1);
  set("fps-big", fps);

  const canvas = document.getElementById("fps-spark");
  if (!canvas || fpsHistory.length < 2) return;

  const wrap = canvas.parentElement;
  canvas.width  = wrap.clientWidth || 400;
  canvas.height = 50;

  const ctx = canvas.getContext("2d");
  const W = canvas.width, H = canvas.height;
  const max = Math.max(...fpsHistory, 30);

  ctx.clearRect(0, 0, W, H);
  ctx.strokeStyle = "rgba(0,200,255,0.7)";
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  fpsHistory.forEach((v, i) => {
    const x = (i / (fpsHistory.length - 1)) * W;
    const y = H - (v / max) * H;
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  });
  ctx.stroke();
}

// ── Session stats module ──────────────────────────────────────
function updateSessionModule(data) {
  set("sess-time",   data.session_time  || "0m 0s");
  set("sess-peak",   `${Math.round(data.peak ?? 0)}%`);
  set("sess-low",    `${Math.round(data.low  ?? 0)}%`);
  set("sess-frames", data.total_frames  ?? 0);
}

// ── AI Suggestions module ─────────────────────────────────────
function updateSuggestionsModule(data) {
  const body = document.getElementById("suggestions-body");
  if (!body) return;
  const insights = data.insights || [];
  if (!insights.length) return;
  body.innerHTML = insights
    .map(txt => `<div class="insight-row">${esc(txt)}</div>`)
    .join("");
}

// ── Mood module ───────────────────────────────────────────────
function updateMoodModule(data) {
  const total = data.total || 1;
  const att   = ((data.attentive    ?? 0) / total * 100).toFixed(0);
  const dis   = ((data.distracted   ?? 0) / total * 100).toFixed(0);
  const look  = ((data.looking_away ?? 0) / total * 100).toFixed(0);
  const drowsy= ((data.drowsy       ?? 0) / total * 100).toFixed(0);

  setBar("mb-att",   att);
  setBar("mb-dis",   dis);
  setBar("mb-look",  look);
  setBar("mb-drowsy",drowsy);
}

function setBar(id, pct) {
  const bar = document.getElementById(id);
  if (bar) bar.style.width = `${pct}%`;
  const pctEl = document.getElementById(`${id}-p`);
  if (pctEl) pctEl.textContent = `${pct}%`;
}


// ══════════════════════════════════════════════════════════════
//  UTILITY
// ══════════════════════════════════════════════════════════════

function esc(s) {
  return String(s)
    .replace(/&/g,"&amp;")
    .replace(/</g,"&lt;")
    .replace(/>/g,"&gt;");
}

// Redraw charts on resize
window.addEventListener("resize", () => {
  if (!pinnedModule) return;
  if (["analytics","attention","timeline"].includes(pinnedModule))
    drawTimelineChart(pinnedModule === "timeline" ? "timeline-chart" : "attention-chart");
  if (pinnedModule === "fps") updateFpsModule(lastAnalytics);
});


// ══════════════════════════════════════════════════════════════
//  BOOT
// ══════════════════════════════════════════════════════════════

connectWS();
console.log("[AI Classroom Monitor] Dashboard v3.1 loaded.");