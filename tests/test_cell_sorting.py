"""Deep coverage for Cell Sorting — the entry point of the whole
traceability chain (creates the cell identity every downstream station
depends on)."""


def _payload(cell_code, station_code="S1", **overrides):
    record = {
        "proline_code": "L1",
        "cell_code": cell_code,
        "station_code": station_code,
        "voltage": 3.6,
        "inter_res": 1.0,
        "nnr": 0.5,
        "pass_information": "OK",
        "usercode": "OP-TEST-1",
    }
    record.update(overrides)
    return {"productionDataList": [record]}


def test_success(client, api_keys, unique_code):
    cell_code = unique_code("CELL")
    r = client.post(
        "/stations/cell-sorting/data",
        json=_payload(cell_code),
        headers={"X-API-Key": api_keys["cell-sorting"]},
    )
    assert r.json() == {"rtnCode": 200, "msg": "Upload successful", "data": None}


def test_resubmit_same_key_overwrites_in_place(client, api_keys, unique_code):
    cell_code = unique_code("CELL")
    headers = {"X-API-Key": api_keys["cell-sorting"]}

    r1 = client.post("/stations/cell-sorting/data", json=_payload(cell_code, voltage=3.6), headers=headers)
    assert r1.json()["rtnCode"] == 200

    # Same cell_code + station_code (the idempotency key) but a different
    # voltage — must succeed as an overwrite, not a duplicate-key error.
    r2 = client.post("/stations/cell-sorting/data", json=_payload(cell_code, voltage=3.9), headers=headers)
    assert r2.json()["rtnCode"] == 200


def test_ng_judgment_triggers_rework_code(client, api_keys, unique_code):
    r = client.post(
        "/stations/cell-sorting/data",
        json=_payload(unique_code("CELL"), pass_information="NG"),
        headers={"X-API-Key": api_keys["cell-sorting"]},
    )
    body = r.json()
    assert body["rtnCode"] == 201
    assert "rework" in body["msg"].lower()


def test_permissive_judgment_input_normalized(client, api_keys, unique_code):
    # "fail" is not the documented OK/NG contract, but the permissive input
    # normalization (app/schemas/common.py) must still accept it and treat
    # it as NG -> rework.
    r = client.post(
        "/stations/cell-sorting/data",
        json=_payload(unique_code("CELL"), pass_information="fail"),
        headers={"X-API-Key": api_keys["cell-sorting"]},
    )
    assert r.json()["rtnCode"] == 201


def test_invalid_judgment_value_is_400(client, api_keys, unique_code):
    r = client.post(
        "/stations/cell-sorting/data",
        json=_payload(unique_code("CELL"), pass_information="maybe"),
        headers={"X-API-Key": api_keys["cell-sorting"]},
    )
    assert r.json()["rtnCode"] == 400


def test_negative_voltage_is_400(client, api_keys, unique_code):
    r = client.post(
        "/stations/cell-sorting/data",
        json=_payload(unique_code("CELL"), voltage=-1),
        headers={"X-API-Key": api_keys["cell-sorting"]},
    )
    assert r.json()["rtnCode"] == 400


def test_numeric_string_is_coerced(client, api_keys, unique_code):
    r = client.post(
        "/stations/cell-sorting/data",
        json=_payload(unique_code("CELL"), voltage="3.65"),
        headers={"X-API-Key": api_keys["cell-sorting"]},
    )
    assert r.json()["rtnCode"] == 200


def test_missing_required_field_is_400(client, api_keys, unique_code):
    payload = _payload(unique_code("CELL"))
    del payload["productionDataList"][0]["voltage"]
    r = client.post(
        "/stations/cell-sorting/data",
        json=payload,
        headers={"X-API-Key": api_keys["cell-sorting"]},
    )
    assert r.json()["rtnCode"] == 400
