"""Tìm FreeCAD và chạy script dựng 3D ở chế độ headless."""
from __future__ import annotations

import glob
import json
import os
import shutil
import subprocess
from pathlib import Path

from . import __version__

PATTERNS = [
    r"C:\Program Files\FreeCAD*\bin\FreeCADCmd.exe",
    r"C:\Program Files (x86)\FreeCAD*\bin\FreeCADCmd.exe",
    r"%LOCALAPPDATA%\Programs\FreeCAD*\bin\FreeCADCmd.exe",
    r"C:\FreeCAD*\bin\FreeCADCmd.exe",
    "/usr/lib/freecad*/bin/FreeCADCmd",
    "/usr/bin/FreeCADCmd",
    "/Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd",
]


def find_freecad() -> Path | None:
    env = os.environ.get("FREECAD_CMD", "").strip()
    if env and Path(env).exists():
        return Path(env)
    which = shutil.which("FreeCADCmd")
    if which:
        return Path(which)
    for pattern in PATTERNS:
        for hit in sorted(glob.glob(os.path.expandvars(pattern)), reverse=True):
            path = Path(hit)
            if path.exists():
                return path
    return None


def status() -> dict:
    path = find_freecad()
    return {
        "available": path is not None,
        "path": str(path) if path else "",
        "hint": (
            "Đã tìm thấy FreeCADCmd"
            if path
            else "Chưa cài FreeCAD. Tải FreeCAD 1.0 (freecad.org) hoặc: winget install FreeCAD.FreeCAD. "
            "Có thể đặt biến môi trường FREECAD_CMD trỏ tới FreeCADCmd.exe"
        ),
        "app_version": __version__,
    }


def run(plan_path: str | Path, out_dir: str | Path, timeout: int = 420) -> dict:
    executable = find_freecad()
    if executable is None:
        return {"ok": False, "error": "freecad_not_found", "message": status()["hint"]}
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    script = Path(__file__).with_name("freecad_build.py")
    env = os.environ.copy()
    env["XFCAD_PLAN"] = str(Path(plan_path).resolve())
    env["XFCAD_OUT"] = str(out_dir.resolve())
    cmd = [str(executable), str(script), "--plan", env["XFCAD_PLAN"], "--out", env["XFCAD_OUT"]]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=env,
            cwd=str(out_dir),
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout", "message": f"FreeCAD chạy quá {timeout}s"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": "spawn_failed", "message": str(exc)}

    report_path = out_dir / "freecad_report.json"
    report = None
    if report_path.exists():
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except Exception:
            report = None
    ok = proc.returncode == 0 and report is not None
    return {
        "ok": ok,
        "returncode": proc.returncode,
        "stdout": (proc.stdout or "")[-4000:],
        "stderr": (proc.stderr or "")[-4000:],
        "report": report,
        "executable": str(executable),
        "error": "" if ok else "freecad_failed",
    }
