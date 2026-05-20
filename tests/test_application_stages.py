import pytest


def test_set_interview(logged_in_client, sample_job_id):
    resp = logged_in_client.post(f"/job/{sample_job_id}/status", data={"status": "interview"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True


def test_set_offer(logged_in_client, sample_job_id):
    resp = logged_in_client.post(f"/job/{sample_job_id}/status", data={"status": "offer"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True


def test_interview_reflected_in_partial(logged_in_client, sample_job_id):
    logged_in_client.post(f"/job/{sample_job_id}/status", data={"status": "interview"})
    resp = logged_in_client.get(f"/job/{sample_job_id}/partial")
    assert resp.status_code == 200
    assert b"Interview" in resp.data


def test_offer_reflected_in_partial(logged_in_client, sample_job_id):
    logged_in_client.post(f"/job/{sample_job_id}/status", data={"status": "offer"})
    resp = logged_in_client.get(f"/job/{sample_job_id}/partial")
    assert resp.status_code == 200
    assert b"Offer" in resp.data


def test_offer_date_shown(logged_in_client, sample_job_id):
    logged_in_client.post(f"/job/{sample_job_id}/status", data={"status": "offer"})
    resp = logged_in_client.get(f"/job/{sample_job_id}/partial")
    assert b"Offer:" in resp.data
