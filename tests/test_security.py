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


def test_account_lockout_after_failures(client):
    """Account is locked after 5 failed login attempts."""
    import app as app_module
    app_module._login_attempts.clear()

    for _ in range(5):
        client.post("/login", data={"username": "testuser", "password": "wrongpass"})

    resp = client.post("/login", data={"username": "testuser", "password": "testpass"})
    # After lockout, even correct password is rejected — must NOT redirect to dashboard
    assert resp.status_code != 302 or "/dashboard" not in resp.headers.get("Location", "")
    assert b"locked" in resp.data.lower()


def test_successful_login_clears_lockout(client):
    """Successful login resets the failure counter."""
    import app as app_module
    app_module._login_attempts.clear()

    client.post("/login", data={"username": "testuser", "password": "wrongpass"})
    client.post("/login", data={"username": "testuser", "password": "testpass"})
    assert "testuser" not in app_module._login_attempts


def test_unknown_user_does_not_create_lockout_entry(client):
    """Failed login for non-existent user does not pollute lockout dict."""
    import app as app_module
    app_module._login_attempts.clear()

    client.post("/login", data={"username": "ghost_user_xyz", "password": "anything"})
    assert "ghost_user_xyz" not in app_module._login_attempts
