"""Adapter AI vision: ảnh → JSON spec cửa (OpenAI / Gemini / OpenAI-compatible).

Nguyên tắc: AI chỉ nhận dạng (loại cửa, cánh, đố, hướng mở). Không suy ra mm,
không sinh CAD. Kết quả được chuẩn hoá + đánh dấu `needs_review` để người dùng duyệt.
"""
from __future__ import annotations

import datetime as dt
import json
import os
from typing import Any

from . import paths
from .models import ITEM_TYPE_LABELS

ITEM_TYPES = set(ITEM_TYPE_LABELS)
PANEL_OPEN = {"in", "out", "slide", "none"}
PANEL_DIR = {"left", "right", "up", "down", "none"}

DEFAULT_CONFIG: dict[str, Any] = {
    "provider": "openai",
    "temperature": 0.1,
    "timeout_seconds": 120,
    "providers": {
        "openai": {
            "label": "ChatGPT (OpenAI)",
            "base_url": "https://api.openai.com/v1",
            "model": "gpt-4o-mini",
            "api_key_env": "OPENAI_API_KEY",
            "vision": True,
        },
        "gemini": {
            "label": "Google Gemini",
            "base_url": "https://generativelanguage.googleapis.com/v1beta",
            "model": "gemini-2.0-flash",
            "api_key_env": "GEMINI_API_KEY",
            "vision": True,
        },
        "deepseek": {
            "label": "DeepSeek (text)",
            "base_url": "https://api.deepseek.com/v1",
            "model": "deepseek-chat",
            "api_key_env": "DEEPSEEK_API_KEY",
            "vision": False,
        },
        "local": {
            "label": "Local / OpenAI-compatible",
            "base_url": "http://127.0.0.1:11434/v1",
            "model": "qwen2.5-vl",
            "api_key_env": "LOCAL_AI_KEY",
            "vision": True,
        },
    },
}

FALLBACK_PROMPT = (
    "Bạn là kỹ sư cửa nhôm Xingfa. Đọc ảnh và trả về DUY NHẤT JSON dạng "
    '{"items":[...]} với các trường: tag, room, type, width_mm, height_mm, sill_mm, '
    "panels[{kind,open,dir,ratio}], transoms[{orientation,at_mm,band_above,band_below}], "
    "glass{key,thickness_mm}, confidence, needs_review. "
    "Không suy ra kích thước mm từ ảnh: nếu ảnh không ghi số đo, đặt width_mm/height_mm = null "
    'và thêm "kich_thuoc" vào needs_review.'
)


class AIConfigError(RuntimeError):
    """Thiếu khoá / provider không hỗ trợ."""


class AIProviderError(RuntimeError):
    """Nhà cung cấp trả lỗi hoặc trả dữ liệu không đọc được."""


def config_path() -> Path:
    return paths.config_dir() / "ai.json"


def load_config() -> dict[str, Any]:
    config = json.loads(json.dumps(DEFAULT_CONFIG))
    path = config_path()
    if not path.exists():
        return config
    try:
        saved = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return config
    for key, value in saved.items():
        if key == "providers" and isinstance(value, dict):
            for name, entry in value.items():
                if isinstance(entry, dict):
                    config["providers"].setdefault(name, {}).update(entry)
        else:
            config[key] = value
    return config


def provider_status() -> list[dict[str, Any]]:
    config = load_config()
    result: list[dict[str, Any]] = []
    for name, entry in config["providers"].items():
        key_env = str(entry.get("api_key_env", ""))
        result.append(
            {
                "name": name,
                "label": entry.get("label", name),
                "model": entry.get("model", ""),
                "vision": bool(entry.get("vision", True)),
                "available": bool(os.environ.get(key_env, "").strip()),
                "api_key_env": key_env,
            }
        )
    return result


def default_provider() -> str:
    config = load_config()
    name = str(config.get("provider") or "openai")
    if name in config["providers"]:
        return name
    return next(iter(config["providers"]), "openai")


def _resolve(provider: str | None, model: str | None) -> tuple[str, dict[str, Any], str, str]:
    config = load_config()
    name = (provider or default_provider()).strip().lower()
    entry = config["providers"].get(name)
    if entry is None:
        raise AIConfigError(f"Provider AI không hỗ trợ: {name}")
    chosen_model = (model or entry.get("model") or "").strip()
    if not chosen_model:
        raise AIConfigError(f"Provider {name} chưa có model")
    key_env = str(entry.get("api_key_env", ""))
    api_key = os.environ.get(key_env, "").strip()
    if not api_key:
        raise AIConfigError(
            f"Chưa cấu hình {key_env}. Đặt biến môi trường hoặc dùng cách dán JSON từ ChatGPT."
        )
    return name, entry, chosen_model, api_key


def _prompt_text() -> str:
    path = paths.data_dir() / "prompts" / "extract_windows.md"
    return path.read_text(encoding="utf-8") if path.exists() else FALLBACK_PROMPT


def _sniff_mime(image_base64: str) -> tuple[str, str]:
    if image_base64.startswith("data:"):
        header, _, payload = image_base64.partition(",")
        mime = header[5:].split(";")[0].strip() or "image/jpeg"
        return mime, payload
    markers = (
        ("/9j/", "image/jpeg"),
        ("iVBOR", "image/png"),
        ("R0lGOD", "image/gif"),
        ("UklGR", "image/webp"),
    )
    for marker, mime in markers:
        if image_base64.startswith(marker):
            return mime, image_base64
    return "image/jpeg", image_base64


def _post_json(
    url: str,
    body: dict[str, Any],
    headers: dict[str, str] | None = None,
    params: dict[str, str] | None = None,
    timeout: float = 120,
) -> dict[str, Any]:
    """Lớp gọi HTTP duy nhất — test có thể monkeypatch hàm này."""
    import httpx

    response = httpx.post(url, json=body, headers=headers or {}, params=params or {}, timeout=timeout)
    if response.status_code >= 400:
        raise AIProviderError(f"AI trả lỗi {response.status_code}: {response.text[:300]}")
    try:
        return response.json()
    except ValueError as exc:
        raise AIProviderError("AI trả về dữ liệu không phải JSON") from exc


def _call_openai(
    base_url: str,
    model: str,
    api_key: str,
    prompt: str,
    data_url: str,
    temperature: float,
    timeout: float,
) -> str:
    body = {
        "model": model,
        "temperature": temperature,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Trích xuất danh sách cửa trong ảnh theo JSON schema đã mô tả."},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            },
        ],
    }
    data = _post_json(
        f"{base_url.rstrip('/')}/chat/completions",
        body,
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=timeout,
    )
    try:
        return str(data["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError) as exc:
        raise AIProviderError("Không đọc được nội dung trả về của OpenAI") from exc


def _call_gemini(
    base_url: str,
    model: str,
    api_key: str,
    prompt: str,
    image_b64: str,
    mime: str,
    temperature: float,
    timeout: float,
) -> str:
    body = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": prompt + "\n\nChỉ trả về JSON đúng schema, không markdown."},
                    {"inline_data": {"mime_type": mime, "data": image_b64}},
                ],
            }
        ],
        "generationConfig": {"temperature": temperature, "responseMimeType": "application/json"},
    }
    data = _post_json(
        f"{base_url.rstrip('/')}/models/{model}:generateContent",
        body,
        params={"key": api_key},
        timeout=timeout,
    )
    try:
        parts = data["candidates"][0]["content"]["parts"]
        return "".join(str(part.get("text", "")) for part in parts)
    except (KeyError, IndexError, TypeError) as exc:
        raise AIProviderError("Không đọc được nội dung trả về của Gemini") from exc


def _parse_json(text: str) -> Any:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start >= 0 and end > start:
        cleaned = cleaned[start : end + 1]
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise AIProviderError(f"AI trả JSON lỗi: {exc}") from exc


def _number(value: Any, minimum: float = 0.0, maximum: float = 100_000.0) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number <= minimum or number > maximum:
        return None
    return number


def _tag_prefix(item_type: str) -> str:
    if item_type.startswith("door"):
        return "D"
    if item_type == "fixed":
        return "F"
    return "C"


def normalize_items(payload: Any) -> list[dict[str, Any]]:
    """Chuẩn hoá JSON AI → item an toàn: không tự bịa mm, đánh dấu needs_review."""
    raw_items = payload.get("items") if isinstance(payload, dict) else payload
    if raw_items is None and isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        raw_items = payload["data"].get("items")
    if not isinstance(raw_items, list):
        return []

    items: list[dict[str, Any]] = []
    used: set[str] = set()
    counters = {"C": 0, "D": 0, "F": 0}
    for raw in raw_items:
        if not isinstance(raw, dict):
            continue
        review = [str(entry) for entry in (raw.get("needs_review") or []) if str(entry).strip()]
        item_type = str(raw.get("type") or "").strip()
        if item_type not in ITEM_TYPES:
            item_type = "casement"
            review.append("loai_cua")

        width = _number(raw.get("width_mm"), 100, 20_000)
        height = _number(raw.get("height_mm"), 100, 20_000)
        if width is None or height is None:
            review.append("kich_thuoc")
        sill = _number(raw.get("sill_mm"), -1, 20_000)
        if sill is None:
            sill = 0.0 if item_type.startswith("door") else 900.0

        panels: list[dict[str, Any]] = []
        for entry in raw.get("panels") or []:
            if not isinstance(entry, dict):
                continue
            kind = "fixed" if entry.get("kind") == "fixed" else "sash"
            open_ = str(entry.get("open") or "").lower()
            if open_ not in PANEL_OPEN:
                open_ = "slide" if "sliding" in item_type else ("out" if kind == "sash" else "none")
            dir_ = str(entry.get("dir") or "").lower()
            if dir_ not in PANEL_DIR:
                dir_ = "none"
            ratio = _number(entry.get("ratio"), 0, 100) or 1.0
            panels.append({"kind": kind, "open": open_, "dir": dir_, "ratio": ratio})
        if not panels:
            review.append("chia_canh")

        transoms: list[dict[str, Any]] = []
        for entry in raw.get("transoms") or []:
            if not isinstance(entry, dict):
                continue
            above = entry.get("band_above")
            below = entry.get("band_below")
            transoms.append(
                {
                    "orientation": "v" if str(entry.get("orientation")).lower() == "v" else "h",
                    "at_mm": _number(entry.get("at_mm"), 0, 20_000),
                    "profile": str(entry.get("profile") or "transom"),
                    "band_above": above if above in {"sash", "fixed"} else None,
                    "band_below": below if below in {"sash", "fixed"} else None,
                }
            )

        confidence = _number(raw.get("confidence"), -1, 1.0001)
        if confidence is None:
            confidence = 0.5
        if confidence < 0.6:
            review.append("do_tin_cay_thap")

        tag = str(raw.get("tag") or "").strip()
        if not tag or tag in used:
            if tag:
                review.append("trung_ma")
            base = _tag_prefix(item_type)
            while True:
                counters[base] += 1
                candidate = f"{base}{counters[base]}"
                if candidate not in used:
                    tag = candidate
                    break
        used.add(tag)

        glass = raw.get("glass") if isinstance(raw.get("glass"), dict) else {}
        items.append(
            {
                "tag": tag,
                "room": str(raw.get("room") or ""),
                "qty": int(_number(raw.get("qty"), 0, 999) or 1),
                "type": item_type,
                "width_mm": width,
                "height_mm": height,
                "sill_mm": sill,
                "panels": panels,
                "transoms": transoms,
                "glass": {
                    "key": str(glass.get("key") or "cuong_luc_8"),
                    "thickness_mm": _number(glass.get("thickness_mm"), 0, 60) or 8.0,
                },
                "notes": str(raw.get("notes") or ""),
                "confidence": round(confidence, 2),
                "needs_review": sorted(set(review)),
                "source": "ai",
            }
        )
    return items


def _log_exchange(provider: str, model: str, prompt: str, response_text: str, items: list[dict]) -> str:
    try:
        folder = paths.out_dir() / "_ai"
        folder.mkdir(parents=True, exist_ok=True)
        stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        target = folder / f"{stamp}_{provider}.json"
        target.write_text(
            json.dumps(
                {
                    "provider": provider,
                    "model": model,
                    "created_at": dt.datetime.now().isoformat(timespec="seconds"),
                    "prompt": prompt,
                    "response": response_text,
                    "items": items,
                },
                ensure_ascii=False,
                indent=1,
            ),
            encoding="utf-8",
        )
        return str(target)
    except OSError:
        return ""


def extract(
    image_base64: str,
    provider: str | None = None,
    model: str | None = None,
    prompt: str | None = None,
) -> dict[str, Any]:
    """Gọi AI vision → item đã chuẩn hoá + cảnh báo + file log audit."""
    name, entry, chosen_model, api_key = _resolve(provider, model)
    if not entry.get("vision", True):
        raise AIConfigError(
            f"{entry.get('label', name)} không hỗ trợ đọc ảnh — chọn OpenAI hoặc Gemini"
        )
    config = load_config()
    system_prompt = (prompt or "").strip() or _prompt_text()
    mime, image_b64 = _sniff_mime(image_base64)
    if not image_b64:
        raise ValueError("Thiếu dữ liệu ảnh (image_base64)")
    timeout = float(config.get("timeout_seconds", 120))
    temperature = float(config.get("temperature", 0.1))
    base_url = str(entry.get("base_url", ""))
    if name == "gemini":
        text = _call_gemini(
            base_url, chosen_model, api_key, system_prompt, image_b64, mime, temperature, timeout
        )
    else:
        data_url = f"data:{mime};base64,{image_b64}"
        text = _call_openai(
            base_url, chosen_model, api_key, system_prompt, data_url, temperature, timeout
        )
    payload = _parse_json(text)
    items = normalize_items(payload)

    warnings: list[str] = []
    if not items:
        warnings.append("AI không tìm thấy cửa nào trong ảnh")
    missing = [item["tag"] for item in items if "kich_thuoc" in item["needs_review"]]
    if missing:
        warnings.append("Cần nhập kích thước: " + ", ".join(missing))
    return {
        "ok": True,
        "provider": name,
        "model": chosen_model,
        "items": items,
        "warnings": warnings,
        "log": _log_exchange(name, chosen_model, system_prompt, text, items),
        "raw": payload,
    }
