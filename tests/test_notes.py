import pytest
import database
import pathlib


@pytest.fixture(autouse=True)
def _restore_db_path():
    original = database.DB_PATH
    yield
    database.DB_PATH = original


def _make_job(tmp_path, user_id):
    database.DB_PATH = pathlib.Path(tmp_path) / "notes_test.db"
    database.init_db()
    with database.get_conn() as conn:
        conn.execute(
            "INSERT INTO users (id, username, password_hash) VALUES (?, ?, ?)",
            (user_id, "u", "s:h"),
        )
    result = {
        "company_name": "Acme", "role_title": "PM", "verdict": "warning",
        "verdict_summary": "ok", "zero_list_hit": False, "zero_list_reason": None,
        "zero_list_evidence": None, "yellow_list_hit": False, "yellow_list_reason": None,
        "triage": {"status": "ok", "findings": "", "evidence": None,
                   "ghost_job_risk": "low", "ghost_job_signals": None, "role_archetype": "pm"},
        "layers": {
            "product":    {"status": "ok", "findings": "", "evidence": None,
                           "compensation_signal": "undisclosed", "compensation_note": None},
            "business":   {"status": "ok", "findings": "", "evidence": None,
                           "compensation_signal": "undisclosed", "compensation_note": None},
            "reputation": {"status": "ok", "findings": "", "evidence": None},
            "values":     {"status": "ok", "findings": "", "evidence": None},
        },
        "fit": {"status": "ok", "score": 3.0, "strengths": "", "gaps": "", "improve": ""},
        "gut_feeling": "",
    }
    database.save_job(user_id, result)
    with database.get_conn() as conn:
        return conn.execute("SELECT id FROM jobs WHERE user_id=?", (user_id,)).fetchone()["id"]


def test_notes_column_exists(tmp_path):
    import pathlib
    database.DB_PATH = pathlib.Path(tmp_path) / "nc.db"
    database.init_db()
    with database.get_conn() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(jobs)").fetchall()}
    assert "notes" in cols


def test_update_and_read_notes(tmp_path):
    job_id = _make_job(tmp_path, user_id=42)
    database.update_job_notes(job_id, 42, "Follow up next week")
    with database.get_conn() as conn:
        row = conn.execute("SELECT notes FROM jobs WHERE id=?", (job_id,)).fetchone()
    assert row["notes"] == "Follow up next week"


def test_update_notes_wrong_user(tmp_path):
    job_id = _make_job(tmp_path, user_id=43)
    result = database.update_job_notes(job_id, 99, "should not save")
    assert result is False
    with database.get_conn() as conn:
        row = conn.execute("SELECT notes FROM jobs WHERE id=?", (job_id,)).fetchone()
    assert not row["notes"]


def test_notes_endpoint(logged_in_client):
    import database as db
    with db.get_conn() as conn:
        user = conn.execute("SELECT id FROM users WHERE username='testuser'").fetchone()
    uid = user["id"]
    result = {
        "company_name": "NotesCo", "role_title": "Dev", "verdict": "warning",
        "verdict_summary": "x", "zero_list_hit": False, "zero_list_reason": None,
        "zero_list_evidence": None, "yellow_list_hit": False, "yellow_list_reason": None,
        "triage": {"status": "ok", "findings": "", "evidence": None,
                   "ghost_job_risk": "low", "ghost_job_signals": None, "role_archetype": "dev"},
        "layers": {
            "product":    {"status": "ok", "findings": "", "evidence": None,
                           "compensation_signal": "undisclosed", "compensation_note": None},
            "business":   {"status": "ok", "findings": "", "evidence": None,
                           "compensation_signal": "undisclosed", "compensation_note": None},
            "reputation": {"status": "ok", "findings": "", "evidence": None},
            "values":     {"status": "ok", "findings": "", "evidence": None},
        },
        "fit": {"status": "ok", "score": 3.0, "strengths": "", "gaps": "", "improve": ""},
        "gut_feeling": "",
    }
    db.save_job(uid, result)
    with db.get_conn() as conn:
        job_id = conn.execute(
            "SELECT id FROM jobs WHERE user_id=? ORDER BY id DESC LIMIT 1", (uid,)
        ).fetchone()["id"]

    resp = logged_in_client.post(f"/job/{job_id}/notes",
                                  data={"notes": "Interview scheduled"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True


def test_notes_endpoint_requires_login(client):
    resp = client.post("/job/1/notes", data={"notes": "x"})
    assert resp.status_code in (302, 401)
