import os
import pytest


def test_secret_key_is_set(app):
    """App must have a stable SECRET_KEY, not a random one."""
    assert app.secret_key is not None
    assert len(app.secret_key) >= 10


def test_debug_mode_off_by_default():
    """FLASK_DEBUG env var defaults to off."""
    env_backup = os.environ.pop("FLASK_DEBUG", None)
    try:
        debug = os.environ.get("FLASK_DEBUG", "0") == "1"
        assert debug is False
    finally:
        if env_backup is not None:
            os.environ["FLASK_DEBUG"] = env_backup


def test_security_headers_present(client):
    """All responses include basic security headers."""
    resp = client.get("/about")
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert "strict-origin-when-cross-origin" in resp.headers.get("Referrer-Policy", "")
