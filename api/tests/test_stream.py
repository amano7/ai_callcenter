from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_websocket_accepts_connection_and_sends_connected():
    with client.websocket_connect("/stream/test-session-123") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "connected"
        assert msg["session_id"] == "test-session-123"
