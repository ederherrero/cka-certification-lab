"""CKA Lab — FastAPI backend."""

import asyncio
import importlib.util
import json
import os
import sys
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent
SCENARIOS_DIR = ROOT / "scenarios"
PROGRESS_FILE = Path(os.getenv("PROGRESS_FILE", "/var/lib/cka-lab/progress.json"))

sys.path.insert(0, str(ROOT))

app = FastAPI(title="CKA Lab")

# ---------------------------------------------------------------------------
# Carregamento de cenários
# ---------------------------------------------------------------------------

_SCENARIO_CACHE: list = []


def _load_scenarios() -> list:
    global _SCENARIO_CACHE
    if _SCENARIO_CACHE:
        return _SCENARIO_CACHE
    mods = []
    for path in sorted(SCENARIOS_DIR.glob("s??_*.py")):
        spec = importlib.util.spec_from_file_location(path.stem, path)
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
            mods.append(mod)
        except Exception as exc:
            print(f"[warn] Erro ao carregar {path.name}: {exc}")
    _SCENARIO_CACHE = mods
    return mods


def _find_scenario(sid: str):
    for mod in _load_scenarios():
        mid = mod.METADATA["id"]
        num = mid.split("-")[0]
        if mid == sid or num == sid.zfill(2):
            return mod
    return None


# ---------------------------------------------------------------------------
# Progresso
# ---------------------------------------------------------------------------

def _load_progress() -> dict:
    if PROGRESS_FILE.exists():
        try:
            return json.loads(PROGRESS_FILE.read_text())
        except Exception:
            pass
    return {}


def _save_progress(scenario_id: str, status: str) -> None:
    p = _load_progress()
    p[scenario_id] = status
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROGRESS_FILE.write_text(json.dumps(p, indent=2))


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------

_CAT_ORDER = ["Troubleshooting", "Architecture", "Networking", "Workloads", "Storage"]


@app.get("/api/scenarios")
def list_scenarios():
    progress = _load_progress()
    result = []
    for mod in _load_scenarios():
        m = mod.METADATA
        result.append({
            "id":         m["id"],
            "title":      m["title"],
            "category":   m.get("category", ""),
            "difficulty": m.get("difficulty", ""),
            "lab_ref":    m.get("lab_ref", ""),
            "status":     progress.get(m["id"], "idle"),
        })
    return {"scenarios": result, "category_order": _CAT_ORDER}


@app.get("/api/scenarios/{scenario_id}")
def get_scenario(scenario_id: str):
    mod = _find_scenario(scenario_id)
    if not mod:
        return {"error": f"Cenário '{scenario_id}' não encontrado."}, 404
    progress = _load_progress()
    m = mod.METADATA
    return {
        "id":          m["id"],
        "title":       m["title"],
        "category":    m.get("category", ""),
        "difficulty":  m.get("difficulty", ""),
        "description": mod.DESCRIPTION,
        "hint":        mod.HINT,
        "status":      progress.get(m["id"], "idle"),
    }


@app.get("/api/progress")
def get_progress():
    progress = _load_progress()
    mods = _load_scenarios()
    verified = sum(1 for m in mods if progress.get(m.METADATA["id"]) == "verified")
    return {
        "total":    len(mods),
        "verified": verified,
        "progress": progress,
    }


@app.delete("/api/progress")
def reset_all_progress():
    _save_progress.__globals__  # dummy
    if PROGRESS_FILE.exists():
        PROGRESS_FILE.write_text("{}")
    return {"ok": True}


# ---------------------------------------------------------------------------
# WebSocket — execução de ações com streaming
# ---------------------------------------------------------------------------

@app.websocket("/ws/{scenario_id}/{action}")
async def scenario_ws(websocket: WebSocket, scenario_id: str, action: str):
    await websocket.accept()

    mod = _find_scenario(scenario_id)
    if not mod:
        await websocket.send_json({"type": "error", "msg": f"Cenário '{scenario_id}' não encontrado."})
        await websocket.close()
        return

    if action not in ("deploy", "verify", "reset", "hint"):
        await websocket.send_json({"type": "error", "msg": f"Ação '{action}' inválida."})
        await websocket.close()
        return

    m = mod.METADATA

    if action == "hint":
        await websocket.send_json({"type": "hint", "msg": mod.HINT})
        await websocket.close()
        return

    await websocket.send_json({"type": "info", "msg": f"Executando {action} para [{m['id']}]..."})

    fn = {"deploy": mod.deploy, "verify": mod.verify, "reset": mod.reset}[action]

    loop = asyncio.get_event_loop()
    try:
        success, msg = await loop.run_in_executor(None, fn)
    except Exception as exc:
        await websocket.send_json({"type": "error", "msg": f"Erro inesperado: {exc}"})
        await websocket.close()
        return

    if action == "deploy" and success:
        _save_progress(m["id"], "deployed")
        await websocket.send_json({"type": "description", "msg": mod.DESCRIPTION})

    elif action == "verify":
        status = "verified" if success else "deployed"
        _save_progress(m["id"], status)

    elif action == "reset" and success:
        _save_progress(m["id"], "idle")

    result_type = "ok" if success else "error"
    await websocket.send_json({"type": result_type, "msg": msg, "success": success})
    await websocket.send_json({"type": "done", "action": action, "success": success})

    try:
        await websocket.close()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Static files + SPA fallback
# ---------------------------------------------------------------------------

STATIC_DIR = ROOT / "static"

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def index():
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/{full_path:path}")
def spa_fallback(full_path: str):
    return FileResponse(str(STATIC_DIR / "index.html"))
