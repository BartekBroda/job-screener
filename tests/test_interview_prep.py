import pytest


def test_interview_prep_column_exists(app):
    from database import get_conn
    with get_conn() as conn:
        cols = {r['name'] for r in conn.execute("PRAGMA table_info(jobs)").fetchall()}
    assert 'interview_prep' in cols


def test_save_and_get_interview_prep(logged_in_client, sample_job_id):
    from database import save_interview_prep, get_interview_prep, get_user
    user = get_user("testuser")
    content = "# Interview Prep\n\n## Company context\n- Bullet one"
    result = save_interview_prep(sample_job_id, user["id"], content)
    assert result is True
    retrieved = get_interview_prep(sample_job_id, user["id"])
    assert retrieved == content


def test_get_returns_none_when_empty(logged_in_client, sample_job_id):
    from database import get_interview_prep, get_user
    user = get_user("testuser")
    result = get_interview_prep(sample_job_id, user["id"])
    assert result is None


def test_save_returns_false_for_wrong_user(logged_in_client, sample_job_id):
    from database import save_interview_prep
    result = save_interview_prep(sample_job_id, 99999, "content")
    assert result is False


def test_save_overwrites_existing(logged_in_client, sample_job_id):
    from database import save_interview_prep, get_interview_prep, get_user
    user = get_user("testuser")
    save_interview_prep(sample_job_id, user["id"], "first version")
    save_interview_prep(sample_job_id, user["id"], "second version")
    assert get_interview_prep(sample_job_id, user["id"]) == "second version"
