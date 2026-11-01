from __future__ import annotations

import copy

GRAMS_PER_MM_PLA = 0.0029826
SLOT_TO_COLOR = {"A": "gray", "B": "black", "C": "white"}


def grams_from_mm(length_mm):
    return round(max(0.0, float(length_mm or 0)) * GRAMS_PER_MM_PLA, 2)


def physical_slot(box_status):
    slot = str((box_status or {}).get("T1", {}).get("filament", "")).upper()
    return SLOT_TO_COLOR.get(slot)


def completed_job_key(job):
    return "|".join(str(job.get(key, "")) for key in ("filename", "start_time", "end_time"))


def apply_terminal_job(state, job, color):
    status = job.get("status")
    if status not in {"completed", "cancelled", "error", "failed"}:
        return False
    key = completed_job_key(job)
    if key in state.setdefault("processed", []):
        return False
    state["processed"].append(key)
    grams = grams_from_mm(job.get("filament_used"))
    counted = status == "completed" and color in state.get("spools", {})
    if counted:
        spool = state["spools"][color]
        spool["grams"] = round(max(0, float(spool.get("grams", 0)) - grams), 2)
        spool["spent"] = round(float(spool.get("spent", 0)) + grams, 2)
    state.setdefault("jobs", []).insert(0, {
        "key": key,
        "filename": job.get("filename", ""),
        "status": status,
        "color": color,
        "grams": grams,
        "counted": counted,
    })
    state["jobs"] = state["jobs"][:50]
    return True


def seed_history(state, jobs, preserve_filename=None):
    processed = state.setdefault("processed", [])
    for job in jobs:
        if (job.get("status") in {"completed", "cancelled", "error", "failed"}
                and job.get("filename") != preserve_filename):
            key = completed_job_key(job)
            if key not in processed:
                processed.append(key)
    state["historySeeded"] = True


def new_state():
    return {
        "spools": {
            "gray": {"name": "Cinza", "grams": 401.0, "capacity": 1000, "spent": 599.0, "hex": "#808080"},
            "black": {"name": "Preto", "grams": 148.0, "capacity": 1000, "spent": 852.0, "hex": "#171717"},
            "white": {"name": "Branco", "grams": 679.0, "capacity": 1000, "spent": 321.0, "hex": "#f4f2e9"},
        },
        "sealed": [{"name": "Cor por definir", "grams": 1000, "hex": "#d7d5cc"} for _ in range(7)],
        "processed": [],
        "jobs": [],
        "pending": None,
        "historySeeded": False,
        "lastError": None,
        "cfs": [],
        "project": {"connected": False, "loaded": False, "source": "MCP", "data": None},
    }

