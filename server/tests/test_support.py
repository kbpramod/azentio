import io
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_support_status_endpoint():
    res = client.get("/api/v1/support/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "online"
    assert data["voice_support_enabled"] is True


def test_support_voice_upload_endpoint():
    fake_audio_bytes = b"RIFF....WAVEfmt ....dataFAKEAUDIOSTREAMCONTENT12345"
    files = {
        "audio_file": ("test_voice.webm", io.BytesIO(fake_audio_bytes), "audio/webm")
    }
    data = {
        "customer_name": "Test Customer",
        "account_number": "AZ-998877",
        "note": "Voice inquiry test",
    }

    res = client.post("/api/v1/support/voice", files=files, data=data)
    assert res.status_code == 200
    res_data = res.json()
    assert res_data["status"] == "received"
    assert res_data["type"] == "voice"
    assert "SUP-V-" in res_data["ticket_id"]
    assert res_data["filename"] == "test_voice.webm"
    assert res_data["size_bytes"] == len(fake_audio_bytes)


def test_support_text_endpoint():
    payload = {
        "message": "I would like to inquire about high-yield savings interest rates.",
        "customer_name": "Pramod User",
        "category": "General Inquiry",
    }
    res = client.post("/api/v1/support/text", json=payload)
    assert res.status_code == 200
    res_data = res.json()
    assert res_data["status"] == "received"
    assert res_data["type"] == "text"
    assert "SUP-T-" in res_data["ticket_id"]
