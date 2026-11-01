from __future__ import annotations


def project_summary(live):
    if not live or not live.get("project_loaded"):
        return None
    requirements = {}
    for item in live.get("filaments", []):
        color = normalize_color(item.get("color", "unknown"))
        requirements[color] = round(requirements.get(color, 0.0) + float(item.get("grams", 0) or 0), 2)
    return {"name": live.get("name") or "Projeto atual", "requirements": requirements,
            "colors": [normalize_color(c) for c in (live.get("colors") or [])],
            "totalGrams": round(sum(requirements.values()), 2)}


def normalize_color(value):
    raw = str(value).lower().replace("#", "")
    if len(raw) >= 6:
        try:
            raw = raw[-6:]
            channels = [int(raw[i:i+2], 16) for i in (0, 2, 4)]
            avg = sum(channels) / 3
            if avg < 45: return "black"
            if avg > 210: return "white"
            if max(channels) - min(channels) < 30: return "gray"
        except ValueError:
            pass
    return str(value)


def compare_project_to_slots(project, slots):
    available = {}
    for slot in slots or []:
        color = slot.get("color")
        if color:
            available[color] = available.get(color, 0.0) + float(slot.get("grams", 0) or 0)
    shortages = []
    rows = []
    for color, needed in (project.get("requirements") or {}).items():
        left = round(available.get(color, 0.0), 2)
        needed = round(float(needed), 2)
        delta = round(left - needed, 2)
        rows.append({"color": color, "needed": needed, "available": left, "delta": delta})
        if delta < 0:
            shortages.append({"color": color, "missing": round(-delta, 2)})
    return {"canPrint": not shortages, "rows": rows, "shortages": shortages}

