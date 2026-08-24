"""Deep coverage for Cell-Module Code Binding — the first genealogy gate
(a cell must exist AND have passed Cell Sorting) and the first rebind
protection (a cell can't silently move to a different module)."""


def sort_cell(client, api_keys, cell_code, result="OK"):
    payload = {
        "productionDataList": [
            {
                "proline_code": "L1",
                "cell_code": cell_code,
                "station_code": "S1",
                "voltage": 3.6,
                "inter_res": 1.0,
                "nnr": 0.5,
                "pass_information": result,
                "usercode": "OP-TEST-1",
            }
        ]
    }
    r = client.post("/stations/cell-sorting/data", json=payload, headers={"X-API-Key": api_keys["cell-sorting"]})
    assert r.json()["rtnCode"] in (200, 201)


def bind(client, api_keys, cell_code, mod_code, cell_index=1):
    payload = {
        "productionDataList": [
            {
                "proline_code": "L1",
                "mod_code": mod_code,
                "cell_code": cell_code,
                "cell_index": cell_index,
                "station_code": "S1",
                "usercode": "OP-TEST-1",
            }
        ]
    }
    return client.post(
        "/stations/cell-module-binding/data", json=payload, headers={"X-API-Key": api_keys["cell-module-binding"]}
    )


def test_binding_unknown_cell_is_404(client, api_keys, unique_code):
    r = bind(client, api_keys, unique_code("CELL"), unique_code("MOD"))
    body = r.json()
    assert body["rtnCode"] == 404
    assert "cell-sorting" in body["msg"]


def test_binding_ng_sorted_cell_is_422(client, api_keys, unique_code):
    cell_code = unique_code("CELL")
    sort_cell(client, api_keys, cell_code, result="NG")

    r = bind(client, api_keys, cell_code, unique_code("MOD"))
    body = r.json()
    assert body["rtnCode"] == 422
    assert cell_code in body["msg"]


def test_binding_ok_sorted_cell_succeeds(client, api_keys, unique_code):
    cell_code = unique_code("CELL")
    sort_cell(client, api_keys, cell_code, result="OK")

    r = bind(client, api_keys, cell_code, unique_code("MOD"))
    assert r.json()["rtnCode"] == 200


def test_resubmitting_same_pair_is_idempotent(client, api_keys, unique_code):
    cell_code = unique_code("CELL")
    mod_code = unique_code("MOD")
    sort_cell(client, api_keys, cell_code, result="OK")

    r1 = bind(client, api_keys, cell_code, mod_code)
    assert r1.json()["rtnCode"] == 200

    r2 = bind(client, api_keys, cell_code, mod_code)
    assert r2.json()["rtnCode"] == 200


def test_rebinding_cell_to_different_module_is_409(client, api_keys, unique_code):
    cell_code = unique_code("CELL")
    mod_a = unique_code("MOD")
    mod_b = unique_code("MOD")
    sort_cell(client, api_keys, cell_code, result="OK")

    r1 = bind(client, api_keys, cell_code, mod_a)
    assert r1.json()["rtnCode"] == 200

    r2 = bind(client, api_keys, cell_code, mod_b)
    body = r2.json()
    assert body["rtnCode"] == 409
    assert mod_a in body["msg"]
