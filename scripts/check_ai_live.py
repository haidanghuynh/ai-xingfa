"""Kiểm tra AI sống: liệt kê model Gemini + gọi /api/extract với 1 ảnh nhỏ (dev tool)."""
from __future__ import annotations

import base64
import io
import json
import os
import sys

import httpx
from PIL import Image

BASE = "http://127.0.0.1:8010"
KEY = os.environ.get("GEMINI_API_KEY", "").strip()
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if not KEY:
    raise SystemExit("Thiếu GEMINI_API_KEY")

models = httpx.get(
    "https://generativelanguage.googleapis.com/v1beta/models",
    params={"key": KEY},
    timeout=30,
)
if models.status_code >= 400:
    raise SystemExit(f"List models lỗi {models.status_code}: {models.text[:200]}")
names = [
    entry["name"].split("/")[-1]
    for entry in models.json().get("models", [])
    if "generateContent" in entry.get("supportedGenerationMethods", [])
]
print("models:", [name for name in names if "flash" in name][:8])

preferred = next(
    (name for name in ("gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash") if name in names),
    next((name for name in names if "flash" in name), names[0] if names else ""),
)
print("dùng model:", preferred)

image = Image.open("out/ANH-01/D1_banve.png")
image.thumbnail((900, 900))
buffer = io.BytesIO()
image.save(buffer, "PNG")
image_b64 = base64.b64encode(buffer.getvalue()).decode()
print("ảnh thử:", image.size, len(image_b64) // 1024, "KB base64")

response = httpx.post(
    f"{BASE}/api/extract",
    json={"image_base64": image_b64, "provider": "gemini", "model": preferred},
    timeout=120,
)
print("status:", response.status_code)
body = response.json()
if response.status_code >= 400:
    print("lỗi:", json.dumps(body, ensure_ascii=False)[:600])
    raise SystemExit(1)
print("provider/model:", body["provider"], body["model"])
print("warnings:", body["warnings"])
print("items:", json.dumps(body["items"], ensure_ascii=False, indent=1)[:1800])
print("log:", body.get("log", ""))
