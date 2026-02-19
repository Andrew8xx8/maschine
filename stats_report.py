#!/usr/bin/env python3
"""
Generate interactive HTML report from pad_trainer stats.

Usage:
    python stats_report.py name            # → opens stats/name.html
    python stats_report.py name --no-open  # generate only
    python stats_report.py                 # all students
"""

import json
import sys
import webbrowser
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots

STATS_DIR = Path(__file__).parent / "stats"

C = {
    'green': '#4caf50', 'yellow': '#ffc107', 'red': '#f44336',
    'bg': '#0d1117', 'surface': '#161b22', 'border': '#21262d',
    'text': '#c9d1d9', 'muted': '#484f58', 'white': '#ffffff',
    'accent': '#7c4dff', 'blue': '#58a6ff',
}

LAYER_COLORS = [
    '#7c4dff', '#00bcd4', '#ff9800', '#e91e63',
    '#8bc34a', '#795548', '#03a9f4', '#cddc39',
]

BANKS = [
    (0,  16, 'Beginner'),
    (16, 32, 'Intermediate'),
    (32, 48, 'Pro'),
    (48, 64, 'Virtuoso'),
]

EXERCISES_PER_BANK = 16
GRID_COLS = 4
GRID_ROWS = 4

GREEN_SHADES = [
    (80, '#39d353'),
    (60, '#26a641'),
    (40, '#006d32'),
    (1,  '#0e4429'),
    (0,  '#0e4429'),
]
GREY = '#21262d'


def load_passes(path):
    passes = []
    for line in path.open():
        line = line.strip()
        if line:
            try:
                passes.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return passes


def _all_offsets(p):
    return [ly['max_off'] for lp in p.get('loops', [])
            for ly in lp.get('layers', []) if ly['max_off'] > 0]


def _grade_counts(passes):
    g = sum(p['summary']['greens'] for p in passes)
    y = sum(p['summary']['yellows'] for p in passes)
    r = sum(p['summary']['reds'] for p in passes)
    return g, y, r


def _green_rate(passes):
    g, y, r = _grade_counts(passes)
    t = g + y + r
    return round(g / t * 100) if t else 0


def _avg_offset(passes):
    offs = [o for p in passes for o in _all_offsets(p)]
    return round(sum(offs) / len(offs), 1) if offs else 0


def _fig_layout(fig, height=None):
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor=C['surface'],
        font=dict(color=C['text'], family='-apple-system, SF Pro, Segoe UI, sans-serif', size=12),
        legend=dict(orientation='h', y=-0.18, font=dict(size=11)),
        margin=dict(t=10, b=10, l=50, r=20),
        height=height,
    )
    fig.update_xaxes(gridcolor=C['border'], zeroline=False)
    fig.update_yaxes(gridcolor=C['border'], zeroline=False)
    return fig


def _shade(pct):
    for threshold, color in GREEN_SHADES:
        if pct >= threshold:
            return color
    return GREY


def _hex_to_rgba(hex_color, alpha):
    h = hex_color.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f'rgba({r},{g},{b},{alpha})'


# ── progress charts ──────────────────────────────────────────────────

def make_progress_charts(passes):
    sessions = defaultdict(list)
    for p in passes:
        sessions[p['session']].append(p)
    sess_ids = sorted(sessions.keys())
    labels = [f"#{s}" for s in sess_ids]

    bpm_max = [max(max(p['bpm'], p['bpm_after']) for p in sessions[s])
               for s in sess_ids]
    gr = [_green_rate(sessions[s]) for s in sess_ids]
    avg_offs = [_avg_offset(sessions[s]) for s in sess_ids]

    charts = []
    for title, y, color, suffix, invert in [
        ('Max BPM', bpm_max, C['accent'], '', False),
        ('Accuracy', avg_offs, C['yellow'], 'ms', True),
        ('Green rate', gr, C['green'], '%', False),
    ]:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=labels, y=y, mode='lines+markers',
            line=dict(color=color, width=3), marker=dict(size=8),
            fill='tozeroy',
            fillcolor=_hex_to_rgba(color, 0.08),
            hovertemplate=f'%{{y}}{suffix}<extra></extra>',
        ))
        fig.update_yaxes(
            gridcolor=C['border'], zeroline=False,
            autorange='reversed' if invert else True,
        )
        fig.update_xaxes(gridcolor=C['border'], zeroline=False)
        _fig_layout(fig, height=140)
        fig.update_layout(
            margin=dict(t=4, b=4, l=44, r=16),
            showlegend=False,
        )
        charts.append(
            f'<div class="metric-chart">'
            f'<div class="metric-label">{title}'
            f'<span class="metric-val">{y[-1]}{suffix}</span></div>'
            f'{fig.to_html(full_html=False, include_plotlyjs=False)}'
            f'</div>'
        )

    return '\n'.join(charts)


# ── exercise heatmap grid (GitHub-style) ─────────────────────────────

def _best_green_rate(by_idx, i):
    if i not in by_idx:
        return None
    best = 0
    for p in by_idx[i]:
        s = p.get('summary', {})
        g_count = s.get('greens', 0)
        t = g_count + s.get('yellows', 0) + s.get('reds', 0)
        if t > 0:
            best = max(best, g_count / t)
    return round(best * 100)


def make_exercise_grid(passes):
    by_idx = defaultdict(list)
    idx_to_name = {}
    for p in passes:
        idx = p.get('exercise_idx', -1)
        by_idx[idx].append(p)
        idx_to_name[idx] = p.get('exercise', f'#{idx+1}')

    html_parts = []
    for bank_start, bank_end, bank_name in BANKS:
        has_data = any(i in by_idx for i in range(bank_start, bank_end))
        if not has_data and bank_start > 0:
            cells = []
            for i in range(bank_start, bank_end):
                cells.append(
                    f'<div class="grid-cell empty" title="{bank_name} #{i - bank_start + 1}">'
                    f'</div>'
                )
            html_parts.append(
                f'<div class="bank-row">'
                f'<div class="bank-label">{bank_name}</div>'
                f'<div class="bank-grid">{"".join(cells)}</div>'
                f'</div>'
            )
            continue

        cells = []
        for i in range(bank_start, bank_end):
            pct = _best_green_rate(by_idx, i)
            if pct is not None:
                bg = _shade(pct)
                name = idx_to_name.get(i, f'#{i+1}')
                tooltip = f'{name} — {pct}% green'
            else:
                bg = GREY
                tooltip = f'#{i - bank_start + 1} — not played'

            cells.append(
                f'<div class="grid-cell" style="background:{bg}" title="{tooltip}">'
                f'<span class="grid-num">{i - bank_start + 1}</span></div>'
            )

        html_parts.append(
            f'<div class="bank-row">'
            f'<div class="bank-label">{bank_name}</div>'
            f'<div class="bank-grid">{"".join(cells)}</div>'
            f'</div>'
        )

    return '<div class="exercise-grid">' + ''.join(html_parts) + '</div>'


# ── exercise cards ───────────────────────────────────────────────────

_DOT_COLORS = {'green': C['green'], 'yellow': C['yellow'], 'red': C['red']}

import re as _re
_DUP_NUM = _re.compile(r'^(\d+)\s*[—–-]\s*\1\s*[—–-]\s*')


def _clean_name(name):
    return _DUP_NUM.sub(r'\1 — ', name)


def _pass_avg_offset(p):
    offs = _all_offsets(p)
    return round(sum(offs) / len(offs), 1) if offs else 0


def _pass_green_pct(p):
    s = p.get('summary', {})
    g = s.get('greens', 0)
    t = g + s.get('yellows', 0) + s.get('reds', 0)
    return round(g / t * 100) if t else 0


def _pass_dots(p):
    dots = []
    for lp in p.get('loops', []):
        g = lp.get('grade', 'red')
        color = _DOT_COLORS.get(g, C['red'])
        dots.append(f'<span class="dot" style="background:{color}"></span>')
    return ''.join(dots)


def _trend_color(val, lower_is_better=False):
    if val == 0:
        return C['muted']
    if lower_is_better:
        return C['green'] if val < 0 else C['red']
    return C['green'] if val > 0 else C['red']


def make_exercise_cards(passes):
    exercises = defaultdict(list)
    for p in passes:
        exercises[p['exercise']].append(p)
    ex_order = list(dict.fromkeys(p['exercise'] for p in passes))

    cards = []
    for ex_name in ex_order:
        ex_passes = exercises[ex_name]
        display_name = _clean_name(ex_name)

        first_bpm = ex_passes[0]['bpm']
        last_bpm = max(ex_passes[-1]['bpm'], ex_passes[-1]['bpm_after'])

        rows = []
        prev_off = None
        prev_pct = None
        for p in ex_passes:
            bpm = p['bpm']
            avg_off = _pass_avg_offset(p)
            pct = _pass_green_pct(p)
            dots = _pass_dots(p)

            off_color = C['text']
            if prev_off is not None:
                d = avg_off - prev_off
                if abs(d) >= 2:
                    off_color = _trend_color(d, lower_is_better=True)
            pct_color = C['text']
            if prev_pct is not None:
                d = pct - prev_pct
                if abs(d) >= 5:
                    pct_color = _trend_color(d)

            rows.append(
                f'<div class="pass-row">'
                f'<span class="pass-bpm">{bpm}</span>'
                f'<span class="pass-dots">{dots}</span>'
                f'<span class="pass-off" style="color:{off_color}">{avg_off:.0f}ms</span>'
                f'<span class="pass-pct" style="color:{pct_color}">{pct}%</span>'
                f'</div>'
            )
            prev_off = avg_off
            prev_pct = pct

        bpm_summary = (f'{first_bpm} → {last_bpm} BPM'
                        if last_bpm != first_bpm
                        else f'{last_bpm} BPM')

        cards.append(
            f'<div class="ex-card">'
            f'<div class="ex-header">'
            f'<span class="ex-name">{display_name}</span>'
            f'<span class="ex-summary">{bpm_summary}</span>'
            f'</div>'
            f'{"".join(rows)}'
            f'</div>'
        )

    return '\n'.join(cards)


# ── build ────────────────────────────────────────────────────────────

def build_report(student, passes, out_path):
    g, y, r = _grade_counts(passes)
    total_loops = g + y + r
    green_rate = round(g / total_loops * 100) if total_loops else 0
    max_bpm = max(max(p['bpm'], p['bpm_after']) for p in passes)
    avg_off = _avg_offset(passes)
    session_groups = defaultdict(list)
    for p in passes:
        session_groups[p['session']].append(p)
    sessions = len(session_groups)

    total_secs = 0
    for sess_passes in session_groups.values():
        try:
            t_start = datetime.fromisoformat(sess_passes[0]['session_start'])
            t_end = datetime.fromisoformat(sess_passes[-1]['ts'])
            total_secs += max(0, (t_end - t_start).total_seconds())
        except (KeyError, ValueError):
            total_secs += sum(p['duration_s'] for p in sess_passes)
    mins = int(total_secs // 60)
    secs = int(total_secs % 60)

    progress_charts = make_progress_charts(passes)
    exercise_grid = make_exercise_grid(passes)
    exercise_cards = make_exercise_cards(passes)

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Pad Trainer — {student}</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
    font-family: -apple-system, 'SF Pro', 'Segoe UI', system-ui, sans-serif;
    background: {C['bg']}; color: {C['text']};
    max-width: 800px; margin: 0 auto; padding: 32px 20px;
}}

.hero {{
    text-align: center; margin-bottom: 32px;
}}
.hero h1 {{
    font-size: 16px; font-weight: 400; color: {C['muted']};
    text-transform: uppercase; letter-spacing: 2px; margin-bottom: 8px;
}}
.hero .big {{
    font-size: 64px; font-weight: 800; color: {C['white']};
    line-height: 1;
}}
.hero .big small {{
    font-size: 20px; font-weight: 400; color: {C['muted']};
}}
.hero .sub {{
    font-size: 14px; color: {C['muted']}; margin-top: 8px;
}}

.kpi-row {{
    display: grid; grid-template-columns: repeat(4, 1fr);
    gap: 12px; margin-bottom: 36px;
}}
.kpi {{
    background: {C['surface']}; border: 1px solid {C['border']};
    border-radius: 12px; padding: 16px; text-align: center;
}}
.kpi .val {{
    font-size: 26px; font-weight: 700; color: {C['white']};
}}
.kpi .lbl {{
    font-size: 11px; color: {C['muted']}; margin-top: 4px;
    text-transform: uppercase; letter-spacing: 0.5px;
}}

.section {{
    margin-bottom: 36px;
}}
.section-title {{
    font-size: 13px; font-weight: 600; color: {C['muted']};
    text-transform: uppercase; letter-spacing: 1px;
    margin-bottom: 12px;
}}

/* ── exercise grid ── */
.exercise-grid {{
    display: flex; gap: 16px; margin-bottom: 8px;
}}
.bank-row {{
    display: flex; flex-direction: column; align-items: center; gap: 6px;
}}
.bank-label {{
    font-size: 9px; font-weight: 600; color: {C['muted']};
    text-transform: uppercase; letter-spacing: 0.5px;
}}
.bank-grid {{
    display: grid; grid-template-columns: repeat({GRID_COLS}, 24px);
    grid-template-rows: repeat({GRID_ROWS}, 24px);
    gap: 3px;
}}
.grid-cell {{
    border-radius: 3px;
    display: flex; align-items: center; justify-content: center;
    cursor: default; transition: transform .1s;
}}
.grid-cell.empty {{
    background: {C['border']}; opacity: 0.3;
}}
.grid-cell:hover {{ transform: scale(1.2); }}
.grid-num {{
    font-size: 8px; font-weight: 600; color: rgba(255,255,255,0.35);
}}
.grid-legend {{
    display: flex; gap: 5px; align-items: center;
    font-size: 9px; color: {C['muted']}; margin-top: 8px;
}}
.grid-legend-swatch {{
    width: 10px; height: 10px; border-radius: 2px; display: inline-block;
}}

/* ── metric charts ── */
.metric-row {{
    display: flex; flex-direction: column; gap: 8px;
}}
.metric-chart {{
    background: {C['surface']}; border: 1px solid {C['border']};
    border-radius: 10px; padding: 10px 12px 4px;
}}
.metric-label {{
    font-size: 11px; font-weight: 600; color: {C['muted']};
    text-transform: uppercase; letter-spacing: 0.5px;
    display: flex; justify-content: space-between; align-items: baseline;
    margin-bottom: 2px;
}}
.metric-val {{
    font-size: 18px; font-weight: 700; color: {C['white']};
    letter-spacing: 0; text-transform: none;
}}

/* ── exercise cards ── */
.ex-grid {{
    display: grid; grid-template-columns: 1fr; gap: 12px;
}}
.ex-card {{
    background: {C['surface']}; border: 1px solid {C['border']};
    border-radius: 12px; padding: 14px 16px;
}}
.ex-header {{
    display: flex; justify-content: space-between; align-items: baseline;
    margin-bottom: 8px;
}}
.ex-name {{
    font-size: 14px; font-weight: 600; color: {C['white']};
}}
.ex-summary {{
    font-size: 12px; color: {C['muted']};
}}
.pass-row {{
    display: grid; grid-template-columns: 42px 1fr 52px 44px;
    gap: 8px; align-items: center;
    padding: 4px 2px; border-radius: 4px;
    font-size: 12px; color: {C['text']};
}}
.pass-row:nth-child(even) {{
    background: rgba(255,255,255,0.02);
}}
.pass-bpm {{
    font-weight: 600; font-size: 12px; font-variant-numeric: tabular-nums;
}}
.pass-dots {{
    display: flex; gap: 4px; align-items: center;
}}
.dot {{
    width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0;
}}
.pass-off {{
    text-align: right; font-variant-numeric: tabular-nums; color: {C['muted']};
    font-size: 11px;
}}
.pass-pct {{
    text-align: right; font-variant-numeric: tabular-nums;
    font-size: 11px; font-weight: 600;
}}

@media (max-width: 600px) {{
    .kpi-row {{ grid-template-columns: repeat(2, 1fr); }}
    .exercise-grid {{ gap: 10px; }}
    .bank-grid {{ grid-template-columns: repeat({GRID_COLS}, 18px); grid-template-rows: repeat({GRID_ROWS}, 18px); gap: 2px; }}
}}
</style>
</head>
<body>

<div class="hero">
    <h1>{student}</h1>
    <div class="big">{green_rate}% <small>green</small></div>
    <div class="sub">{sessions} sessions · {len(passes)} passes · {mins}m {secs}s practice</div>
</div>

<div class="kpi-row">
    <div class="kpi"><div class="val">{max_bpm}</div><div class="lbl">Max BPM</div></div>
    <div class="kpi"><div class="val">{avg_off:.0f}ms</div><div class="lbl">Avg accuracy</div></div>
    <div class="kpi"><div class="val">{g}</div><div class="lbl">🟢 loops</div></div>
    <div class="kpi"><div class="val">{total_loops}</div><div class="lbl">Total loops</div></div>
</div>

<div class="section">
    <div class="section-title">Lessons</div>
    {exercise_grid}
    <div class="grid-legend">
        <span class="grid-legend-swatch" style="background:{GREY}"></span> not played
        <span class="grid-legend-swatch" style="background:#0e4429"></span> &lt;40%
        <span class="grid-legend-swatch" style="background:#006d32"></span> 40-60%
        <span class="grid-legend-swatch" style="background:#26a641"></span> 60-80%
        <span class="grid-legend-swatch" style="background:#39d353"></span> 80%+
    </div>
</div>

<div class="section">
    <div class="section-title">Progress by session</div>
    <div class="metric-row">
    {progress_charts}
    </div>
</div>

<div class="section">
    <div class="section-title">Exercises</div>
    <div class="ex-grid">
        {exercise_cards}
    </div>
</div>

</body>
</html>'''

    out_path.write_text(html, encoding='utf-8')
    return out_path


def main():
    args = sys.argv[1:]
    no_open = '--no-open' in args
    args = [a for a in args if not a.startswith('--')]

    if not STATS_DIR.exists():
        print(f"  No stats/ directory")
        return

    targets = ([STATS_DIR / f"{a}.jsonl" for a in args]
               if args else sorted(STATS_DIR.glob("*.jsonl")))

    if not targets:
        print("  No .jsonl files found")
        return

    for jsonl_path in targets:
        if not jsonl_path.exists():
            print(f"  {jsonl_path} — not found")
            continue
        passes = load_passes(jsonl_path)
        if not passes:
            print(f"  {jsonl_path.stem} — empty")
            continue
        out = jsonl_path.with_suffix('.html')
        build_report(jsonl_path.stem, passes, out)
        print(f"  {jsonl_path.stem}: {len(passes)} passes → {out}")
        if not no_open:
            webbrowser.open(out.as_uri())


if __name__ == '__main__':
    main()
