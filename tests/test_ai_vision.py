"""Test adapter AI vision (OpenAI / Gemini) — không gọi mạng thật."""
from __future__ import annotations

import json

import pytest

from xingfacad import ai_vision


def _openai_payload(content: dict) -> dict:
    return {"choices": [{"message": {"content": json.dumps(content, ensure_ascii=False)}}]}


def _gemini_payload(content: dict) -> dict:
    return {"candidates": [{"content": {"parts": [{"text": json.dumps(content, ensure_ascii=False)}]}}]}


SAMPLE = {
    "items": [
        {
            "tag": "C1",
            "room": "Phòng khách",
            "type": "casement",
            "width_mm": None,
            "height_mm": None,
            "panels": [
                {"kind": "sash", "open": "out", "dir": "left", "ratio": 1},
                {"kind": "sash", "open": "out", "dir": "right", "ratio": 1},
            ],
            "transoms": [],
            "glass": {"key": "cuong_luc_8", "thickness_mm": 8},
            "confidence": 0.72,
            "needs_review": ["kich_thuoc"],
        },
        {
            "tag": "",
            "type": "door_swing",
            "width_mm": 1800,
            "height_mm": 2200,
            "panels": [{"kind": "sash", "open": "out", "dir": "left", "ratio": 1}],
            "confidence": 0.9,
        },
        {
            "tag": "C1",
            "type": "khong_hop_le",
            "width_mm": 50,
            "height_mm": 0,
            "panels": [],
            "confidence": 0.3,
        },
    ]
}


@pytest.fixture()
def sandbox_ai(sandbox, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    return sandbox


def test_openai_extract_normalizes_and_keeps_dimensions_empty(sandbox_ai, monkeypatch):
    calls: list[dict] = []

    def fake_post(url, body, headers=None, params=None, timeout=120):
        calls.append({"url": url, "body": body, "headers": headers or {}})
        return _openai_payload(SAMPLE)

    monkeypatch.setattr(ai_vision, "_post_json", fake_post)
    result = ai_vision.extract("data:image/png;base64,AAAA", provider="openai")

    assert result["provider"] == "openai"
    assert result["model"] == "gpt-4o-mini"
    assert len(result["items"]) == 3
    assert calls[0]["url"].endswith("/chat/completions")
    assert calls[0]["headers"]["Authorization"] == "Bearer test-key"
    assert calls[0]["body"]["messages"][1]["content"][1]["image_url"]["url"].startswith("data:image/png;base64,")

    first = result["items"][0]
    assert first["width_mm"] is None and first["height_mm"] is None
    assert "kich_thuoc" in first["needs_review"]
    assert first["sill_mm"] == 900  # cửa sổ mặc định cao độ bệ

    second = result["items"][1]
    assert second["tag"] == "D1"
    assert second["sill_mm"] == 0
    assert second["width_mm"] == 1800

    third = result["items"][2]
    assert third["type"] == "casement"
    assert "loai_cua" in third["needs_review"]
    assert "kich_thuoc" in third["needs_review"]
    assert "do_tin_cay_thap" in third["needs_review"]
    assert "trung_ma" in third["needs_review"]
    assert third["tag"] == "C2"  # trùng tag C1 → tự đổi sang C2
    assert result["warnings"]
    assert result["log"].endswith(".json")


def test_gemini_extract(sandbox_ai, monkeypatch):
    captured: dict = {}

    def fake_post(url, body, headers=None, params=None, timeout=120):
        captured.update({"url": url, "body": body, "params": params})
        return _gemini_payload({"items": [SAMPLE["items"][1]]})

    monkeypatch.setattr(ai_vision, "_post_json", fake_post)
    result = ai_vision.extract("iVBORw0KGgo=", provider="gemini", model="gemini-2.0-flash")

    assert result["provider"] == "gemini"
    assert captured["params"] == {"key": "test-key"}
    assert ":generateContent" in captured["url"]
    assert captured["body"]["contents"][0]["parts"][1]["inline_data"]["mime_type"] == "image/png"
    assert result["items"][0]["type"] == "door_swing"


def test_missing_key_raises_config_error(sandbox_ai, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ai_vision.AIConfigError):
        ai_vision.extract("AAAA", provider="openai")


def test_non_vision_provider_rejected(sandbox_ai, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "x")
    with pytest.raises(ai_vision.AIConfigError):
        ai_vision.extract("AAAA", provider="deepseek")


def test_provider_error_wrapped(sandbox_ai, monkeypatch):
    def fake_post(*_args, **_kwargs):
        raise ai_vision.AIProviderError("AI trả lỗi 401")

    monkeypatch.setattr(ai_vision, "_post_json", fake_post)
    with pytest.raises(ai_vision.AIProviderError):
        ai_vision.extract("AAAA", provider="openai")


def test_invalid_json_wrapped(sandbox_ai, monkeypatch):
    monkeypatch.setattr(
        ai_vision, "_post_json", lambda *a, **k: {"choices": [{"message": {"content": "không phải json"}}]}
    )
    with pytest.raises(ai_vision.AIProviderError):
        ai_vision.extract("AAAA", provider="openai")


def test_provider_status_reports_availability(sandbox_ai, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    names = {entry["name"]: entry for entry in ai_vision.provider_status()}
    assert names["openai"]["available"] is True
    assert names["gemini"]["available"] is False
    assert names["deepseek"]["vision"] is False


def test_normalize_accepts_extra_review_flags():
    items = ai_vision.normalize_items(
        {
            "items": [
                {
                    "tag": "D1",
                    "type": "door_swing",
                    "width_mm": 1800,
                    "height_mm": 2200,
                    "panels": [{"kind": "sash", "open": "out", "dir": "right", "ratio": 1}],
                    "confidence": 0.95,
                    "needs_review": ["huong_mo", "room", "sill_mm"],
                }
            ]
        }
    )
    assert items[0]["width_mm"] == 1800
    assert items[0]["sill_mm"] == 0
    assert {"huong_mo", "room", "sill_mm"} <= set(items[0]["needs_review"])
