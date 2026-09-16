import hashlib

from quant_brain.llm import ollama_client


def test_generate_uses_local_json_schema_temperature_zero_and_hashes(monkeypatch):
    captured = {}

    def fake_post(path, payload, host, timeout):
        captured.update(path=path, payload=payload, host=host, timeout=timeout)
        return {"response": '{"ok":true}', "total_duration": 123_000_000}

    monkeypatch.setattr(ollama_client, "_post", fake_post)
    schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}}
    response = ollama_client.generate("prompt", "qwen3:14b", format=schema, timeout=17)

    assert captured["path"] == "/api/generate"
    assert captured["payload"]["stream"] is False
    assert captured["payload"]["think"] is False
    assert captured["payload"]["format"] == schema
    assert captured["payload"]["options"]["temperature"] == 0.0
    assert captured["timeout"] == 17
    assert response.text == '{"ok":true}'
    assert response.model == "qwen3:14b"
    assert response.prompt_hash == hashlib.sha256(b"prompt").hexdigest()
    assert response.response_hash == hashlib.sha256(b'{"ok":true}').hexdigest()
    assert response.duration_seconds >= 0


def test_generate_never_contains_cloud_fallback(monkeypatch):
    def unavailable(*_args, **_kwargs):
        raise ollama_client.OllamaError("offline")

    monkeypatch.setattr(ollama_client, "_post", unavailable)
    try:
        ollama_client.generate("prompt", "qwen3:14b")
    except ollama_client.OllamaError as exc:
        assert str(exc) == "offline"
    else:
        raise AssertionError("local failure must propagate")
