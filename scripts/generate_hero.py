#!/usr/bin/env python3
"""Generate the animated terminal-session hero SVGs (dark + light).

With --embed-snake DARK_SVG LIGHT_SVG, the Platane/snk contribution graph is
composed into the terminal as the output of a snake command — this mode runs
in the Snake workflow daily. The animation is pure CSS keyframes so it plays
inside GitHub's <img>-embedded SVG sandbox (no JS allowed there).
"""

import os
import random
import re
import sys
from xml.sax.saxutils import escape

CHAR_W = 9.6
FONT_SIZE = 16
LINE_H = 27
LEFT = 40
TOP = 76
WIDTH = 900
PROMPT = "$ "

SESSION = [
    ("type", "whoami"),
    ("out", [("guitaripod", "text"), (" · ", "muted"), ("engineer who ships.", "green")]),
    ("type", 'snake --eat ~/contributions --since "365 days ago"'),
    ("snake", None),
    ("idle", None),
]

SNAKE_H = 132
SNAKE_SCALE = 0.94

TYPE_CPS = 32
GAP_AFTER_TYPE = 0.22
GAP_AFTER_OUT = 0.38
HOLD = 8.0

DARK = {
    "bg": "#0d1117",
    "panel": "#161b22",
    "titlebar": "#1c2128",
    "border": "#2d333b",
    "text": "#e6edf3",
    "muted": "#9198a1",
    "green": "#33ff66",
    "amber": "#ffb000",
    "red": "#ff7b72",
    "rain": True,
    "glow": True,
}

LIGHT = {
    "bg": "#fdf6e3",
    "panel": "#f6eed8",
    "titlebar": "#eee8d5",
    "border": "#dcd3b8",
    "text": "#073642",
    "muted": "#586e75",
    "green": "#005f00",
    "amber": "#7a5d00",
    "red": "#cb4b16",
    "rain": False,
    "glow": False,
}

RAIN_GLYPHS = "アィウェオカキクケコサシスセソ0123456789$#*+"


def build_timeline():
    events = []
    t = 0.8
    line = 0
    for kind, payload in SESSION:
        if kind == "type":
            dur = len(payload) / TYPE_CPS
            events.append({"kind": "type", "line": line, "text": payload, "start": t, "dur": dur})
            t += dur + GAP_AFTER_TYPE
            line += 1
        elif kind == "out":
            events.append({"kind": "out", "line": line, "parts": payload, "start": t})
            t += GAP_AFTER_OUT
            line += 1
        elif kind == "snake":
            events.append({"kind": "snake", "line": line, "start": t})
            t += GAP_AFTER_OUT
            line += SNAKE_LINES
        elif kind == "idle":
            events.append({"kind": "idle", "line": line, "start": t})
    total = t + HOLD
    return events, total


def pct(seconds, total):
    return round(seconds / total * 100, 3)


def rain_layer(palette, height):
    if not palette["rain"]:
        return "", ""
    rng = random.Random(42)
    cols = []
    css = []
    n_cols = 16
    for i in range(n_cols):
        x = 30 + i * (WIDTH - 60) / (n_cols - 1) + rng.uniform(-10, 10)
        dur = rng.uniform(6, 14)
        delay = rng.uniform(-14, 0)
        glyphs = "".join(
            f'<text x="0" y="{j * 22}" font-size="14" fill="{palette["green"]}">{rng.choice(RAIN_GLYPHS)}</text>'
            for j in range(14)
        )
        cols.append(
            f'<g transform="translate({x:.0f},0)"><g class="rc rc{i}">{glyphs}</g></g>'
        )
        css.append(
            f".rc{i}{{animation:fall {dur:.2f}s linear {delay:.2f}s infinite}}"
        )
    css.append(
        f"@keyframes fall{{from{{transform:translateY(-308px)}}to{{transform:translateY({height}px)}}}}"
    )
    group = (
        f'<clipPath id="rainclip"><rect x="10" y="46" width="{WIDTH - 20}" height="{height - 56}"/></clipPath>'
        f'<g clip-path="url(#rainclip)" opacity="0.13">{"".join(cols)}</g>'
    )
    return group, "\n".join(css)


def extract_snake(path):
    snake = open(path).read()
    style = re.search(r"<style>(.*?)</style>", snake, re.S).group(1)
    body = snake[snake.index("</style>") + len("</style>"):]
    body = body[: body.rindex("</svg>")]
    return style, body


def render(palette, name, snake_path=None):
    events, total = build_timeline()
    n_lines = events[-1]["line"] + 1
    height = TOP + n_lines * LINE_H + 34

    body = []
    css = [
        f"text{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:{FONT_SIZE}px}}",
        ".cursor{animation:blink 1.1s steps(2,jump-none) infinite}",
        "@keyframes blink{50%{opacity:0}}",
    ]

    rain_svg, rain_css = rain_layer(palette, height)
    if rain_css:
        css.append(rain_css)

    cursor_frames = []
    glow = 'filter="url(#glow)"' if palette["glow"] else ""

    for idx, ev in enumerate(events):
        y = TOP + ev["line"] * LINE_H
        if ev["kind"] == "type":
            text = ev["text"]
            w = len(text) * CHAR_W
            x_text = LEFT + len(PROMPT) * CHAR_W
            start_pct = pct(ev["start"], total)
            end_pct = pct(ev["start"] + ev["dur"], total)
            body.append(
                f'<text x="{LEFT}" y="{y}" fill="{palette["green"]}" class="pr pr{idx}">{PROMPT.strip()}</text>'
            )
            body.append(
                f'<g clip-path="url(#tc{idx})">'
                f'<text x="{x_text}" y="{y}" fill="{palette["text"]}" textLength="{w:.1f}" lengthAdjust="spacing">{escape(text)}</text>'
                f"</g>"
            )
            body.append(
                f'<clipPath id="tc{idx}"><rect class="tw{idx}" x="{x_text}" y="{y - 18}" width="{w:.1f}" height="24"/></clipPath>'
            )
            css.append(
                f".tw{idx}{{animation:t{idx} {total}s infinite}}"
                f"@keyframes t{idx}{{0%{{width:0}}{start_pct}%{{width:0;animation-timing-function:steps({len(text)})}}{end_pct}%{{width:{w:.1f}px}}100%{{width:{w:.1f}px}}}}"
            )
            css.append(
                f".pr{idx}{{opacity:0;animation:o{idx} {total}s infinite}}"
                f"@keyframes o{idx}{{0%{{opacity:0}}{max(start_pct - 0.1, 0)}%{{opacity:0}}{start_pct}%{{opacity:1}}100%{{opacity:1}}}}"
            )
            cursor_frames.append((ev["start"], ev["start"] + ev["dur"], x_text, w, y))
        elif ev["kind"] == "out":
            start_pct = pct(ev["start"], total)
            x = LEFT
            for text, color_key in ev["parts"]:
                fill = palette[color_key if color_key != "text" else "text"]
                use_glow = glow if color_key == "green" else ""
                body.append(
                    f'<text x="{x}" y="{y}" fill="{fill}" {use_glow} xml:space="preserve" textLength="{len(text) * CHAR_W:.1f}" lengthAdjust="spacing" class="ol ol{idx}">{escape(text)}</text>'
                )
                x += len(text) * CHAR_W
            css.append(
                f".ol{idx}{{opacity:0;animation:o{idx} {total}s infinite}}"
                f"@keyframes o{idx}{{0%{{opacity:0}}{max(start_pct - 0.1, 0)}%{{opacity:0}}{start_pct}%{{opacity:1}}100%{{opacity:1}}}}"
            )
        elif ev["kind"] == "snake":
            start_pct = pct(ev["start"], total)
            snake_style, snake_body = extract_snake(snake_path)
            css.append(snake_style)
            css.append(
                f".sn{{opacity:0;animation:o{idx} {total}s infinite}}"
                f"@keyframes o{idx}{{0%{{opacity:0}}{max(start_pct - 0.1, 0)}%{{opacity:0}}{start_pct}%{{opacity:1}}100%{{opacity:1}}}}"
            )
            body.append(
                f'<clipPath id="snclip"><rect x="0" y="-14" width="{(WIDTH - 2 * LEFT) / SNAKE_SCALE:.0f}" height="{(SNAKE_H + 6) / SNAKE_SCALE:.0f}"/></clipPath>'
                f'<g class="sn" transform="translate({LEFT - 8},{y}) scale({SNAKE_SCALE})">'
                f'<g clip-path="url(#snclip)"><g transform="translate(16,12)">{snake_body}</g></g>'
                f"</g>"
            )
        elif ev["kind"] == "idle":
            start_pct = pct(ev["start"], total)
            body.append(
                f'<text x="{LEFT}" y="{y}" fill="{palette["green"]}" class="pr pr{idx}">{PROMPT.strip()}</text>'
            )
            css.append(
                f".pr{idx}{{opacity:0;animation:o{idx} {total}s infinite}}"
                f"@keyframes o{idx}{{0%{{opacity:0}}{max(start_pct - 0.1, 0)}%{{opacity:0}}{start_pct}%{{opacity:1}}100%{{opacity:1}}}}"
            )
            cursor_frames.append((ev["start"], total, LEFT + len(PROMPT) * CHAR_W, 0, y))

    kf_rules = ["0%{transform:translate(0,0);opacity:0}"]
    for start, end, x_base, w, y in cursor_frames:
        s = pct(start, total)
        e = pct(end, total)
        steps_fn = f"animation-timing-function:steps({max(int(w / CHAR_W), 1)});" if w else ""
        kf_rules.append(f"{s}%{{transform:translate({x_base:.1f}px,{y - 14}px);opacity:1;{steps_fn}}}")
        if w:
            kf_rules.append(f"{e}%{{transform:translate({x_base + w:.1f}px,{y - 14}px);opacity:1}}")
    kf_rules.append(f"100%{{transform:translate({cursor_frames[-1][2]:.1f}px,{cursor_frames[-1][4] - 14}px);opacity:1}}")
    css.append(f'.cpos{{animation:cmove {total}s step-end infinite}}@keyframes cmove{{{"".join(kf_rules)}}}')

    cursor_fill = palette["green"]
    body.append(
        f'<g class="cpos"><rect class="cursor" width="{CHAR_W:.1f}" height="19" fill="{cursor_fill}" {glow}/></g>'
    )

    css.append(
        "@media (prefers-reduced-motion:reduce){*{animation:none !important}.ol,.pr,.cpos{opacity:1 !important}}"
    )

    glow_def = (
        '<filter id="glow" x="-50%" y="-50%" width="200%" height="200%">'
        '<feGaussianBlur stdDeviation="2.5" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>'
        "</filter>"
        if palette["glow"]
        else ""
    )

    scanlines = (
        f'<pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse">'
        f'<rect width="4" height="1" fill="#000" opacity="0.16"/></pattern>'
        f'<rect x="10" y="46" width="{WIDTH - 20}" height="{height - 56}" fill="url(#scan)"/>'
        if palette["rain"]
        else ""
    )

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}" role="img" aria-label="guitaripod terminal session: engineer who ships. 9 apps on the App Store. midgarcorp.cc">
  <defs>{glow_def}</defs>
  <style>{"".join(css)}</style>
  <rect width="{WIDTH}" height="{height}" fill="{palette["bg"]}"/>
  <rect x="8" y="8" width="{WIDTH - 16}" height="{height - 16}" fill="{palette["panel"]}" stroke="{palette["border"]}" stroke-width="2"/>
  <rect x="8" y="8" width="{WIDTH - 16}" height="36" fill="{palette["titlebar"]}" stroke="{palette["border"]}" stroke-width="2"/>
  <circle cx="30" cy="26" r="6" fill="{palette["red"]}"/>
  <circle cx="52" cy="26" r="6" fill="{palette["amber"]}"/>
  <circle cx="74" cy="26" r="6" fill="{palette["green"]}"/>
  <text x="{WIDTH / 2}" y="31" text-anchor="middle" font-size="14" fill="{palette["muted"]}">guitaripod@midgar: ~</text>
  {rain_svg}
  {"".join(body)}
  {scanlines}
</svg>
'''
    os.makedirs("assets", exist_ok=True)
    with open(f"assets/{name}", "w") as f:
        f.write(svg)
    print(f"wrote assets/{name} ({len(svg)} bytes, {total:.1f}s loop)")


if len(sys.argv) == 4 and sys.argv[1] == "--embed-snake":
    SNAKE_LINES = (SNAKE_H // LINE_H) + 1
    render(DARK, "terminal-dark.svg", sys.argv[2])
    render(LIGHT, "terminal-light.svg", sys.argv[3])
else:
    SESSION = [entry for entry in SESSION if entry[0] != "snake"]
    SESSION = SESSION[:2] + [("idle", None)]
    SNAKE_LINES = 0
    render(DARK, "hero-dark.svg")
    render(LIGHT, "hero-light.svg")
