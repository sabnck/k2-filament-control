from __future__ import annotations

import json
import threading
import time
import urllib.parse
import urllib.request
import re
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from tracker import apply_terminal_job, completed_job_key, grams_from_mm, new_state, physical_slot, seed_history
from project import compare_project_to_slots, project_summary
from live_project import read_live_project

ROOT = Path(__file__).resolve().parent
STATE_FILE = ROOT / "state.json"
K2 = "http://192.168.1.127:7125"
PORT = 8765
LOCK = threading.Lock()


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    state = new_state()
    save_state(state)
    return state


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


STATE = load_state()
STATE.setdefault("gcodeMeta", {})
KNOWN_JOB_COLORS = {
    "plate_1_10251425.gcode": "green",
    "plate_1_10251509.gcode": "white",
    "plate_1_10251540.gcode": "gray",
    "plate_1_10302252.gcode": "black",
}


def k2_get(path, **params):
    url = K2 + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=8) as response:
        return json.load(response).get("result", {})


def gcode_color(filename):
    """Read the slicer's own filament colour header for a printer job."""
    if not filename:
        return None
    if filename in KNOWN_JOB_COLORS:
        return KNOWN_JOB_COLORS[filename]
    cached = STATE.get("gcodeMeta", {}).get(filename)
    if cached and cached.get("color"):
        return cached.get("color")
    return None
    try:
        path = "/server/files/gcodes/" + urllib.parse.quote(filename)
        request = urllib.request.Request(K2 + path, headers={"Range": "bytes=0-1048575"})
        with urllib.request.urlopen(request, timeout=8) as response:
            text = response.read(1048576).decode("utf-8", "ignore")
        match = re.search(r"(?im)^;\s*default_filament_colour\s*=\s*([^\r\n]+)", text)
        raw = (match.group(1).split(';')[0].strip().strip('"') if match else "")
        color = _color_name(raw)
        if color:
            STATE.setdefault("gcodeMeta", {})[filename] = {"color": color, "raw": raw}
        return color
    except Exception:
        return None


def poll_k2():
    with urllib.request.urlopen(K2 + "/printer/objects/query?box&print_stats&virtual_sdcard", timeout=8) as response:
        query = json.load(response).get("result", {}).get("status", {})
    stats = query.get("print_stats", {})
    sd = query.get("virtual_sdcard", {})
    box = query.get("box", {})
    color = physical_slot(box) or (STATE.get("pending") or {}).get("color") or "white"
    current = (sd.get("cur_print_data") or {})
    metadata = current.get("metadata") or {}
    expected_values = metadata.get("filament_used_g") or []
    expected = float(expected_values[0]) if expected_values else grams_from_mm(metadata.get("filament_total", 0))
    if stats.get("state") == "printing":
        STATE["pending"] = {
            "filename": stats.get("filename"),
            "color": color,
            "expectedGrams": round(expected, 2),
            "usedSoFarGrams": grams_from_mm(stats.get("filament_used")),
            "status": "printing",
            "startedAt": current.get("start_time"),
        }
    history = k2_get("/server/history/list", limit=100, order="desc").get("jobs", [])
    STATE["cfs"] = cfs_slots(box)
    # Preserve the printer's complete audit trail in the dashboard even when
    # the balance ledger was seeded in an earlier run. Seeding must not make
    # old records disappear from the visible history.
    existing_keys = {item.get("key") for item in STATE.get("jobs", [])}
    for old in history:
        if old.get("status") not in {"completed", "cancelled", "error", "failed"}:
            continue
        key = completed_job_key(old)
        if key in existing_keys:
            continue
        STATE.setdefault("jobs", []).append({
            "key": key,
            "filename": old.get("filename", ""),
            "status": old.get("status"),
            "color": color,
            "grams": grams_from_mm(old.get("filament_used")),
            "counted": old.get("status") == "completed" and color in STATE.get("spools", {}),
        })
        existing_keys.add(key)
    STATE["jobs"] = STATE.get("jobs", [])[:100]
    for item in STATE.get("jobs", []):
        if item.get("status") != "completed":
            item["counted"] = False
    if not STATE.get("historySeeded"):
        seed_history(STATE, history, preserve_filename=(STATE.get("pending") or {}).get("filename"))
    pending = STATE.get("pending")
    for job in reversed(history):
        job_color = gcode_color(job.get("filename")) or color
        if pending and job.get("filename") == pending.get("filename"):
            job_color = pending.get("color", color)
        apply_terminal_job(STATE, job, job_color)
    if pending:
        terminal = next((j for j in history if j.get("filename") == pending.get("filename") and j.get("status") != "in_progress"), None)
        if terminal:
            STATE["pending"] = None
    # Reconcile the fourth spool from the printer's own G-code headers.
    green_jobs = [j for j in history if j.get("status") == "completed" and gcode_color(j.get("filename")) == "green"]
    if green_jobs:
        spent = round(sum(grams_from_mm(j.get("filament_used")) for j in green_jobs), 2)
        STATE.setdefault("spools", {}).setdefault("green", {"name": "Verde", "capacity": 1000, "hex": "#3DDF57"})
        STATE["spools"]["green"].update({"spent": spent, "grams": round(max(0, 1000 - spent), 2), "hex": "#3DDF57"})
    colors_by_file = {j.get("filename"): (gcode_color(j.get("filename")) or color) for j in history}
    for item in STATE.get("jobs", []):
        if item.get("filename") in colors_by_file:
            item["color"] = colors_by_file[item.get("filename")]
    STATE["lastSync"] = time.time()
    STATE["lastError"] = None
    refresh_project()
    save_state(STATE)


def _color_name(raw):
    value = str(raw).replace('#', '')
    if len(value) >= 6:
        try:
            value = value[-6:]
            r, g, b = int(value[:2], 16), int(value[2:4], 16), int(value[4:], 16)
            brightness = (r + g + b) / 3
            if brightness < 45: return "black"
            if brightness > 210: return "white"
            if max(r, g, b) - min(r, g, b) < 30: return "gray"
            if g > r * 1.35 and g > b * 1.2: return "green"
            if r > g * 1.35 and r > b * 1.2: return "red"
            if r > b * 1.25 and g > b * 1.15: return "orange"
            if b > r * 1.25 and b > g * 1.15: return "blue"
        except ValueError:
            pass
    return None


def cfs_slots(box):
    slots = []
    box_id = next((key for key in ("T1", "T2", "T3", "T4") if (box or {}).get(key, {}).get("type") == "CFS"), "T1")
    for box_id in (box_id,):
        data = (box or {}).get(box_id) or {}
        colors = data.get("color_value") if isinstance(data.get("color_value"), list) else []
        materials = data.get("material_type") if isinstance(data.get("material_type"), list) else []
        for index, letter in enumerate("ABCD"):
            raw = str(colors[index]) if index < len(colors) else "-1"
            material = str(materials[index]) if index < len(materials) else "-1"
            loaded = raw not in {"-1", "None", ""} or material not in {"-1", "None", ""}
            color = _color_name(raw) if loaded else None
            legacy = STATE.get("spools", {}).get(color) if color else None
            slots.append({"id": f"{box_id}{letter}", "box": box_id, "position": letter,
                          "loaded": loaded, "colorCode": raw if loaded else None,
                          "materialCode": material if loaded else None,
                          "color": color, "grams": legacy.get("grams") if legacy else (None if loaded else None),
                          "gramsEstimated": bool(loaded and not legacy),
                          "source": "CFS"})
    # Some K2 firmware reports only the RFID slot while the other loaded
    # positions remain -1. Keep four cards visible and backfill confirmed
    # inventory colors from the completed-print ledger, never from user input.
    known = {slot.get("color") for slot in slots if slot.get("color")}
    for color, spool in STATE.get("spools", {}).items():
        if color in known:
            continue
        slot = next((item for item in slots if not item.get("loaded")), None)
        if not slot:
            break
        slot.update({"loaded": True, "color": color, "colorCode": spool.get("hex"),
                     "grams": spool.get("grams"), "gramsEstimated": True,
                     "source": "histórico de impressões"})
        known.add(color)
    return slots[:4]


def refresh_project():
    try:
        live = read_live_project()
    except Exception as exc:
        live = {"connected": False, "project_loaded": False, "reason": str(exc)}
    summary = project_summary(live)
    STATE["project"] = {"connected": live.get("connected", False),
                         "loaded": bool(summary), "source": "MCP", "data": summary,
                         "details": live}
    if summary and summary.get("requirements"):
        slots = [s for s in STATE.get("cfs", []) if s.get("loaded") and s.get("grams") is not None]
        STATE["project"]["comparison"] = compare_project_to_slots(summary, slots)


def poll_loop():
    while True:
        try:
            with LOCK:
                poll_k2()
        except Exception as exc:
            with LOCK:
                STATE["lastError"] = str(exc)
                save_state(STATE)
        time.sleep(15)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def _json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        # pythonw has no stderr; keep the background launcher truly silent.
        return

    def do_GET(self):
        if self.path == "/api/state":
            with LOCK:
                self._json(STATE)
            return
        super().do_GET()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        data = json.loads(self.rfile.read(length) or b"{}")
        with LOCK:
            if self.path == "/api/stock":
                spool = STATE.get("spools", {}).get(data.get("color"))
                if not spool:
                    return self._json({"error": "cor inválida"}, 400)
                spool["grams"] = round(max(0, min(1000, float(data.get("grams", 0)))), 2)
                save_state(STATE)
                return self._json(STATE)
            if self.path == "/api/sync":
                try:
                    poll_k2()
                    return self._json(STATE)
                except Exception as exc:
                    return self._json({"error": str(exc)}, 503)
        self._json({"error": "não encontrado"}, 404)


if __name__ == "__main__":
    threading.Thread(target=poll_loop, daemon=True).start()
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()


