from __future__ import annotations

import json
from pathlib import Path
import urllib.request
from websockets.sync.client import connect


def _target():
    with urllib.request.urlopen("http://127.0.0.1:9227/json/list", timeout=2) as response:
        targets = json.load(response)
    for target in targets:
        if target.get("type") == "page" and "cxagent.crealitycloud." in target.get("url", ""):
            return target.get("webSocketDebuggerUrl")
    return None


def _evaluate(url, expression):
    with connect(url, open_timeout=3, max_size=16 * 1024 * 1024) as ws:
        ws.send(json.dumps({"id": 1, "method": "Runtime.evaluate", "params": {
            "expression": expression, "returnByValue": True, "awaitPromise": True
        }}))
        while True:
            result = json.loads(ws.recv(timeout=8))
            if result.get("id") == 1:
                return result.get("result", {}).get("result", {}).get("value")


def read_live_project():
    snapshot = Path(__file__).with_name("project_snapshot.json")
    if snapshot.exists():
        try:
            state = json.loads(snapshot.read_text(encoding="utf-8"))
            return _project_from_state(state)
        except Exception:
            pass
    url = _target()
    if not url:
        return {"connected": False, "project_loaded": False, "reason": "MCP não conectado"}
    # Ask the same native bridge used by the MCP tool for the current scene.
    expression = """new Promise((resolve,reject)=>{
      const previous=window.handleSlicerEvent; let done=false;
      const cleanup=()=>{if(window.handleSlicerEvent===handler)window.handleSlicerEvent=previous;clearTimeout(timer)};
      const handler=(msg)=>{if(msg&&msg.command==='slicer_state'&&!done){done=true;cleanup();resolve(msg.data?.state||msg.data)}};
      const timer=setTimeout(()=>{done=true;cleanup();reject(new Error('bridge timeout'))},7000);
      window.handleSlicerEvent=handler;
      try{window.wx.postMessage(JSON.stringify({command:'get_slicer_state',data:{}}))}catch(e){cleanup();reject(e)}
    })"""
    state = _evaluate(url, expression)
    if not state:
        return {"connected": True, "project_loaded": False, "reason": "Abra o painel de IA do MCP"}
    return _project_from_state(state)


def _project_from_state(state):
    plate = state.get("current_plate") or {}
    loaded = bool(state.get("has_model") and state.get("project_path"))
    colors = state.get("extruder_colors") or []
    grams = float(plate.get("filament_weight_g", 0) or 0)
    filaments = []
    if len(colors) == 1 and grams > 0:
        filaments = [{"color": colors[0], "grams": grams}]
    return {"connected": True, "project_loaded": loaded, "name": state.get("project_path", "").split("\\")[-1],
            "filaments": filaments, "colors": colors, "totalGrams": grams, "breakdownAvailable": bool(filaments),
            "raw": {"estimatedTime": plate.get("estimated_time_s"), "filename": plate.get("filename")}}

