"""Presentation layer for the triage loop app: design tokens, CSS, and the
graph diagram.

Kept separate from app.py so the visual language can be changed without
touching the run logic, and from main.py so the agent stays headless.
"""

# --- tokens ----------------------------------------------------------------
# Instrument-panel palette: a warm painted-metal chassis in daylight, with
# polychrome signal colours the way real test equipment has them. Teal is
# lifted from the architecture diagram, where it marks the reflection edge.

CHASSIS = "#DEDCD5"
CHASSIS_DEEP = "#C9C6BC"
PAPER = "#F8F7F4"
INK = "#1B1A17"
INK_SOFT = "#6A675F"
HAIRLINE = "#A9A69C"

TEAL = "#0B6E63"
AMBER = "#B0731A"
CLAY = "#9E3A26"

TEAL_WASH = "#E2EDEA"
AMBER_WASH = "#F3E5C9"
CLAY_WASH = "#F0DED8"

# Node fill / stroke / label colour per run state.
TONES = {
    "idle": (CHASSIS_DEEP, HAIRLINE, INK_SOFT),
    "active": (AMBER_WASH, AMBER, INK),
    "done": (PAPER, TEAL, INK),
    "failed": (CLAY_WASH, CLAY, INK),
}

DISPLAY = "'Saira Semi Condensed', 'Arial Narrow', sans-serif"
MONO = "'IBM Plex Mono', ui-monospace, monospace"
SERIF = "'Source Serif 4', Georgia, serif"


CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Saira+Semi+Condensed:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500;600&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap');

:root {{
  --chassis: {CHASSIS};
  --chassis-deep: {CHASSIS_DEEP};
  --paper: {PAPER};
  --ink: {INK};
  --ink-soft: {INK_SOFT};
  --hairline: {HAIRLINE};
  --teal: {TEAL};
  --amber: {AMBER};
  --clay: {CLAY};
}}

/* --- strip the default Streamlit chrome --- */
header[data-testid="stHeader"], #MainMenu, footer {{ display: none !important; }}
[data-testid="stToolbar"] {{ display: none !important; }}
[data-testid="stDecoration"] {{ display: none !important; }}

.stApp {{ background: var(--chassis); }}
.block-container {{
  max-width: 1200px;
  padding: 2rem 2.5rem 5rem 2.5rem;
}}

/* --- masthead --- */
.tl-eyebrow {{
  font-family: {MONO};
  font-size: 10.5px;
  font-weight: 500;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--ink-soft);
  margin: 0 0 11px 0;
}}
.tl-title {{
  font-family: {DISPLAY} !important;
  font-size: 52px !important;
  font-weight: 700 !important;
  letter-spacing: -0.005em;
  text-transform: uppercase;
  line-height: 0.92 !important;
  margin: 0 !important;
  padding: 0 !important;
}}
.tl-title .a {{ color: {INK} !important; }}
.tl-title .b {{ color: {TEAL} !important; }}
.tl-standfirst {{
  font-family: {SERIF} !important;
  font-size: 15.5px !important;
  line-height: 1.5 !important;
  color: var(--ink-soft) !important;
  max-width: 58ch;
  margin: 18px 0 0 0 !important;
}}
.tl-rule {{
  height: 1px;
  background: var(--hairline);
  margin: 22px 0 20px 0;
}}

/* --- panel label used above each rail section --- */
.tl-label {{
  font-family: {DISPLAY};
  font-size: 11.5px;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--ink-soft);
  margin: 0 0 10px 0;
}}

/* --- attempt lamps --- */
.tl-lamps {{
  display: flex; align-items: center; gap: 9px;
  margin: -6px 0 0 4px;
}}
.tl-lamp {{
  width: 13px; height: 13px; border-radius: 50%;
  border: 1.5px solid var(--hairline);
  background: var(--chassis-deep);
}}
.tl-lamp.burned {{ background: var(--amber); border-color: var(--amber); }}
.tl-lamp.passed {{ background: var(--teal);  border-color: var(--teal); }}
.tl-lamp.spent  {{ background: var(--clay);  border-color: var(--clay); }}
.tl-lamps-note {{
  font-family: {MONO}; font-size: 11.5px; color: var(--ink-soft); margin-left: 8px;
}}

/* --- ticket facts --- */
.tl-facts {{ margin-top: 4px; }}
.tl-fact {{ margin-bottom: 11px; }}
.tl-fact-key {{
  font-family: {MONO}; font-size: 10px; font-weight: 500;
  letter-spacing: 0.14em; text-transform: uppercase; color: var(--ink-soft);
  display: block; margin-bottom: 2px;
}}
.tl-fact-val {{
  font-family: {SERIF}; font-size: 14.5px; line-height: 1.45; color: var(--ink);
}}
.tl-fact-val.mono {{ font-family: {MONO}; font-size: 12.5px; }}

/* --- readout step header --- */
.tl-step {{
  display: flex; align-items: baseline; gap: 12px;
  padding-bottom: 7px; margin-bottom: 0;
  border-bottom: 1px solid var(--hairline);
}}
.tl-step-node {{
  font-family: {MONO}; font-size: 13px; font-weight: 600;
  color: var(--ink); letter-spacing: -0.01em;
}}
.tl-step-gloss {{
  font-family: {DISPLAY}; font-size: 12px; font-weight: 600;
  letter-spacing: 0.1em; text-transform: uppercase; color: var(--ink-soft);
}}
.tl-step-meta {{
  font-family: {MONO}; font-size: 11px; color: var(--ink-soft);
  margin-left: auto; white-space: nowrap;
}}
.tl-step-node.pass {{ color: var(--teal); }}
.tl-step-node.fail {{ color: var(--clay); }}

/* --- verdict chip --- */
.tl-chip {{
  display: inline-block;
  font-family: {MONO}; font-size: 11px; font-weight: 600;
  letter-spacing: 0.16em; text-transform: uppercase;
  padding: 3px 10px; border-radius: 2px; margin-bottom: 9px;
}}
.tl-chip.pass {{ background: var(--teal); color: {PAPER}; }}
.tl-chip.fail {{ background: var(--clay); color: {PAPER}; }}

/* --- prose surfaces --- */
[class*="st-key-tlnote-"] p {{
  font-family: {SERIF} !important;
  font-size: 15px !important;
  line-height: 1.55 !important;
  color: var(--ink) !important;
  margin-bottom: 0.5em !important;
}}

/* the drafted reply: a letter on paper, not telemetry */
[class*="st-key-tlletter-"] {{
  background: var(--paper);
  border: 1px solid var(--hairline);
  border-left: 3px solid var(--teal);
  padding: 20px 24px 14px 24px;
  margin-top: 12px;
}}
[class*="st-key-tlletter-"] p,
[class*="st-key-tlletter-"] li {{
  font-family: {SERIF} !important;
  font-size: 15px !important;
  line-height: 1.6 !important;
  color: var(--ink) !important;
}}
[class*="st-key-tlletter-"] strong {{ font-weight: 600; }}
[class*="st-key-tlletter-"].spent {{ border-left-color: var(--clay); }}

[class*="st-key-tlstep-"] {{ margin-bottom: 26px; }}

/* --- outcome banner --- */
.tl-outcome {{
  border: 1px solid var(--hairline);
  border-top: 3px solid var(--teal);
  background: {TEAL_WASH};
  padding: 16px 20px;
  margin: 4px 0 18px 0;
}}
.tl-outcome.spent {{ border-top-color: var(--clay); background: {CLAY_WASH}; }}
.tl-outcome-head {{
  font-family: {DISPLAY}; font-size: 17px; font-weight: 700;
  letter-spacing: 0.06em; text-transform: uppercase; color: var(--ink);
  margin: 0 0 4px 0;
}}
.tl-outcome-sub {{
  font-family: {MONO}; font-size: 11.5px; color: var(--ink-soft); margin: 0;
}}

/* --- empty state --- */
.tl-empty {{
  border: 1px dashed var(--hairline);
  padding: 28px 26px;
  background: rgba(248,247,244,0.5);
}}
.tl-empty p {{
  font-family: {SERIF}; font-size: 15.5px; line-height: 1.55;
  color: var(--ink-soft); margin: 0;
}}

/* --- Streamlit widgets, quieted down --- */
.stButton > button {{
  font-family: {DISPLAY} !important;
  font-size: 13px !important;
  font-weight: 700 !important;
  letter-spacing: 0.14em !important;
  text-transform: uppercase !important;
  border-radius: 2px !important;
  border: 1px solid var(--teal) !important;
  background: var(--teal) !important;
  color: {PAPER} !important;
  padding: 0.5rem 1.1rem !important;
}}
.stButton > button:hover {{ background: #095A51 !important; border-color: #095A51 !important; }}
.stButton > button:focus-visible {{ outline: 2px solid var(--ink) !important; outline-offset: 2px !important; }}

[data-testid="stSegmentedControl"] button {{
  font-family: {MONO} !important;
  font-size: 12px !important;
  letter-spacing: 0.04em !important;
  border-radius: 2px !important;
}}

[data-testid="stExpander"] details {{
  border: 1px solid var(--hairline) !important;
  border-radius: 2px !important;
  background: transparent !important;
}}
[data-testid="stExpander"] summary p {{
  font-family: {MONO} !important; font-size: 11.5px !important;
  letter-spacing: 0.08em !important; text-transform: uppercase !important;
  color: var(--ink-soft) !important;
}}

@media (prefers-reduced-motion: reduce) {{
  * {{ animation: none !important; }}
}}
</style>
"""


# --- diagram ---------------------------------------------------------------
# Exercise 1: priority classification can bypass drafting and critique.

NODE_W, NODE_H = 150, 32
COL_X = 130
CENTER = COL_X + NODE_W // 2

MAIN = [
    ("new_ticket", 8),
    ("intake", 64),
    ("triage", 120),
    ("classify_priority", 176),
    ("draft_reply", 270),
    ("critique", 326),
]
MAIN_Y = dict(MAIN)

PRIORITY_BOX = (140, 222, 130, 30)
VERDICT_BOX = (150, 382, 110, 30)
SEND_BOX = (66, 464, 116, 32)
ESC_BOX = (296, 464, 140, 32)
CANVAS_W, CANVAS_H = 450, 512


def _rect(x, y, w, h, tone, label, *, size=12.5, pulse=False):
    fill, stroke, text = TONES[tone]
    anim = ' class="tl-pulse"' if pulse else ""
    return f"""
  <g{anim}>
    <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="3"
          fill="{fill}" stroke="{stroke}" stroke-width="{2 if tone != 'idle' else 1}"/>
    <text x="{x + w / 2}" y="{y + h / 2 + 4.2}" text-anchor="middle"
          font-family={MONO!r} font-size="{size}" font-weight="500" fill="{text}">{label}</text>
  </g>"""


def _tone_of(node, status):
    return status.get(node, "idle")


def diagram(status: dict, *, firing: bool = False) -> str:
    """Render the triage graph with priority routing and retry escalation."""
    parts = []

    def edge(path, active=False, color=TEAL, dashed=False):
        stroke = color if active else HAIRLINE
        marker = (
            "ah-clay" if active and color == CLAY
            else "ah-teal" if active
            else "ah-grey"
        )
        dash = ' stroke-dasharray="3 4"' if dashed else ""
        parts.append(
            f'<path d="{path}" stroke="{stroke}" stroke-width="1.5" '
            f'fill="none"{dash} marker-end="url(#{marker})"/>'
        )

    def reached(node):
        return status.get(node, "idle") != "idle"

    # Distinguish the two possible escalation paths.
    high_escalation = (
        reached("escalate_to_human")
        and status.get("classify_priority") == "done"
        and status.get("critique", "idle") == "idle"
    )

    retry_escalation = (
        reached("escalate_to_human")
        and status.get("critique") == "done"
    )

    # Main vertical sequence: new_ticket -> intake -> triage -> classify_priority
    for (upper, _), (lower, _) in zip(MAIN[:4], MAIN[1:4]):
        edge(
            f'M {CENTER} {MAIN_Y[upper] + NODE_H} '
            f'V {MAIN_Y[lower] - 6}',
            reached(lower),
        )

    # Classification decision box
    px, py, pw, ph = PRIORITY_BOX
    edge(
        f'M {CENTER} {MAIN_Y["classify_priority"] + NODE_H} '
        f'V {py - 6}',
        reached("classify_priority"),
    )

    # Priority NORMAL -> draft_reply
    dx = COL_X + NODE_W / 2
    draft_y = MAIN_Y["draft_reply"]
    normal_path = (
        f'M {px + pw / 2} {py + ph} '
        f'V {draft_y - 6}'
    )
    edge(
        normal_path,
        reached("draft_reply"),
    )

    # Priority HIGH -> escalate_to_human
    ex, ey, ew, eh = ESC_BOX
    high_path = (
        f'M {px + pw} {py + ph / 2} '
        f'H {ex + ew / 2} '
        f'V {ey - 6}'
    )
    edge(high_path, high_escalation, CLAY)

    # draft_reply -> critique
    edge(
        f'M {CENTER} {MAIN_Y["draft_reply"] + NODE_H} '
        f'V {MAIN_Y["critique"] - 6}',
        reached("critique"),
    )

    # critique -> verdict
    vx, vy, vw, vh = VERDICT_BOX
    edge(
        f'M {CENTER} {MAIN_Y["critique"] + NODE_H} '
        f'V {vy - 6}',
        reached("verdict"),
    )

    # verdict PASS -> send_reply
    sx, sy, sw, sh = SEND_BOX
    send_on = reached("send_reply")
    edge(
        f'M {CENTER} {vy + vh} '
        f'V {sy - 55} '
        f'H {sx + sw / 2} '
        f'V {sy - 6}',
        send_on,
    )

    # verdict FAIL after MAX_ATTEMPTS -> escalate_to_human
    edge(
        f'M {vx + vw} {vy + vh / 2} '
        f'H {ex + ew / 2} '
        f'V {ey - 6}',
        retry_escalation,
        CLAY,
    )

    # Retry loop: verdict -> draft_reply
    dy = MAIN_Y["draft_reply"] + NODE_H / 2
    back = (
        f'M {vx} {vy + vh / 2} '
        f'H 76 Q 66 {vy + vh / 2} 66 {vy + vh / 2 - 10} '
        f'V {dy + 10} Q 66 {dy} 76 {dy} '
        f'H {COL_X - 7}'
    )

    if firing:
        parts.append(
            f'<path d="{back}" stroke="{TEAL}" stroke-width="2.6" '
            f'fill="none" stroke-dasharray="11 8" '
            f'class="tl-march" marker-end="url(#ah-teal)"/>'
        )
    else:
        edge(back, False, dashed=True)

    # Edge labels
    labels = [
        (
            px + pw + 45, py + 10,
            "high",
            CLAY if high_escalation else INK_SOFT,
        ),
        (
            CENTER + 12, draft_y - 10,
            "normal",
            TEAL if reached("draft_reply") else INK_SOFT,
        ),
        (
            sx + sw / 2 - 7, sy - 54,
            "pass",
            TEAL if send_on else INK_SOFT,
        ),
        (
            ex + ew / 2 - 70, ey - 30,
            "fail = 3",
            CLAY if retry_escalation else INK_SOFT,
        ),
    ]

    for x, y, label, color in labels:
        parts.append(
            f'<text x="{x}" y="{y}" font-family={MONO!r} '
            f'font-size="9.5" fill="{color}">{label}</text>'
        )

    lab_col = TEAL if firing else INK_SOFT
    parts.append(
        f'<text transform="rotate(-90 44 {(vy + dy) / 2})" '
        f'x="44" y="{(vy + dy) / 2}" '
        f'text-anchor="middle" font-family={MONO!r} '
        f'font-size="10" fill="{lab_col}">'
        f'fail &#183; attempts &lt; 3</text>'
    )

    # Main nodes
    for node, y in MAIN:
        tone = _tone_of(node, status)
        parts.append(
            _rect(
                COL_X, y, NODE_W, NODE_H,
                tone, node, pulse=(tone == "active")
            )
        )

    # Decision boxes and terminal nodes
    parts.append(
        _rect(
            px, py, pw, ph,
            _tone_of("classify_priority", status),
            "priority?", size=11.5
        )
    )

    parts.append(
        _rect(
            vx, vy, vw, vh,
            _tone_of("verdict", status),
            "verdict?", size=11.5
        )
    )

    parts.append(
        _rect(
            sx, sy, sw, sh,
            _tone_of("send_reply", status),
            "send_reply", size=11
        )
    )

    parts.append(
        _rect(
            ex, ey, ew, eh,
            _tone_of("escalate_to_human", status),
            "escalate", size=11
        )
    )

    # Arrow markers
    defs = "".join(
        f'<marker id="ah-{name}" viewBox="0 0 8 8" '
        f'refX="6" refY="4" markerWidth="5.5" '
        f'markerHeight="5.5" orient="auto">'
        f'<path d="M 0 1 L 7 4 L 0 7 z" fill="{col}"/>'
        f'</marker>'
        for name, col in (
            ("grey", HAIRLINE),
            ("teal", TEAL),
            ("clay", CLAY),
        )
    )

    return f"""
<style>
@keyframes tl-march {{
    to {{ stroke-dashoffset: -19; }}
}}
@keyframes tl-breathe {{
    0%,100% {{ opacity: 1; }}
    50% {{ opacity: 0.5; }}
}}
.tl-march {{
    animation: tl-march 0.85s linear infinite;
}}
.tl-pulse {{
    animation: tl-breathe 1.3s ease-in-out infinite;
}}
</style>
<svg viewBox="0 0 {CANVAS_W} {CANVAS_H}"
     width="100%"
     style="display:block;overflow:visible">
    <defs>{defs}</defs>
    {''.join(parts)}
</svg>"""


def lamps(attempts: int, outcome: str | None, max_attempts: int) -> str:
    """Three lamps that burn down as draft attempts are consumed."""
    cells = []
    for i in range(1, max_attempts + 1):
        cls = ""
        if i < attempts:
            cls = "burned"
        elif i == attempts:
            cls = {"sent": "passed", "escalated": "spent"}.get(outcome, "burned")
        cells.append(f'<div class="tl-lamp {cls}"></div>')

    if outcome == "sent":
        note = f"passed on attempt {attempts}"
    elif outcome == "escalated" and attempts == 0:
        note = "escalated immediately (high priority)"
    elif outcome == "escalated":
        note = f"all {max_attempts} used, none passed"
    elif attempts:
        note = f"attempt {attempts} of {max_attempts}"
    else:
        note = f"{max_attempts} attempts available"

    return (
        f'<div class="tl-lamps">{"".join(cells)}'
        f'<span class="tl-lamps-note">{note}</span></div>'
    )


def step_header(node: str, gloss: str, meta: str = "", tone: str = "") -> str:
    cls = f" {tone}" if tone else ""
    right = f'<span class="tl-step-meta">{meta}</span>' if meta else ""
    return (
        f'<div class="tl-step"><span class="tl-step-node{cls}">{node}</span>'
        f'<span class="tl-step-gloss">{gloss}</span>{right}</div>'
    )
