"""Deep coverage for Module EOL Test + Module-Pack Code Bonding — the
second genealogy gate (a module must exist AND have a Module EOL Test
record with pass_information = OK), plus pack-slot uniqueness and the
second rebind protection (a module can't silently move to a different
pack)."""

from tests.test_cell_module_binding import bind, sort_cell


def eol_test(client, api_keys, mod_code, result="OK"):
    payload = {
        "productionDataList": [
            {
                "station_code": "S1",
                "mod_code": mod_code,
                "mod_V": 51.2,
                "mod_V_Result": result,
                "mod_R": 0.045,
                "mod_R_Result": result,
                "mod_IR": 500.0,
                "mod_IR_Result": result,
                "mod_DWV": 1000.0,
                "mod_DWV_Result": result,
                "pass_information": result,
                "usercode": "OP-TEST-1",
            }
        ]
    }
    r = client.post("/stations/module-eol-test/data", json=payload, headers={"X-API-Key": api_keys["module-eol-test"]})
    assert r.json()["rtnCode"] in (200, 201)


def pack_bind(client, api_keys, mod_code, pack_code, mod_index=1):
    payload = {
        "productionDataList": [
            {
                "proline_code": "L1",
                "mod_code": mod_code,
                "pack_code": pack_code,
                "mod_index": mod_index,
                "bms_code": "BMS-1",
                "station_code": "S1",
                "usercode": "OP-TEST-1",
            }
        ]
    }
    return client.post(
        "/stations/module-pack-binding/data", json=payload, headers={"X-API-Key": api_keys["module-pack-binding"]}
    )


def new_ok_module(client, api_keys, unique_code):
    """Cell sorted OK -> bound to a fresh module. Returns the mod_code."""
    cell_code = unique_code("CELL")
    mod_code = unique_code("MOD")
    sort_cell(client, api_keys, cell_code, result="OK")
    r = bind(client, api_keys, cell_code, mod_code)
    assert r.json()["rtnCode"] == 200
    return mod_code


def test_pack_binding_without_any_eol_record_is_422(client, api_keys, unique_code):
    mod_code = new_ok_module(client, api_keys, unique_code)
    r = pack_bind(client, api_keys, mod_code, unique_code("PACK"))
    body = r.json()
    assert body["rtnCode"] == 422
    assert "no module-eol-test record" in body["msg"]


def test_pack_binding_after_ng_eol_is_422(client, api_keys, unique_code):
    mod_code = new_ok_module(client, api_keys, unique_code)
    eol_test(client, api_keys, mod_code, result="NG")

    r = pack_bind(client, api_keys, mod_code, unique_code("PACK"))
    body = r.json()
    assert body["rtnCode"] == 422
    assert "NG" in body["msg"]


def test_pack_binding_after_ok_eol_succeeds(client, api_keys, unique_code):
    mod_code = new_ok_module(client, api_keys, unique_code)
    eol_test(client, api_keys, mod_code, result="OK")

    r = pack_bind(client, api_keys, mod_code, unique_code("PACK"))
    assert r.json()["rtnCode"] == 200


def test_resubmitting_same_module_slot_is_idempotent(client, api_keys, unique_code):
    mod_code = new_ok_module(client, api_keys, unique_code)
    eol_test(client, api_keys, mod_code, result="OK")
    pack_code = unique_code("PACK")

    r1 = pack_bind(client, api_keys, mod_code, pack_code, mod_index=1)
    assert r1.json()["rtnCode"] == 200

    r2 = pack_bind(client, api_keys, mod_code, pack_code, mod_index=1)
    assert r2.json()["rtnCode"] == 200


def test_different_module_claiming_same_slot_is_409(client, api_keys, unique_code):
    pack_code = unique_code("PACK")

    mod_a = new_ok_module(client, api_keys, unique_code)
    eol_test(client, api_keys, mod_a, result="OK")
    r1 = pack_bind(client, api_keys, mod_a, pack_code, mod_index=1)
    assert r1.json()["rtnCode"] == 200

    mod_b = new_ok_module(client, api_keys, unique_code)
    eol_test(client, api_keys, mod_b, result="OK")
    r2 = pack_bind(client, api_keys, mod_b, pack_code, mod_index=1)
    body = r2.json()
    assert body["rtnCode"] == 409
    assert mod_a in body["msg"]


def test_rebinding_module_to_different_pack_is_409(client, api_keys, unique_code):
    mod_code = new_ok_module(client, api_keys, unique_code)
    eol_test(client, api_keys, mod_code, result="OK")

    pack_a = unique_code("PACK")
    pack_b = unique_code("PACK")

    r1 = pack_bind(client, api_keys, mod_code, pack_a, mod_index=1)
    assert r1.json()["rtnCode"] == 200

    r2 = pack_bind(client, api_keys, mod_code, pack_b, mod_index=1)
    body = r2.json()
    assert body["rtnCode"] == 409
    assert pack_a in body["msg"]
