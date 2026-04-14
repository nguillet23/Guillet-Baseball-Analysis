"""
build_html.py
=============
Reads expected_2025_stats.csv (output of the main pipeline) and produces
a single self-contained HTML file — statcast_explorer.html — with all four
features baked in:

  1. Player lookup + MB simulator
  2. Annotated scrollytelling story
  3. Report cards (graded A–F)
  4. Rankings leaderboard

Usage
-----
    python build_html.py
    python build_html.py --csv my_file.csv --out my_output.html

The output file has zero external dependencies and opens in any browser.
"""

import argparse
import json
import sys
import pandas as pd

# ── Column config ─────────────────────────────────────────────────────────────
REQUIRED  = ["Name", "MB", "xMB", "TB", "xTB", "BB", "xBB",
             "AB", "xAB", "H", "xH", "SB", "xSB", "CS", "xCS"]
INT_COLS  = ["MB", "xMB", "TB", "xTB", "BB", "xBB",
             "AB", "xAB", "H",  "xH",  "SB", "xSB", "CS", "xCS"]
FALLBACKS = {"xTB":"TB","xBB":"BB","xAB":"AB","xH":"H","xSB":"SB","xCS":"CS"}


# ── Data loading ──────────────────────────────────────────────────────────────
def load_players(csv_path: str) -> list[dict]:
    df = pd.read_csv(csv_path)
    df = df.dropna(subset=["Name", "MB", "xMB"])

    for xcol, col in FALLBACKS.items():
        if xcol not in df.columns:
            df[xcol] = df.get(col, 0)
        else:
            df[xcol] = df[xcol].fillna(df.get(col, 0))

    for col in INT_COLS:
        if col in df.columns:
            df[col] = df[col].round(0).astype(int)

    cols    = [c for c in REQUIRED if c in df.columns]
    records = df[cols].dropna().to_dict(orient="records")

    # Sanitise: ensure Name is a plain string
    for r in records:
        r["Name"] = str(r["Name"]).strip()

    print(f"  Loaded {len(records)} players from {csv_path}", file=sys.stderr)
    return records


# ── HTML template ─────────────────────────────────────────────────────────────
# The template contains the marker  /*PLAYERS_DATA*/  which is replaced with
# the real JSON array at build time.

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Statcast xMB Explorer · 2025</title>
<style>
/* ── Google Fonts (embedded as @import so the file stays single-file) ── */
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg:      #0e1117;
  --surface: #161b25;
  --border:  #242c3d;
  --accent:  #3b82f6;
  --cyan:    #22d3ee;
  --over:    #f87171;
  --under:   #4ade80;
  --amber:   #fbbf24;
  --muted:   #64748b;
  --text:    #e2e8f0;
  --mono:    'DM Mono', monospace;
  --serif:   'Libre Baskerville', serif;
}

html { scroll-behavior: smooth; }
body { background: var(--bg); color: var(--text); font-family: var(--mono); min-height: 100vh; }

/* ── Top nav ── */
#top-nav {
  position: sticky; top: 0; z-index: 200;
  background: rgba(14,17,23,0.95);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--border);
  display: flex; align-items: center; gap: 6px;
  padding: 10px 1.5rem; flex-wrap: wrap;
}
#top-nav .brand { font-family: var(--serif); font-size: 1rem; color: #fff; margin-right: 1rem; white-space: nowrap; }
.tab-btn {
  padding: 6px 16px; border-radius: 20px;
  border: 1px solid var(--border);
  background: transparent; color: var(--muted);
  font-family: var(--mono); font-size: 0.8rem;
  cursor: pointer; transition: all 0.15s;
}
.tab-btn:hover  { background: var(--surface); color: var(--text); }
.tab-btn.active { background: var(--accent); border-color: var(--accent); color: #fff; }

/* ── Sections ── */
.section { display: none; padding: 2rem 1rem; max-width: 1100px; margin: 0 auto; }
.section.active { display: block; }

/* ══════════════════════════════════════════════════════════════
   SHARED COMPONENTS
══════════════════════════════════════════════════════════════ */
.page-title { font-family: var(--serif); font-size: 1.6rem; color: #fff; margin-bottom: 4px; }
.page-sub   { font-size: 0.78rem; color: var(--muted); margin-bottom: 1.5rem; }

.search-wrap { position: relative; margin-bottom: 1.5rem; }
.search-wrap input {
  width: 100%; padding: 11px 16px 11px 42px;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 8px; font-family: var(--mono); font-size: 0.88rem;
  color: var(--text); outline: none; transition: border-color 0.2s;
}
.search-wrap input:focus { border-color: var(--accent); }
.search-wrap input::placeholder { color: var(--muted); }
.search-icon { position: absolute; left: 14px; top: 50%; transform: translateY(-50%); color: var(--muted); pointer-events: none; }
.dropdown {
  position: absolute; top: calc(100% + 4px); left: 0; right: 0;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 8px; overflow: hidden; z-index: 50; display: none;
  max-height: 260px; overflow-y: auto;
}
.dropdown.open { display: block; }
.dd-item { padding: 10px 16px; font-size: 0.85rem; cursor: pointer; color: var(--text); transition: background 0.1s; }
.dd-item:hover { background: var(--border); }

.toolbar {
  display: flex; gap: 10px; flex-wrap: wrap;
  align-items: center; margin-bottom: 1.25rem;
}
.toolbar select, .toolbar input[type=text] {
  padding: 8px 12px; background: var(--surface);
  border: 1px solid var(--border); border-radius: 6px;
  font-family: var(--mono); font-size: 0.82rem;
  color: var(--text); outline: none; cursor: pointer;
}
.toolbar select:focus, .toolbar input[type=text]:focus { border-color: var(--accent); }
.toolbar label { font-size: 0.75rem; color: var(--muted); }
.result-count { font-size: 0.72rem; color: var(--muted); margin-left: auto; }

/* ══════════════════════════════════════════════════════════════
   TAB 1 — PLAYER LOOKUP
══════════════════════════════════════════════════════════════ */
.player-card {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 12px; overflow: hidden; animation: fadeUp 0.3s ease;
}
@keyframes fadeUp { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:translateY(0); } }
.card-header {
  display: flex; align-items: center; gap: 1rem;
  padding: 1.25rem 1.5rem; border-bottom: 1px solid var(--border);
  background: linear-gradient(135deg,#161b25,#1a2235);
}
.avatar {
  width: 50px; height: 50px; border-radius: 50%;
  background: #1e3a5f; border: 2px solid var(--accent);
  display: flex; align-items: center; justify-content: center;
  font-family: var(--serif); font-size: 1rem; font-weight: 700;
  color: var(--cyan); flex-shrink: 0;
}
.player-name { font-family: var(--serif); font-size: 1.25rem; color: #fff; }
.player-meta { font-size: 0.72rem; color: var(--muted); margin-top: 3px; }

.stats-grid { display: grid; grid-template-columns: repeat(3,1fr); gap: 1px; background: var(--border); }
.stat-block { background: var(--surface); padding: 1rem 1.25rem; }
.stat-label { font-size: 0.68rem; letter-spacing: 0.1em; text-transform: uppercase; color: var(--muted); margin-bottom: 6px; }
.stat-values { display: flex; align-items: baseline; gap: 8px; margin-bottom: 8px; }
.stat-actual { font-size: 1.5rem; font-weight: 500; color: #fff; line-height: 1; }
.stat-pred   { font-size: 0.82rem; color: var(--cyan); }
.bar-wrap    { display: flex; flex-direction: column; gap: 3px; }
.bar-row     { display: flex; align-items: center; gap: 6px; }
.bar-track   { flex: 1; height: 4px; background: var(--border); border-radius: 2px; overflow: hidden; }
.bar-fill    { height: 100%; border-radius: 2px; transition: width 0.5s cubic-bezier(.4,0,.2,1); }
.bar-key     { font-size: 0.62rem; width: 12px; }
.badge       { display: inline-block; font-size: 0.65rem; padding: 2px 7px; border-radius: 4px; font-weight: 500; margin-top: 5px; }
.badge-over  { background:rgba(248,113,113,.15); color:var(--over);  border:1px solid rgba(248,113,113,.3); }
.badge-under { background:rgba(74,222,128,.15);  color:var(--under); border:1px solid rgba(74,222,128,.3); }
.badge-on    { background:rgba(59,130,246,.15);  color:var(--accent);border:1px solid rgba(59,130,246,.3); }

.mb-row {
  display: flex; align-items: center; justify-content: space-between;
  padding: 1.25rem 1.5rem; border-top: 1px solid var(--border);
  background: #0b1118;
}
.mb-block  { text-align: center; }
.mb-lbl    { font-size: 0.65rem; letter-spacing: 0.08em; color: var(--muted); margin-bottom: 4px; }
.mb-val    { font-family: var(--serif); font-size: 2rem; font-weight: 700; }
.mb-err    { font-size: 0.78rem; font-weight: 500; padding: 4px 10px; border-radius: 6px; }

/* Simulator */
.sim-panel {
  background: #090d14; border: 1px solid var(--border);
  border-radius: 10px; padding: 1.5rem; margin-top: 1.25rem;
}
.sim-title { font-family: var(--serif); font-size: 0.95rem; color: var(--cyan); margin-bottom: 1rem; display: flex; align-items: center; gap: 8px; }
.sim-title::before { content:''; display:block; width:8px; height:8px; border-radius:50%; background:var(--cyan); box-shadow:0 0 6px var(--cyan); }
.sim-grid  { display: grid; grid-template-columns: repeat(2,1fr); gap: 1rem; }
.sim-row   { display: flex; flex-direction: column; gap: 4px; }
.sim-lbl   { font-size: 0.7rem; color: var(--muted); letter-spacing: 0.06em; }
.sim-ctrl  { display: flex; align-items: center; gap: 10px; }
.sim-ctrl input[type=range] { flex: 1; accent-color: var(--accent); }
.sim-out   { font-size: 0.85rem; font-weight: 500; min-width: 36px; text-align: right; color: var(--cyan); }
.sim-result { margin-top: 1.25rem; padding-top: 1.25rem; border-top: 1px solid var(--border); display: flex; align-items: center; gap: 1rem; }
.sim-mb-lbl { font-size: 0.72rem; color: var(--muted); }
.sim-mb-val { font-family: var(--serif); font-size: 1.8rem; font-weight: 700; color: var(--cyan); }
.sim-formula { font-size: 0.7rem; color: var(--muted); line-height: 1.8; flex: 1; }

.empty-state { text-align: center; padding: 4rem 2rem; color: var(--muted); font-size: 0.85rem; border: 1px dashed var(--border); border-radius: 10px; }

/* ══════════════════════════════════════════════════════════════
   TAB 2 — STORY
══════════════════════════════════════════════════════════════ */
#progress-bar { position: fixed; top: 0; left: 0; height: 3px; width: 0; background: linear-gradient(90deg,var(--accent),var(--cyan)); z-index: 300; transition: width 0.1s linear; }

.story-block { max-width: 760px; margin: 0 auto 4rem; }
.story-tag   { font-size: 0.65rem; letter-spacing: 0.15em; color: var(--cyan); text-transform: uppercase; margin-bottom: 0.75rem; }
.story-h     { font-family: var(--serif); font-size: clamp(1.3rem,3vw,1.9rem); color: #fff; line-height: 1.25; margin-bottom: 0.9rem; }
.story-body  { font-size: 0.875rem; color: var(--muted); line-height: 1.9; margin-bottom: 1.5rem; }
.story-body strong { color: var(--text); font-weight: 500; }

.kpi-strip   { display: grid; grid-template-columns: repeat(3,1fr); gap: 10px; margin-bottom: 1.5rem; }
.kpi-card    { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 0.9rem 1rem; }
.kpi-lbl     { font-size: 0.62rem; letter-spacing: 0.1em; color: var(--muted); margin-bottom: 4px; }
.kpi-val     { font-family: var(--serif); font-size: 1.5rem; font-weight: 700; }

.formula-box { background: var(--surface); border: 1px solid var(--border); border-left: 3px solid var(--cyan); border-radius: 8px; padding: 1.25rem 1.5rem; font-size: 0.82rem; line-height: 2; }
.formula-line { font-family: var(--mono); color: var(--cyan); font-size: 0.92rem; }

.r2-chart    { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 1.5rem; }
.r2-row      { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.r2-row:last-child { margin-bottom: 0; }
.r2-stat     { width: 36px; font-size: 0.8rem; font-weight: 500; }
.r2-track    { flex: 1; height: 28px; background: var(--border); border-radius: 4px; overflow: hidden; }
.r2-fill     { height: 100%; border-radius: 4px; display: flex; align-items: center; padding-left: 10px; font-size: 0.75rem; font-weight: 500; color: #fff; transition: width 1.2s cubic-bezier(.4,0,.2,1); }
.r2-quality  { width: 70px; font-size: 0.7rem; color: var(--muted); text-align: right; }

.scatter-wrap { position: relative; background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 1.25rem; }
.scatter-canvas { width: 100%; display: block; }
.callout { position: absolute; background: var(--bg); border: 1px solid var(--border); border-radius: 6px; padding: 7px 11px; font-size: 0.7rem; line-height: 1.5; max-width: 150px; pointer-events: none; opacity: 0; transition: opacity 0.2s; }
.callout.show { opacity: 1; }
.callout-name  { color: #fff; font-weight: 500; }
.callout-stats { color: var(--muted); }

.comp-table  { width: 100%; border-collapse: collapse; font-size: 0.8rem; }
.comp-table th { text-align: left; padding: 8px 12px; color: var(--muted); font-weight: 400; border-bottom: 1px solid var(--border); font-size: 0.68rem; letter-spacing: 0.06em; }
.comp-table td { padding: 10px 12px; border-bottom: 1px solid rgba(36,44,61,0.5); }
.comp-table tr:last-child td { border-bottom: none; }
.pass { color: var(--under); } .fail { color: var(--over); }

.outlier-strip { display: flex; flex-direction: column; gap: 8px; background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 1.5rem; }
.outlier-row   { display: flex; align-items: center; gap: 10px; }
.outlier-name  { width: 160px; font-size: 0.78rem; color: var(--text); overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.outlier-track { flex: 1; height: 18px; background: var(--border); border-radius: 4px; overflow: hidden; }
.outlier-fill  { height: 100%; border-radius: 4px; }
.outlier-val   { width: 56px; font-size: 0.72rem; font-weight: 500; text-align: right; }

/* ══════════════════════════════════════════════════════════════
   TAB 3 — REPORT CARDS
══════════════════════════════════════════════════════════════ */
.grade-filter { display: flex; gap: 6px; flex-wrap: wrap; }
.grade-btn    { padding: 6px 14px; border-radius: 4px; font-family: var(--mono); font-size: 0.78rem; font-weight: 500; cursor: pointer; border: 1px solid; transition: opacity 0.15s; opacity: 0.45; }
.grade-btn.active { opacity: 1; }

.cards-grid { display: grid; grid-template-columns: repeat(auto-fill,minmax(290px,1fr)); gap: 12px; }
.report-card {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 12px; overflow: hidden;
  transition: transform 0.2s, border-color 0.2s; cursor: pointer;
}
.report-card:hover { transform: translateY(-3px); border-color: var(--accent); }
.card-band  { height: 4px; }
.card-top   { display: flex; align-items: center; justify-content: space-between; padding: 1rem 1.25rem 0.75rem; border-bottom: 1px solid var(--border); }
.card-ident { display: flex; align-items: center; gap: 10px; }
.card-name  { font-family: var(--serif); font-size: 0.95rem; color: #fff; }
.card-sea   { font-size: 0.68rem; color: var(--muted); margin-top: 2px; }
.grade-circle { width: 42px; height: 42px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-family: var(--serif); font-size: 1.3rem; font-weight: 700; border: 2px solid; }
.card-stats { padding: 0.85rem 1.25rem; }
.cstat-row  { display: flex; align-items: center; justify-content: space-between; margin-bottom: 7px; }
.cstat-row:last-child { margin-bottom: 0; }
.cstat-key  { font-size: 0.7rem; color: var(--muted); width: 88px; }
.cstat-bar  { flex: 1; margin: 0 10px; }
.cstat-track { height: 3px; background: var(--border); border-radius: 2px; position: relative; }
.cbar-a     { position: absolute; top:0; left:0; height:100%; border-radius:2px; background:var(--accent); opacity:0.6; }
.cbar-p     { position: absolute; top:0; left:0; height:3px; border-radius:2px; background:var(--cyan); opacity:0.9; margin-top:-3px; }
.cstat-vals { display: flex; gap: 5px; font-size: 0.7rem; white-space: nowrap; }
.cstat-a    { color: var(--text); font-weight: 500; }
.cstat-p    { color: var(--cyan); }
.card-foot  { display: flex; align-items: center; justify-content: space-between; padding: 0.75rem 1.25rem; border-top: 1px solid var(--border); background: rgba(0,0,0,.25); }
.cf-mb-a    { font-family: var(--serif); font-size: 1.4rem; font-weight: 700; color: #fff; }
.cf-mb-p    { font-family: var(--serif); font-size: 1.4rem; font-weight: 700; color: var(--cyan); }
.cf-err     { font-size: 0.73rem; font-weight: 500; padding: 3px 9px; border-radius: 4px; }
.cf-lbl     { font-size: 0.6rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.07em; }

/* ══════════════════════════════════════════════════════════════
   TAB 4 — RANKINGS
══════════════════════════════════════════════════════════════ */
.summary-strip { display: grid; grid-template-columns: repeat(4,1fr); gap: 10px; margin-bottom: 1.5rem; }
.skpi         { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 0.9rem 1rem; }
.skpi-lbl     { font-size: 0.62rem; letter-spacing: 0.1em; color: var(--muted); margin-bottom: 4px; }
.skpi-val     { font-family: var(--serif); font-size: 1.5rem; font-weight: 700; }

.table-wrap { overflow-x: auto; }
table       { width: 100%; border-collapse: collapse; font-size: 0.82rem; min-width: 720px; }
thead th    { padding: 9px 12px; text-align: left; color: var(--muted); font-size: 0.68rem; font-weight: 400; letter-spacing: 0.08em; text-transform: uppercase; border-bottom: 1px solid var(--border); white-space: nowrap; user-select: none; }
thead th.sortable { cursor: pointer; }
thead th.sortable:hover { color: var(--accent); }
thead th.sort-active    { color: var(--cyan); }
tbody tr { border-bottom: 1px solid rgba(36,44,61,.6); transition: background 0.1s; }
tbody tr:hover { background: rgba(59,130,246,.04); }
tbody td { padding: 9px 12px; color: var(--text); vertical-align: middle; }
.rank-c  { color: var(--muted); font-weight: 500; width: 36px; }
.name-c  { color: #fff; font-weight: 500; cursor: pointer; transition: color 0.15s; }
.name-c:hover { color: var(--cyan); }
.pred-c  { color: var(--muted); }
.acc-c   { color: var(--cyan); font-weight: 500; }
.mb-bar-cell { display: flex; align-items: center; gap: 6px; }
.mb-bar-track { flex: 1; height: 4px; background: var(--border); border-radius: 2px; min-width: 60px; }
.mb-bar-fill  { height: 100%; border-radius: 2px; background: var(--accent); }
.err-pill { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.72rem; font-weight: 500; }
.gbadge   { display: inline-flex; align-items: center; justify-content: center; width: 22px; height: 22px; border-radius: 50%; font-family: var(--serif); font-size: 0.75rem; font-weight: 700; border: 1px solid; }

.pagination { display: flex; align-items: center; gap: 8px; margin-top: 1.25rem; justify-content: center; flex-wrap: wrap; }
.pg-btn { padding: 6px 14px; background: var(--surface); border: 1px solid var(--border); border-radius: 5px; font-family: var(--mono); font-size: 0.8rem; color: var(--text); cursor: pointer; transition: all 0.15s; }
.pg-btn:hover:not([disabled]) { border-color: var(--accent); color: var(--accent); }
.pg-btn.pg-active { background: var(--accent); border-color: var(--accent); color: #fff; }
.pg-btn[disabled] { opacity: 0.3; cursor: not-allowed; }
.pg-info { font-size: 0.72rem; color: var(--muted); }

/* ── Responsive ── */
@media (max-width: 640px) {
  .stats-grid    { grid-template-columns: repeat(2,1fr); }
  .sim-grid      { grid-template-columns: 1fr; }
  .summary-strip { grid-template-columns: repeat(2,1fr); }
  .kpi-strip     { grid-template-columns: repeat(2,1fr); }
}
</style>
</head>
<body>

<div id="progress-bar"></div>

<!-- ── Navigation ── -->
<nav id="top-nav">
  <span class="brand">Statcast xMB · 2025</span>
  <button class="tab-btn active" onclick="showTab('lookup')">Player lookup</button>
  <button class="tab-btn"        onclick="showTab('story')">Story</button>
  <button class="tab-btn"        onclick="showTab('cards')">Report cards</button>
  <button class="tab-btn"        onclick="showTab('rankings')">Rankings</button>
</nav>

<!-- ══════════════ TAB 1 — LOOKUP ══════════════ -->
<div id="tab-lookup" class="section active">
  <h1 class="page-title">Player lookup</h1>
  <p class="page-sub">Search any 2025 batter to compare actual vs. expected stats. Use the simulator to recalculate MB with custom inputs.</p>
  <div class="search-wrap">
    <span class="search-icon">⌕</span>
    <input type="text" id="lu-search" placeholder="Search player name…" autocomplete="off"
      oninput="luSearch()" onfocus="luOpen()" onblur="setTimeout(luClose,200)">
    <div class="dropdown" id="lu-drop"></div>
  </div>
  <div id="lu-display"><div class="empty-state">⚾<br><br>Type a player name above to begin</div></div>
</div>

<!-- ══════════════ TAB 2 — STORY ══════════════ -->
<div id="tab-story" class="section">

  <div class="story-block">
    <div class="story-tag">Chapter 1 — The setup</div>
    <h2 class="story-h">Training on history, predicting the future</h2>
    <p class="story-body">
      Models were trained on <strong>six seasons of Statcast data (2019–2024)</strong> — exit
      velocity, barrel rate, sprint speed, swing metrics — then applied to 2025 batters who were
      <em>never seen during training</em>. The central question: can raw contact quality reliably
      predict counting stats a full year out?
    </p>
    <div class="kpi-strip">
      <div class="kpi-card"><div class="kpi-lbl">TRAINING SEASONS</div><div class="kpi-val" style="color:var(--accent)">6</div></div>
      <div class="kpi-card"><div class="kpi-lbl">COMPONENT STATS</div><div class="kpi-val" style="color:var(--cyan)">6</div></div>
      <div class="kpi-card"><div class="kpi-lbl">MODEL TYPES</div><div class="kpi-val" style="color:var(--amber)">4</div></div>
    </div>
    <div class="formula-box">
      The Measurable Batting (MB) formula:<br>
      <span class="formula-line">MB = ((H + BB − CS) × (TB + 0.7 × SB)) / (AB + BB + CS)</span><br>
      xMB substitutes expected values wherever model R² ≥ 0.50.
    </div>
  </div>

  <div class="story-block">
    <div class="story-tag">Chapter 2 — Model performance</div>
    <h2 class="story-h">Which stats could the model actually predict?</h2>
    <p class="story-body">
      <strong>AB and H</strong> were most predictable — playing-time and contact profiles are
      stable year-over-year. <strong>SB and CS</strong> were harder; stolen-base decisions depend
      on game situation and manager preference as much as raw speed.
    </p>
    <div class="r2-chart" id="r2-chart"></div>
  </div>

  <div class="story-block">
    <div class="story-tag">Chapter 3 — xMB construction</div>
    <h2 class="story-h">Which components earned a spot in xMB?</h2>
    <p class="story-body">
      Each component passes or fails a <strong>R² ≥ 0.50 threshold</strong>. Failures fall back
      to the real observed stat — preventing a weak model from corrupting the final xMB.
    </p>
    <div style="background:var(--surface);border:1px solid var(--border);border-radius:10px;overflow:hidden;">
      <table class="comp-table"><thead><tr>
        <th>Component</th><th>Training R²</th><th>Threshold</th><th>Result</th><th>Used in xMB as</th>
      </tr></thead><tbody id="comp-tbody"></tbody></table>
    </div>
  </div>

  <div class="story-block">
    <div class="story-tag">Chapter 4 — The big picture</div>
    <h2 class="story-h">Predicted vs actual MB — 2025</h2>
    <p class="story-body">
      Each dot is a player. The dashed line is perfect prediction.
      <strong style="color:var(--over)">Coral dots</strong> were over-predicted;
      <strong style="color:var(--under)">green dots</strong> out-performed their Statcast profile.
      Hover to identify players.
    </p>
    <div class="scatter-wrap">
      <canvas class="scatter-canvas" id="scatter-canvas" height="360"></canvas>
      <div class="callout" id="callout">
        <div class="callout-name" id="c-name"></div>
        <div class="callout-stats" id="c-stats"></div>
      </div>
    </div>
  </div>

  <div class="story-block">
    <div class="story-tag">Chapter 5 — Outliers</div>
    <h2 class="story-h">Who beat — and missed — their Statcast profile?</h2>
    <p class="story-body">
      The largest xMB prediction errors in 2025.
      <strong style="color:var(--over)">Coral</strong> = over-predicted.
      <strong style="color:var(--under)">Green</strong> = under-predicted.
    </p>
    <div class="outlier-strip" id="outlier-strip"></div>
  </div>

</div>

<!-- ══════════════ TAB 3 — CARDS ══════════════ -->
<div id="tab-cards" class="section">
  <h1 class="page-title">Report cards</h1>
  <p class="page-sub">Each card is graded A–F by how accurately xMB tracked MB. Click any card to open the full player lookup.</p>
  <div class="toolbar">
    <input type="text" id="rc-search" placeholder="Filter by name…" oninput="rcRender()" style="width:200px;">
    <select id="rc-sort" onchange="rcRender()">
      <option value="name">Sort: name</option>
      <option value="mb-desc">Sort: MB high→low</option>
      <option value="err-desc">Sort: biggest error first</option>
      <option value="grade">Sort: grade A→F</option>
    </select>
    <div class="grade-filter" id="grade-filter"></div>
    <span class="result-count" id="rc-count"></span>
  </div>
  <div class="cards-grid" id="cards-grid"></div>
</div>

<!-- ══════════════ TAB 4 — RANKINGS ══════════════ -->
<div id="tab-rankings" class="section">
  <h1 class="page-title">Rankings &amp; leaderboard</h1>
  <p class="page-sub">Sort by any column. Filter to over/under-predicted players or by grade.</p>
  <div class="summary-strip" id="summary-strip"></div>
  <div class="toolbar">
    <input type="text" id="lb-search" placeholder="Filter name…" oninput="lbRender()" style="width:180px;">
    <label>Show:</label>
    <select id="lb-show" onchange="lbRender()">
      <option value="all">All players</option>
      <option value="over">Over-predicted</option>
      <option value="under">Under-predicted</option>
      <option value="a">Grade A only</option>
      <option value="b">Grade B only</option>
      <option value="cf">Grade C or worse</option>
    </select>
    <label>Per page:</label>
    <select id="lb-pp" onchange="lbGoPage(1)">
      <option value="20" selected>20</option>
      <option value="50">50</option>
      <option value="100">100</option>
    </select>
    <span class="result-count" id="lb-count"></span>
  </div>
  <div class="table-wrap">
    <table><thead id="lb-thead"></thead><tbody id="lb-tbody"></tbody></table>
  </div>
  <div class="pagination" id="lb-pagination"></div>
</div>

<script>
/* ============================================================
   DATA — injected by build_html.py
   ============================================================ */
const PLAYERS_RAW = /*PLAYERS_DATA*/;

/* ── Enrich with computed fields ── */
const PLAYERS = PLAYERS_RAW.map(p => ({
  ...p,
  pe: p.MB !== 0 ? +((( p.xMB - p.MB) / Math.abs(p.MB)) * 100).toFixed(1) : 0,
}));
PLAYERS.forEach(p => {
  const a = Math.abs(p.pe);
  p.grade = a <= 3 ? 'A' : a <= 7 ? 'B' : a <= 12 ? 'C' : a <= 20 ? 'D' : 'F';
});

const MODEL_R2  = {TB:0.84, BB:0.81, AB:0.91, H:0.87, SB:0.62, CS:0.55};
const THRESHOLD = 0.50;
const maxMB     = Math.max(...PLAYERS.map(p => p.MB));

const GRADE_CFG = {
  A:{ color:'#4ade80', bg:'rgba(74,222,128,.12)',   border:'rgba(74,222,128,.4)'   },
  B:{ color:'#3b82f6', bg:'rgba(59,130,246,.12)',   border:'rgba(59,130,246,.4)'   },
  C:{ color:'#fbbf24', bg:'rgba(251,191,36,.12)',   border:'rgba(251,191,36,.4)'   },
  D:{ color:'#f97316', bg:'rgba(249,115,22,.12)',   border:'rgba(249,115,22,.4)'   },
  F:{ color:'#f87171', bg:'rgba(248,113,113,.12)',  border:'rgba(248,113,113,.4)'  },
};

/* ============================================================
   TAB SWITCHING
   ============================================================ */
function showTab(name) {
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  event.currentTarget.classList.add('active');
  if (name === 'story')    initStory();
  if (name === 'cards')    rcInit();
  if (name === 'rankings') lbRender();
}

/* ============================================================
   HELPERS
   ============================================================ */
function initials(name) { return name.split(' ').map(w=>w[0]).join('').slice(0,2).toUpperCase(); }

function badgeHtml(pe) {
  const a = Math.abs(pe);
  if (a <= 5)  return `<span class="badge badge-on">on track (${pe>0?'+':''}${pe}%)</span>`;
  if (pe >  5) return `<span class="badge badge-over">+${pe}% over-predicted</span>`;
  return             `<span class="badge badge-under">${pe}% under-predicted</span>`;
}

function errStyle(pe) {
  return pe > 5 ? '#f87171' : pe < -5 ? '#4ade80' : '#3b82f6';
}

/* ============================================================
   TAB 1 — LOOKUP
   ============================================================ */
function luSearch() {
  const q = document.getElementById('lu-search').value.toLowerCase().trim();
  const drop = document.getElementById('lu-drop');
  if (!q) { drop.innerHTML=''; drop.classList.remove('open'); return; }
  const hits = PLAYERS.filter(p => p.Name.toLowerCase().includes(q)).slice(0, 10);
  drop.innerHTML = hits.map(p =>
    `<div class="dd-item" onmousedown="luSelect('${p.Name.replace(/'/g,"\\'")}')">
       ${p.Name}
       <span style="color:var(--muted);font-size:0.72rem;margin-left:8px;">MB ${p.MB}</span>
     </div>`
  ).join('');
  drop.classList.toggle('open', hits.length > 0);
}
function luOpen()  { if (document.getElementById('lu-search').value) luSearch(); }
function luClose() { document.getElementById('lu-drop').classList.remove('open'); }

function luSelect(name) {
  const p = PLAYERS.find(x => x.Name === name);
  document.getElementById('lu-search').value = name;
  luClose();
  luRenderCard(p);
}

function luRenderCard(p) {
  const STATS = [
    {label:'Total Bases (TB)', actual:p.TB, pred:p.xTB},
    {label:'Walks (BB)',        actual:p.BB, pred:p.xBB},
    {label:'Hits (H)',          actual:p.H,  pred:p.xH },
    {label:'Stolen Bases (SB)', actual:p.SB, pred:p.xSB},
    {label:'Caught Stealing',   actual:p.CS, pred:p.xCS},
    {label:'At Bats (AB)',      actual:p.AB, pred:p.xAB},
  ];

  const blocksHtml = STATS.map(s => {
    const pe = s.actual !== 0 ? +((( s.pred-s.actual)/Math.abs(s.actual))*100).toFixed(1) : 0;
    const cap = Math.max(s.actual, s.pred, 1);
    const wa  = Math.round((s.actual/cap)*100);
    const wp  = Math.round((s.pred  /cap)*100);
    return `<div class="stat-block">
      <div class="stat-label">${s.label}</div>
      <div class="stat-values">
        <span class="stat-actual">${s.actual}</span>
        <span style="color:var(--muted);font-size:.8rem">→</span>
        <span class="stat-pred">x: ${s.pred}</span>
      </div>
      <div class="bar-wrap">
        <div class="bar-row"><span class="bar-key" style="color:var(--accent)">A</span>
          <div class="bar-track"><div class="bar-fill" style="width:${wa}%;background:var(--accent)"></div></div></div>
        <div class="bar-row"><span class="bar-key" style="color:var(--cyan)">X</span>
          <div class="bar-track"><div class="bar-fill" style="width:${wp}%;background:var(--cyan)"></div></div></div>
      </div>
      ${badgeHtml(pe)}
    </div>`;
  }).join('');

  const ec = errStyle(p.pe);
  const SIM_DEFS = [
    {id:'sh',  label:'Hits (H)',         min:30,  max:230, val:p.H },
    {id:'sbb', label:'Walks (BB)',        min:5,   max:140, val:p.BB},
    {id:'scs', label:'Caught Stealing',   min:0,   max:25,  val:p.CS},
    {id:'stb', label:'Total Bases (TB)',  min:50,  max:400, val:p.TB},
    {id:'ssb', label:'Stolen Bases (SB)', min:0,   max:80,  val:p.SB},
    {id:'sab', label:'At Bats (AB)',      min:50,  max:700, val:p.AB},
  ];

  document.getElementById('lu-display').innerHTML = `
    <div class="player-card">
      <div class="card-header">
        <div class="avatar">${initials(p.Name)}</div>
        <div>
          <div class="player-name">${p.Name}</div>
          <div class="player-meta">2025 season · model trained 2019–2024</div>
        </div>
      </div>
      <div class="stats-grid">${blocksHtml}</div>
      <div class="mb-row">
        <div class="mb-block"><div class="mb-lbl">ACTUAL MB</div><div class="mb-val" style="color:#fff">${p.MB}</div></div>
        <div style="color:var(--border);font-size:1.4rem">|</div>
        <div class="mb-block"><div class="mb-lbl">xMB (predicted)</div><div class="mb-val" style="color:var(--cyan)">${p.xMB}</div></div>
        <div class="mb-block">
          <div class="mb-lbl">ERROR</div>
          <div class="mb-err" style="color:${ec};border:1px solid ${ec}22;background:${ec}18">
            ${p.pe>0?'+':''}${p.pe}%
          </div>
        </div>
      </div>
    </div>
    <div class="sim-panel">
      <div class="sim-title">xMB simulator — drag to recalculate</div>
      <div class="sim-grid">
        ${SIM_DEFS.map(s=>`
          <div class="sim-row">
            <div class="sim-lbl">${s.label}</div>
            <div class="sim-ctrl">
              <input type="range" id="${s.id}" min="${s.min}" max="${s.max}" value="${s.val}" step="1" oninput="simCalc()">
              <span class="sim-out" id="${s.id}out">${s.val}</span>
            </div>
          </div>`).join('')}
      </div>
      <div class="sim-result">
        <div><div class="sim-mb-lbl">SIMULATED MB</div><div class="sim-mb-val" id="sim-val">—</div></div>
        <div class="sim-formula" id="sim-formula"></div>
      </div>
    </div>`;
  simCalc();
}

function simCalc() {
  const g = id => { const el=document.getElementById(id); if(!el) return 0; const v=+el.value; document.getElementById(id+'out').textContent=v; return v; };
  const H=g('sh'),BB=g('sbb'),CS=g('scs'),TB=g('stb'),SB=g('ssb'),AB=g('sab');
  const d = AB+BB+CS;
  const mb = d>0 ? +( ((H+BB-CS)*(TB+0.7*SB))/d ).toFixed(2) : 0;
  const el=document.getElementById('sim-val'), ft=document.getElementById('sim-formula');
  if(el) el.textContent = mb.toFixed(1);
  if(ft) ft.innerHTML =
    `MB = ((H + BB − CS) × (TB + 0.7×SB)) / (AB + BB + CS)<br>` +
    `= ((${H} + ${BB} − ${CS}) × (${TB} + 0.7×${SB})) / (${AB} + ${BB} + ${CS})<br>` +
    `= <strong style="color:var(--cyan)">${mb.toFixed(2)}</strong>`;
}

/* ============================================================
   TAB 2 — STORY
   ============================================================ */
let storyBuilt = false;
function initStory() {
  if (storyBuilt) return;
  storyBuilt = true;
  buildR2Chart();
  buildCompTable();
  buildScatter();
  buildOutliers();
}

function r2Color(r2) {
  return r2>=0.85?'#4ade80': r2>=0.70?'#3b82f6': r2>=0.55?'#fbbf24':'#f87171';
}
function r2Quality(r2) {
  return r2>=0.85?'excellent': r2>=0.70?'good': r2>=0.55?'moderate':'weak';
}

function buildR2Chart() {
  const el = document.getElementById('r2-chart');
  el.innerHTML = Object.entries(MODEL_R2).map(([s,r2]) =>
    `<div class="r2-row">
      <span class="r2-stat">${s}</span>
      <div class="r2-track">
        <div class="r2-fill" id="r2f-${s}" style="width:0%;background:${r2Color(r2)}">R² ${r2.toFixed(2)}</div>
      </div>
      <span class="r2-quality">${r2Quality(r2)}</span>
    </div>`
  ).join('');
  requestAnimationFrame(() => {
    Object.entries(MODEL_R2).forEach(([s,r2]) => {
      const el = document.getElementById('r2f-'+s);
      if (el) el.style.width = Math.round(r2*100)+'%';
    });
  });
}

function buildCompTable() {
  document.getElementById('comp-tbody').innerHTML =
    Object.entries(MODEL_R2).map(([s,r2]) => {
      const pass = r2 >= THRESHOLD;
      return `<tr>
        <td style="color:#fff;font-weight:500">${s}</td>
        <td>${r2.toFixed(4)}</td><td>≥ ${THRESHOLD}</td>
        <td class="${pass?'pass':'fail'}">${pass?'✓ pass':'✗ fail'}</td>
        <td style="color:${pass?'var(--cyan)':'var(--muted)'}">${pass?'x'+s+' (expected)':s+' (observed)'}</td>
      </tr>`;
    }).join('');
}

function buildScatter() {
  const canvas  = document.getElementById('scatter-canvas');
  const callout = document.getElementById('callout');
  const PAD = 50;

  function draw() {
    const W = canvas.parentElement.clientWidth - 40;
    const H = 360;
    canvas.width  = W * devicePixelRatio;
    canvas.height = H * devicePixelRatio;
    canvas.style.width  = W+'px';
    canvas.style.height = H+'px';
    const ctx = canvas.getContext('2d');
    ctx.scale(devicePixelRatio, devicePixelRatio);

    const vals = PLAYERS.flatMap(p => [p.xMB, p.MB]);
    const vmin = Math.min(...vals)-3, vmax = Math.max(...vals)+3;
    const toX = v => PAD + (v-vmin)/(vmax-vmin)*(W-PAD*2);
    const toY = v => H-PAD - (v-vmin)/(vmax-vmin)*(H-PAD*2);

    // Grid
    ctx.strokeStyle='#242c3d'; ctx.lineWidth=1;
    for(let v=Math.ceil(vmin);v<=vmax;v+=5){
      ctx.beginPath(); ctx.moveTo(toX(v),PAD); ctx.lineTo(toX(v),H-PAD); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(PAD,toY(v)); ctx.lineTo(W-PAD,toY(v)); ctx.stroke();
    }
    // Perfect line
    ctx.strokeStyle='#3b4a5e'; ctx.setLineDash([6,4]); ctx.lineWidth=1.5;
    ctx.beginPath(); ctx.moveTo(toX(vmin),toY(vmin)); ctx.lineTo(toX(vmax),toY(vmax)); ctx.stroke();
    ctx.setLineDash([]);
    // Axis labels
    ctx.fillStyle='#64748b'; ctx.font=`11px 'DM Mono', monospace`;
    ctx.textAlign='center'; ctx.fillText('xMB (predicted)', W/2, H-6);
    ctx.save(); ctx.translate(14,H/2); ctx.rotate(-Math.PI/2); ctx.fillText('MB (actual)',0,0); ctx.restore();
    // Dots
    PLAYERS.forEach(p => {
      ctx.beginPath();
      ctx.arc(toX(p.xMB), toY(p.MB), 4.5, 0, Math.PI*2);
      ctx.fillStyle = p.pe>5?'#f87171': p.pe<-5?'#4ade80':'#3b82f6';
      ctx.globalAlpha = 0.75; ctx.fill(); ctx.globalAlpha=1;
    });
    canvas._meta = { toX, toY };
  }
  draw();
  window.addEventListener('resize', draw);

  canvas.addEventListener('mousemove', e => {
    const rect = canvas.getBoundingClientRect();
    const mx=e.clientX-rect.left, my=e.clientY-rect.top;
    const {toX,toY} = canvas._meta||{};
    if(!toX) return;
    let nearest=null, minD=18;
    PLAYERS.forEach(p=>{
      const d=Math.hypot(toX(p.xMB)-mx, toY(p.MB)-my);
      if(d<minD){minD=d;nearest=p;}
    });
    if(nearest){
      callout.style.left=(mx+14)+'px'; callout.style.top=(my-30)+'px';
      document.getElementById('c-name').textContent=nearest.Name;
      document.getElementById('c-stats').innerHTML=
        `MB ${nearest.MB} · xMB ${nearest.xMB}<br>err: ${nearest.pe>0?'+':''}${nearest.pe}%`;
      callout.classList.add('show');
    } else { callout.classList.remove('show'); }
  });
  canvas.addEventListener('mouseleave',()=>callout.classList.remove('show'));
}

function buildOutliers() {
  const sorted = [...PLAYERS].sort((a,b)=>Math.abs(b.pe)-Math.abs(a.pe)).slice(0,12);
  const maxAbs = Math.max(...sorted.map(p=>Math.abs(p.pe)));
  document.getElementById('outlier-strip').innerHTML = sorted.map(p=>{
    const w   = Math.round((Math.abs(p.pe)/maxAbs)*100);
    const col = p.pe>0?'#f87171':'#4ade80';
    return `<div class="outlier-row">
      <span class="outlier-name">${p.Name}</span>
      <div class="outlier-track"><div class="outlier-fill" style="width:${w}%;background:${col};opacity:.85;"></div></div>
      <span class="outlier-val" style="color:${col}">${p.pe>0?'+':''}${p.pe}%</span>
    </div>`;
  }).join('');
}

/* ============================================================
   TAB 3 — REPORT CARDS
   ============================================================ */
let activeGrades = new Set(['A','B','C','D','F']);

function rcInit() {
  const gf = document.getElementById('grade-filter');
  if (gf.children.length === 0) {
    gf.innerHTML = Object.entries(GRADE_CFG).map(([g,cfg])=>
      `<button class="grade-btn active" id="gbtn-${g}"
        style="color:${cfg.color};background:${cfg.bg};border-color:${cfg.border}"
        onclick="rcToggleGrade('${g}')">${g}</button>`
    ).join('');
  }
  rcRender();
}

function rcToggleGrade(g) {
  if(activeGrades.has(g)){ if(activeGrades.size===1) return; activeGrades.delete(g); }
  else activeGrades.add(g);
  document.getElementById('gbtn-'+g).classList.toggle('active', activeGrades.has(g));
  rcRender();
}

function rcRender() {
  const q    = (document.getElementById('rc-search')||{}).value?.toLowerCase()||'';
  const sort = (document.getElementById('rc-sort')||{}).value||'name';
  const GRADE_ORDER={A:0,B:1,C:2,D:3,F:4};

  let list = PLAYERS.filter(p => p.Name.toLowerCase().includes(q) && activeGrades.has(p.grade));
  if(sort==='name')     list.sort((a,b)=>a.Name.localeCompare(b.Name));
  if(sort==='mb-desc')  list.sort((a,b)=>b.MB-a.MB);
  if(sort==='err-desc') list.sort((a,b)=>Math.abs(b.pe)-Math.abs(a.pe));
  if(sort==='grade')    list.sort((a,b)=>GRADE_ORDER[a.grade]-GRADE_ORDER[b.grade]);

  const grid = document.getElementById('cards-grid');
  grid.innerHTML = list.length===0
    ? `<div class="empty-state" style="grid-column:1/-1">No players match the current filters.</div>`
    : list.map(rcBuildCard).join('');
  document.getElementById('rc-count').textContent = `${list.length} of ${PLAYERS.length} players`;
}

function rcBuildCard(p) {
  const cfg=GRADE_CFG[p.grade], ec=errStyle(p.pe);
  const ROWS=[
    {label:'Total Bases',actual:p.TB,pred:p.xTB},
    {label:'Hits',       actual:p.H, pred:p.xH },
    {label:'Walks',      actual:p.BB,pred:p.xBB},
    {label:'SB',         actual:p.SB,pred:p.xSB},
  ];
  const rowsHtml = ROWS.map(s=>{
    const cap=Math.max(s.actual,s.pred,1);
    const wa=Math.round((s.actual/cap)*100), wp=Math.round((s.pred/cap)*100);
    return `<div class="cstat-row">
      <span class="cstat-key">${s.label}</span>
      <div class="cstat-bar"><div class="cstat-track">
        <div class="cbar-a" style="width:${wa}%"></div>
        <div class="cbar-p" style="width:${wp}%"></div>
      </div></div>
      <div class="cstat-vals"><span class="cstat-a">${s.actual}</span><span style="color:var(--muted)">/</span><span class="cstat-p">${s.pred}</span></div>
    </div>`;
  }).join('');

  return `<div class="report-card" onclick="jumpToPlayer('${p.Name.replace(/'/g,"\\'")}')">
    <div class="card-band" style="background:${cfg.color}"></div>
    <div class="card-top">
      <div class="card-ident">
        <div class="avatar" style="width:38px;height:38px;font-size:.85rem">${initials(p.Name)}</div>
        <div><div class="card-name">${p.Name}</div><div class="card-sea">2025 · 2019–2024 model</div></div>
      </div>
      <div class="grade-circle" style="color:${cfg.color};background:${cfg.bg};border-color:${cfg.border}">${p.grade}</div>
    </div>
    <div class="card-stats">${rowsHtml}</div>
    <div class="card-foot">
      <div><div class="cf-lbl">Actual MB</div><div class="cf-mb-a">${p.MB}</div></div>
      <span style="color:var(--muted)">→</span>
      <div><div class="cf-lbl">xMB</div><div class="cf-mb-p">${p.xMB}</div></div>
      <div class="cf-err" style="color:${ec};background:${ec}18;border:1px solid ${ec}33">${p.pe>0?'+':''}${p.pe}%</div>
    </div>
  </div>`;
}

function jumpToPlayer(name) {
  document.querySelectorAll('.section').forEach(s=>s.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));
  document.getElementById('tab-lookup').classList.add('active');
  document.querySelector('.tab-btn').classList.add('active');
  document.getElementById('lu-search').value = name;
  const p = PLAYERS.find(x=>x.Name===name);
  if (p) luRenderCard(p);
}

/* ============================================================
   TAB 4 — RANKINGS
   ============================================================ */
let lbSortKey='MB', lbSortDir='desc', lbPage=1;

function lbGetFiltered() {
  const q    = document.getElementById('lb-search').value.toLowerCase();
  const show = document.getElementById('lb-show').value;
  return PLAYERS.filter(p=>{
    if(!p.Name.toLowerCase().includes(q)) return false;
    if(show==='over'  && p.pe<=0) return false;
    if(show==='under' && p.pe>=0) return false;
    if(show==='a'     && p.grade!=='A') return false;
    if(show==='b'     && p.grade!=='B') return false;
    if(show==='cf'    && !['C','D','F'].includes(p.grade)) return false;
    return true;
  });
}

function lbGetSorted(list) {
  const GO={A:0,B:1,C:2,D:3,F:4};
  return [...list].sort((a,b)=>{
    let av=a[lbSortKey], bv=b[lbSortKey];
    if(lbSortKey==='grade'){av=GO[a.grade];bv=GO[b.grade];}
    if(lbSortKey==='Name') return lbSortDir==='asc'?av.localeCompare(bv):bv.localeCompare(av);
    return lbSortDir==='desc'?bv-av:av-bv;
  });
}

const LB_COLS=[
  {key:'rank', label:'#',        sortable:false},
  {key:'Name', label:'Player',   sortable:true },
  {key:'grade',label:'Grade',    sortable:true },
  {key:'MB',   label:'MB',       sortable:true },
  {key:'mbbar',label:'',         sortable:false},
  {key:'xMB',  label:'xMB',      sortable:true },
  {key:'pe',   label:'xMB err%', sortable:true },
  {key:'TB',   label:'TB',       sortable:true },
  {key:'xTB',  label:'xTB',      sortable:true },
  {key:'H',    label:'H',        sortable:true },
  {key:'xH',   label:'xH',       sortable:true },
  {key:'BB',   label:'BB',       sortable:true },
  {key:'SB',   label:'SB',       sortable:true },
];

function lbBuildThead() {
  document.getElementById('lb-thead').innerHTML = '<tr>'+
    LB_COLS.map(c=>{
      const active = c.key===lbSortKey ? 'sort-active':'';
      const arrow  = c.key===lbSortKey ? (lbSortDir==='desc'?' ↓':' ↑'):'';
      return c.sortable
        ? `<th class="sortable ${active}" onclick="lbSetSort('${c.key}')">${c.label}${arrow}</th>`
        : `<th>${c.label}</th>`;
    }).join('')+'</tr>';
}

function lbRender() {
  const filtered  = lbGetFiltered();
  const sorted    = lbGetSorted(filtered);
  const pp        = +document.getElementById('lb-pp').value;
  const totalPages= Math.ceil(sorted.length/pp)||1;
  if(lbPage>totalPages) lbPage=totalPages;
  const page = sorted.slice((lbPage-1)*pp, lbPage*pp);

  // Summary KPIs
  const mapes = filtered.map(p=>Math.abs(p.pe));
  const avgM  = mapes.length?(mapes.reduce((a,b)=>a+b,0)/mapes.length).toFixed(1):'—';
  const overP = filtered.length?Math.round(filtered.filter(p=>p.pe>0).length/filtered.length*100):0;
  document.getElementById('summary-strip').innerHTML = `
    <div class="skpi"><div class="skpi-lbl">PLAYERS SHOWN</div><div class="skpi-val" style="color:var(--accent)">${filtered.length}</div></div>
    <div class="skpi"><div class="skpi-lbl">MEAN ABS ERR%</div><div class="skpi-val" style="color:var(--amber)">${avgM}%</div></div>
    <div class="skpi"><div class="skpi-lbl">OVER-PREDICTED</div><div class="skpi-val" style="color:var(--over)">${overP}%</div></div>
    <div class="skpi"><div class="skpi-lbl">GRADE A (≤3%)</div><div class="skpi-val" style="color:var(--under)">${filtered.filter(p=>p.grade==='A').length}</div></div>`;

  lbBuildThead();

  const medal=r=>r===1?'🥇':r===2?'🥈':r===3?'🥉':r;
  document.getElementById('lb-tbody').innerHTML = page.map((p,i)=>{
    const cfg=GRADE_CFG[p.grade], ec=errStyle(p.pe);
    const bw=Math.round((p.MB/maxMB)*100);
    const rank=(lbPage-1)*pp+i+1;
    return `<tr>
      <td class="rank-c">${medal(rank)}</td>
      <td class="name-c" onclick="jumpToPlayer('${p.Name.replace(/'/g,"\\'")}'')">${p.Name}</td>
      <td><span class="gbadge" style="color:${cfg.color};background:${cfg.bg};border-color:${cfg.border}">${p.grade}</span></td>
      <td class="acc-c">${p.MB}</td>
      <td><div class="mb-bar-cell"><div class="mb-bar-track"><div class="mb-bar-fill" style="width:${bw}%"></div></div></div></td>
      <td class="pred-c">${p.xMB}</td>
      <td><span class="err-pill" style="color:${ec};background:${ec}18;border:1px solid ${ec}33">${p.pe>0?'+':''}${p.pe}%</span></td>
      <td>${p.TB}</td><td class="pred-c">${p.xTB}</td>
      <td>${p.H}</td><td class="pred-c">${p.xH}</td>
      <td>${p.BB}</td><td>${p.SB}</td>
    </tr>`;
  }).join('');

  document.getElementById('lb-count').textContent=`${filtered.length} players`;
  lbBuildPagination(totalPages);
}

function lbBuildPagination(total) {
  const pag=document.getElementById('lb-pagination');
  if(total<=1){pag.innerHTML='';return;}
  let html=`<button class="pg-btn" onclick="lbGoPage(${lbPage-1})" ${lbPage===1?'disabled':''}>← prev</button>`;
  const range=[];
  for(let i=1;i<=total;i++){
    if(i===1||i===total||Math.abs(i-lbPage)<=1) range.push(i);
    else if(range[range.length-1]!=='…') range.push('…');
  }
  range.forEach(p=>{
    if(p==='…') html+=`<span class="pg-info">…</span>`;
    else html+=`<button class="pg-btn ${p===lbPage?'pg-active':''}" onclick="lbGoPage(${p})">${p}</button>`;
  });
  html+=`<button class="pg-btn" onclick="lbGoPage(${lbPage+1})" ${lbPage===total?'disabled':''}>next →</button>`;
  pag.innerHTML=html;
}

function lbGoPage(n) {
  const pp=+document.getElementById('lb-pp').value;
  const total=Math.ceil(lbGetFiltered().length/pp)||1;
  lbPage=Math.max(1,Math.min(n,total));
  lbRender();
}

function lbSetSort(key) {
  lbSortDir = lbSortKey===key ? (lbSortDir==='desc'?'asc':'desc') : 'desc';
  lbSortKey = key;
  lbPage=1;
  lbRender();
}

/* ── Scroll progress bar (story tab) ── */
window.addEventListener('scroll',()=>{
  const h=document.documentElement;
  document.getElementById('progress-bar').style.width=
    (h.scrollTop/(h.scrollHeight-h.clientHeight)*100)+'%';
});
</script>
</body>
</html>
"""


# ── Build function ────────────────────────────────────────────────────────────
def build(csv_path: str, out_path: str) -> None:
    players = load_players(csv_path)
    players_json = json.dumps(players, ensure_ascii=False)

    html = HTML_TEMPLATE.replace("/*PLAYERS_DATA*/", players_json)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"  Built:  {out_path}  ({len(players)} players)", file=sys.stderr)
    print(f"  Size:   {len(html) // 1024} KB", file=sys.stderr)


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bake Statcast CSV into a self-contained HTML explorer.")
    parser.add_argument("--csv", default="expected_2025_stats.csv",
                        help="Path to expected_2025_stats.csv (default: expected_2025_stats.csv)")
    parser.add_argument("--out", default="statcast_explorer.html",
                        help="Output HTML file path (default: statcast_explorer.html)")
    args = parser.parse_args()

    build(args.csv, args.out)
    print(f"\nDone! Open {args.out} in any browser.")