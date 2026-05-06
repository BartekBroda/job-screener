import pytest
from database import create_analysis, update_analysis_status, get_analysis, init_db, get_conn


def test_create_analysis_returns_uuid(app):
    analysis_id = create_analysis(user_id=1, source_label="Senior PM · Figma")
    assert len(analysis_id) == 36
    assert analysis_id.count("-") == 4


def test_create_analysis_initial_status(app):
    analysis_id = create_analysis(user_id=1, source_label="Test label")
    row = get_analysis(analysis_id, user_id=1)
    assert row["status"] == "pending"
    assert row["source_label"] == "Test label"
    assert row["result_job_id"] is None
    assert row["error"] is None


def test_update_to_running(app):
    analysis_id = create_analysis(user_id=1, source_label="Test")
    update_analysis_status(analysis_id, "running")
    row = get_analysis(analysis_id, user_id=1)
    assert row["status"] == "running"
    assert row["finished_at"] is None


def test_update_to_done(app):
    analysis_id = create_analysis(user_id=1, source_label="Test")
    update_analysis_status(analysis_id, "done", result_job_id=99)
    row = get_analysis(analysis_id, user_id=1)
    assert row["status"] == "done"
    assert row["result_job_id"] == 99
    assert row["finished_at"] is not None


def test_update_to_error(app):
    analysis_id = create_analysis(user_id=1, source_label="Test")
    update_analysis_status(analysis_id, "error", error="API timeout")
    row = get_analysis(analysis_id, user_id=1)
    assert row["status"] == "error"
    assert row["error"] == "API timeout"
    assert row["finished_at"] is not None


def test_get_analysis_wrong_user_returns_none(app):
    analysis_id = create_analysis(user_id=1, source_label="Test")
    assert get_analysis(analysis_id, user_id=999) is None


def test_init_db_cleans_stuck_analyses(app):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO analyses (id, user_id, status, source_label, started_at) "
            "VALUES ('stuck-uuid', 1, 'running', 'stuck', datetime('now', '-10 minutes'))"
        )
    init_db()
    row = get_analysis("stuck-uuid", user_id=1)
    assert row["status"] == "error"
    assert row["error"] == "Server restarted"
