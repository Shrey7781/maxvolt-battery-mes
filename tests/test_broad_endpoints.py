"""Broad, shallow coverage across all 11 station endpoints.

These checks exercise code paths shared by every station (X-API-Key
auth/scoping, the envelope, and productionDataList's min_length=1) rather
than station-specific business logic — none of them need any pre-existing
cell/module/pack data, so they're cheap to run for every station. Deep,
station-specific behavior (genealogy gates, upsert idempotency, judgment
values) lives in the dedicated test_*.py files for the stations where that
logic actually differs.
"""

import pytest

from tests.stations import STATIONS


@pytest.mark.parametrize("slug", STATIONS)
def test_missing_api_key_is_401(client, slug):
    r = client.post(f"/stations/{slug}/data", json={"productionDataList": []})
    assert r.status_code == 200  # envelope is always HTTP 200
    body = r.json()
    assert body["rtnCode"] == 401
    assert "X-API-Key" in body["msg"]


@pytest.mark.parametrize("slug", STATIONS)
def test_invalid_api_key_is_401(client, slug):
    r = client.post(
        f"/stations/{slug}/data",
        json={"productionDataList": []},
        headers={"X-API-Key": "not-a-real-key"},
    )
    assert r.json()["rtnCode"] == 401


@pytest.mark.parametrize("slug", STATIONS)
def test_wrong_station_key_is_403(client, api_keys, slug):
    other_slug = next(s for s in STATIONS if s != slug)
    r = client.post(
        f"/stations/{slug}/data",
        json={"productionDataList": []},
        headers={"X-API-Key": api_keys[other_slug]},
    )
    body = r.json()
    assert body["rtnCode"] == 403
    assert slug in body["msg"]


@pytest.mark.parametrize("slug", STATIONS)
def test_empty_batch_is_400(client, api_keys, slug):
    r = client.post(
        f"/stations/{slug}/data",
        json={"productionDataList": []},
        headers={"X-API-Key": api_keys[slug]},
    )
    assert r.json()["rtnCode"] == 400


@pytest.mark.parametrize("slug", STATIONS)
def test_malformed_json_is_400(client, api_keys, slug):
    r = client.post(
        f"/stations/{slug}/data",
        content="not json",
        headers={"X-API-Key": api_keys[slug], "Content-Type": "application/json"},
    )
    assert r.json()["rtnCode"] == 400


@pytest.mark.parametrize("slug", STATIONS)
def test_wrong_http_method_is_not_accepted(client, api_keys, slug):
    r = client.get(f"/stations/{slug}/data", headers={"X-API-Key": api_keys[slug]})
    assert r.status_code == 405
