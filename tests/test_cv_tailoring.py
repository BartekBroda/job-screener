import pytest


def test_cv_tailoring_column_exists(app):
    from database import get_conn
    with get_conn() as conn:
        cols = {r['name'] for r in conn.execute("PRAGMA table_info(jobs)").fetchall()}
    assert 'cv_tailoring' in cols


def test_save_and_get_cv_tailoring(logged_in_client, sample_job_id):
    from database import save_cv_tailoring, get_cv_tailoring, get_user
    user = get_user("testuser")
    content = "## What to emphasise\n- Leadership experience"
    result = save_cv_tailoring(sample_job_id, user["id"], content)
    assert result is True
    retrieved = get_cv_tailoring(sample_job_id, user["id"])
    assert retrieved == content


def test_get_returns_none_when_empty(logged_in_client, sample_job_id):
    from database import get_cv_tailoring, get_user
    user = get_user("testuser")
    result = get_cv_tailoring(sample_job_id, user["id"])
    assert result is None


def test_save_returns_false_for_wrong_user(logged_in_client, sample_job_id):
    from database import save_cv_tailoring
    result = save_cv_tailoring(sample_job_id, 99999, "content")
    assert result is False


def test_save_overwrites_existing(logged_in_client, sample_job_id):
    from database import save_cv_tailoring, get_cv_tailoring, get_user
    user = get_user("testuser")
    save_cv_tailoring(sample_job_id, user["id"], "first version")
    save_cv_tailoring(sample_job_id, user["id"], "second version")
    assert get_cv_tailoring(sample_job_id, user["id"]) == "second version"


def test_cv_tailoring_analyzer_truncates_inputs():
    from analyzer import cv_tailoring as _tailor
    import unittest.mock as mock

    long_cv = "x" * 5000
    long_jd = "y" * 6000

    captured = {}

    def fake_urlopen(req, timeout=None):
        import json
        body = json.loads(req.data.decode())
        captured['payload'] = body
        response_data = json.dumps({
            "content": [{"type": "text", "text": "## What to emphasise\n- Leadership"}]
        }).encode()
        mock_resp = mock.MagicMock()
        mock_resp.read.return_value = response_data
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = mock.MagicMock(return_value=False)
        return mock_resp

    with mock.patch('urllib.request.urlopen', fake_urlopen):
        result = _tailor(
            user={"cv": long_cv},
            job_source=long_jd,
            company="Acme",
            role="PM",
            api_key="test-key",
        )

    user_msg = captured['payload']['messages'][0]['content']
    assert "x" * 3001 not in user_msg, "CV was not truncated to 3000 chars"
    assert "y" * 4001 not in user_msg, "JD was not truncated to 4000 chars"
    assert captured['payload']['max_tokens'] == 1500
    assert 'thinking' not in captured['payload']
    assert "##" in result


def test_cv_tailoring_endpoint_requires_login(client, sample_job_id):
    resp = client.post(f"/job/{sample_job_id}/cv_tailoring")
    assert resp.status_code in (302, 401)


def test_cv_tailoring_endpoint_404_for_wrong_user(logged_in_client, app):
    resp = logged_in_client.post("/job/99999/cv_tailoring")
    assert resp.status_code == 404


def test_cv_tailoring_endpoint_400_for_ineligible_verdict(logged_in_client, app):
    from database import get_conn, get_user
    user = get_user("testuser")
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO jobs (user_id, company, role, verdict, verdict_confirmed,
               analyzed_at, source_full)
               VALUES (?, 'Corp', 'Role', 'rejected', 1, date('now'), 'some text')""",
            (user["id"],),
        )
        job_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    resp = logged_in_client.post(f"/job/{job_id}/cv_tailoring")
    assert resp.status_code == 400
    assert b"not available" in resp.data.lower()


def test_cv_tailoring_endpoint_400_when_no_source_text(logged_in_client, app):
    from database import get_conn, get_user
    user = get_user("testuser")
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO jobs (user_id, company, role, verdict, verdict_confirmed,
               analyzed_at, source_full)
               VALUES (?, 'Corp', 'Role', 'worth_considering', 1, date('now'), NULL)""",
            (user["id"],),
        )
        job_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    resp = logged_in_client.post(f"/job/{job_id}/cv_tailoring")
    assert resp.status_code == 400
    assert b"no job description" in resp.data.lower()


def test_cv_tailoring_endpoint_success(logged_in_client, app):
    import unittest.mock as mock
    from database import get_conn, get_user
    user = get_user("testuser")
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO jobs (user_id, company, role, verdict, verdict_confirmed,
               analyzed_at, source_full)
               VALUES (?, 'Acme', 'PM', 'worth_considering', 1, date('now'), 'Full job description text here.')""",
            (user["id"],),
        )
        job_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    with mock.patch('app.cv_tailoring', return_value="## What to emphasise\n- Leadership.") as mock_tailor:
        resp = logged_in_client.post(f"/job/{job_id}/cv_tailoring")

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    assert "What to emphasise" in data["content"]
    mock_tailor.assert_called_once()


def test_cv_tailoring_stored_after_success(logged_in_client, app):
    import unittest.mock as mock
    from database import get_conn, get_user, get_cv_tailoring
    user = get_user("testuser")
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO jobs (user_id, company, role, verdict, verdict_confirmed,
               analyzed_at, source_full)
               VALUES (?, 'Acme', 'PM', 'worth_considering', 1, date('now'), 'Full text.')""",
            (user["id"],),
        )
        job_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    with mock.patch('app.cv_tailoring', return_value="## What to emphasise\n- Stored."):
        logged_in_client.post(f"/job/{job_id}/cv_tailoring")

    stored = get_cv_tailoring(job_id, user["id"])
    assert stored is not None
    assert "Stored." in stored
