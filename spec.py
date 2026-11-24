"""The structured plugin specification the assistant extracts from the chat."""

TYPES = ("effect", "instrument", "midi_effect")


def _num(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate(spec) -> list[str]:
    """Problems that stop the build from starting. Empty list = the spec is usable."""
    if not isinstance(spec, dict):
        return ["a plugin specification"]
    problems = []
    if not str(spec.get("name") or "").strip():
        problems.append("a name for the plugin")
    if spec.get("type") not in TYPES:
        problems.append("whether it is an effect, an instrument or a MIDI effect")
    params = spec.get("parameters")
    if not isinstance(params, list) or not params:
        problems.append("at least one adjustable parameter")
        return problems
    for p in params:
        pname = str(p.get("name") or "").strip() if isinstance(p, dict) else ""
        if not pname:
            problems.append("a name for every parameter")
            continue
        lo, hi, default = p.get("min"), p.get("max"), p.get("default")
        if not (_num(lo) and _num(hi) and _num(default)):
            problems.append(f"the range and default value of '{pname}'")
        elif not lo <= default <= hi:
            problems.append(f"a default for '{pname}' inside its range {lo} to {hi}")
    return problems


def format_spec(spec) -> str:
    """The spec as plain text, for the chat and for the code-writing prompt."""
    if not isinstance(spec, dict) or not spec.get("name"):
        return ""
    lines = [f"Plugin specification: {spec['name']} ({str(spec.get('type') or '?').replace('_', ' ')})"]
    if spec.get("summary"):
        lines.append(str(spec["summary"]))
    params = [p for p in spec.get("parameters") or [] if isinstance(p, dict)]
    if params:
        lines.append("Parameters:")
        for p in params:
            unit = f" {p['unit']}" if p.get("unit") else ""
            rng = f"{p.get('min', '?')} to {p.get('max', '?')}{unit}, default {p.get('default', '?')}"
            lines.append(f"  - {p.get('name', '?')}: {rng}")
    for title, key in (("UI", "ui_elements"), ("Presets", "presets"), ("Not specified yet", "missing"), ("Assumed by me", "assumptions")):
        items = [str(i) for i in spec.get(key) or []]
        if items:
            lines.append(f"{title}: " + "; ".join(items))
    return "\n".join(lines)
