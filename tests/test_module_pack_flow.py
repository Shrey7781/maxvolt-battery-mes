"""Deep coverage for Module EOL Test, Liquid Cooling Plate Airtightness and
Module-Pack Code Bonding — the second genealogy gate (a module must exist
AND have a Module EOL Test record with pass_information = OK), the pack
identity now being created by liquid-cooling-airtightness rather than
module-pack-binding (vendor spec revision, 2026-10), plus pack-slot
uniqueness and the second rebind protection (a module can't silently move
to a different pack)."""

from sqlalchemy import select

from app.database import SessionLocal
from app.models.entities import Module, Pack
from app.models.pack import LiquidCoolingAirtightnessReading
from tests.test_cell_module_binding import bind, sort_cell


def liquid_cooling_record(pack_code, result="OK", leakage=0.8, cooled_code=None):
    """pack_code=None leaves the field out, as the device does on NG."""
    record = {
        "proline_code": "L1",
        "cooled_code": cooled_code or f"CP-{pack_code}",
        "chargetime": 12.0,
        "holdtime": 30.0,
        "testtime": 45.0,
        "pressure": 300.0,
        "leakage": leakage,
        "result": result,
        "station_code": "LC-01",
        "usercode": "OP-TEST-1",
    }
    if pack_code is not None:
        record["pack_code"] = pack_code
    return record


def post_liquid_cooling(client, api_keys, *records):
    return client.post(
        "/stations/liquid-cooling-airtightness/data",
        json={"productionDataList": list(records)},
        headers={"X-API-Key": api_keys["liquid-cooling-airtightness"]},
    )


def liquid_cooling(client, api_keys, pack_code, result="OK", leakage=0.8, cooled_code=None):
    return post_liquid_cooling(client, api_keys, liquid_cooling_record(pack_code, result, leakage, cooled_code))


def new_pack(client, api_keys, unique_code):
    """Registers a fresh pack identity via liquid-cooling-airtightness (the
    first pack station). Returns the pack_code."""
    pack_code = unique_code("PACK")
    assert liquid_cooling(client, api_keys, pack_code).json()["rtnCode"] == 200
    return pack_code


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


def test_liquid_cooling_needs_no_upstream_pack(client, api_keys, unique_code):
    # First pack station: a never-before-seen pack_code is accepted and
    # becomes the pack identity, instead of 404ing.
    r = liquid_cooling(client, api_keys, unique_code("PACK"))
    assert r.json() == {"rtnCode": 200, "msg": "Upload successful", "data": None}


def test_liquid_cooling_creates_pack_for_downstream_stations(client, api_keys, unique_code):
    pack_code = new_pack(client, api_keys, unique_code)
    payload = {
        "productionDataList": [
            {
                "proline_code": "L1",
                "pack_code": pack_code,
                "chargetime": 12.0,
                "holdtime": 30.0,
                "testtime": 45.0,
                "pressure": 150.0,
                "leakage": 0.2,
                "result": "OK",
                "station_code": "PAT-01",
                "usercode": "OP-TEST-1",
            }
        ]
    }
    r = client.post(
        "/stations/pack-airtightness/data", json=payload, headers={"X-API-Key": api_keys["pack-airtightness"]}
    )
    assert r.json()["rtnCode"] == 200


def test_liquid_cooling_ng_triggers_rework_code(client, api_keys, unique_code):
    r = liquid_cooling(client, api_keys, unique_code("PACK"), result="NG")
    assert r.json()["rtnCode"] == 201


def _plate_rows(cooled_code):
    with SessionLocal() as db:
        return db.execute(
            select(LiquidCoolingAirtightnessReading.pack_code, LiquidCoolingAirtightnessReading.result).where(
                LiquidCoolingAirtightnessReading.cooled_code == cooled_code
            )
        ).all()


def _pack_exists(pack_code):
    with SessionLocal() as db:
        return db.scalar(select(Pack.pack_code).where(Pack.pack_code == pack_code)) is not None


def test_liquid_cooling_ng_without_pack_code_is_recorded(client, api_keys, unique_code):
    # Vendor (2026-10-27): on NG the plate barcode is still uploaded, but no
    # pack_code is generated.
    plate = unique_code("CP")
    r = liquid_cooling(client, api_keys, None, result="NG", cooled_code=plate)
    assert r.json()["rtnCode"] == 201
    assert _plate_rows(plate) == [(None, "NG")]


def test_liquid_cooling_ng_with_empty_pack_code_is_recorded(client, api_keys, unique_code):
    plate = unique_code("CP")
    r = liquid_cooling(client, api_keys, "  ", result="NG", cooled_code=plate)
    assert r.json()["rtnCode"] == 201
    assert _plate_rows(plate) == [(None, "NG")]


def test_liquid_cooling_ok_without_pack_code_is_400(client, api_keys, unique_code):
    body = liquid_cooling(client, api_keys, None, result="OK", cooled_code=unique_code("CP")).json()
    assert body["rtnCode"] == 400
    assert "pack_code is required when result is OK" in body["msg"]


def test_liquid_cooling_accepts_1_and_0_as_result(client, api_keys, unique_code):
    # Vendor (2026-10-27): 1 = OK, 0 = NG.
    pack_code = unique_code("PACK")
    assert liquid_cooling(client, api_keys, pack_code, result=1).json()["rtnCode"] == 200
    plate = unique_code("CP")
    assert liquid_cooling(client, api_keys, None, result="0", cooled_code=plate).json()["rtnCode"] == 201
    assert _plate_rows(plate) == [(None, "NG")]


def test_liquid_cooling_ng_plate_retested_ok_gets_its_pack(client, api_keys, unique_code):
    plate, pack_code = unique_code("CP"), unique_code("PACK")
    assert liquid_cooling(client, api_keys, None, result="NG", cooled_code=plate).json()["rtnCode"] == 201
    assert liquid_cooling(client, api_keys, pack_code, result="OK", cooled_code=plate).json()["rtnCode"] == 200
    assert _plate_rows(plate) == [(pack_code, "OK")]
    assert _pack_exists(pack_code)


def test_liquid_cooling_ok_plate_retested_ng_keeps_pack_link(client, api_keys, unique_code):
    plate, pack_code = unique_code("CP"), unique_code("PACK")
    assert liquid_cooling(client, api_keys, pack_code, result="OK", cooled_code=plate).json()["rtnCode"] == 200
    assert liquid_cooling(client, api_keys, None, result="NG", cooled_code=plate).json()["rtnCode"] == 201
    assert _plate_rows(plate) == [(pack_code, "NG")]


def test_liquid_cooling_plate_moved_to_different_pack_is_409(client, api_keys, unique_code):
    plate = unique_code("CP")
    first, second = unique_code("PACK"), unique_code("PACK")
    assert liquid_cooling(client, api_keys, first, cooled_code=plate).json()["rtnCode"] == 200
    body = liquid_cooling(client, api_keys, second, cooled_code=plate).json()
    assert body["rtnCode"] == 409
    assert first in body["msg"]
    assert not _pack_exists(second)
    assert _plate_rows(plate) == [(first, "OK")]


def test_liquid_cooling_second_plate_on_same_pack_is_409(client, api_keys, unique_code):
    # One plate per pack.
    pack_code = unique_code("PACK")
    first, second = unique_code("CP"), unique_code("CP")
    assert liquid_cooling(client, api_keys, pack_code, cooled_code=first).json()["rtnCode"] == 200
    body = liquid_cooling(client, api_keys, pack_code, cooled_code=second).json()
    assert body["rtnCode"] == 409
    assert first in body["msg"]
    assert _plate_rows(second) == []
    assert _plate_rows(first) == [(pack_code, "OK")]


def test_liquid_cooling_two_plates_same_pack_in_one_batch_is_409(client, api_keys, unique_code):
    pack_code = unique_code("PACK")
    first, second = unique_code("CP"), unique_code("CP")
    body = post_liquid_cooling(
        client,
        api_keys,
        liquid_cooling_record(pack_code, cooled_code=first),
        liquid_cooling_record(pack_code, cooled_code=second),
    ).json()
    assert body["rtnCode"] == 409
    assert "in one batch" in body["msg"]
    assert not _pack_exists(pack_code)


def test_liquid_cooling_many_ng_plates_without_pack_code(client, api_keys, unique_code):
    # pack_code is unique, but NULLs don't collide.
    plates = [unique_code("CP") for _ in range(3)]
    r = post_liquid_cooling(client, api_keys, *(liquid_cooling_record(None, result="NG", cooled_code=p) for p in plates))
    assert r.json()["rtnCode"] == 201
    for plate in plates:
        assert _plate_rows(plate) == [(None, "NG")]


def test_liquid_cooling_batch_mixing_ok_and_ng_plates(client, api_keys, unique_code):
    ok_plate, ng_plate, pack_code = unique_code("CP"), unique_code("CP"), unique_code("PACK")
    r = post_liquid_cooling(
        client,
        api_keys,
        liquid_cooling_record(pack_code, cooled_code=ok_plate),
        liquid_cooling_record(None, result="NG", cooled_code=ng_plate),
    )
    assert r.json()["rtnCode"] == 201
    assert _plate_rows(ok_plate) == [(pack_code, "OK")]
    assert _plate_rows(ng_plate) == [(None, "NG")]


def test_liquid_cooling_batch_same_plate_last_record_wins(client, api_keys, unique_code):
    # NG then a passing retest of the same plate in one batch: only the OK
    # record is persisted, so the batch is a plain success.
    plate, pack_code = unique_code("CP"), unique_code("PACK")
    r = post_liquid_cooling(
        client,
        api_keys,
        liquid_cooling_record(None, result="NG", cooled_code=plate),
        liquid_cooling_record(pack_code, cooled_code=plate),
    )
    assert r.json()["rtnCode"] == 200
    assert _plate_rows(plate) == [(pack_code, "OK")]


def test_liquid_cooling_negative_leakage_accepted(client, api_keys, unique_code):
    r = liquid_cooling(client, api_keys, unique_code("PACK"), leakage=-0.5)
    assert r.json()["rtnCode"] == 200


def test_liquid_cooling_non_finite_leakage_is_400(client, api_keys, unique_code):
    r = liquid_cooling(client, api_keys, unique_code("PACK"), leakage="-inf")
    assert r.json()["rtnCode"] == 400


def test_pack_airtightness_negative_leakage_accepted(client, api_keys, unique_code):
    # Vendor's own example value from the revised spec.
    pack_code = new_pack(client, api_keys, unique_code)
    payload = {
        "productionDataList": [
            {
                "proline_code": "L1",
                "pack_code": pack_code,
                "chargetime": 12.0,
                "holdtime": 30.0,
                "testtime": 45.0,
                "pressure": 150.0,
                "leakage": -0.5,
                "result": "OK",
                "station_code": "PAT-01",
                "usercode": "OP-TEST-1",
            }
        ]
    }
    r = client.post(
        "/stations/pack-airtightness/data", json=payload, headers={"X-API-Key": api_keys["pack-airtightness"]}
    )
    assert r.json()["rtnCode"] == 200


def test_pack_binding_unknown_pack_is_404(client, api_keys, unique_code):
    # module-pack-binding no longer creates the pack — it must already have
    # been registered by liquid-cooling-airtightness.
    mod_code = new_ok_module(client, api_keys, unique_code)
    eol_test(client, api_keys, mod_code, result="OK")
    pack_code = unique_code("PACK")

    r = pack_bind(client, api_keys, mod_code, pack_code)
    body = r.json()
    assert body["rtnCode"] == 404
    assert pack_code in body["msg"]
    assert "liquid-cooling-airtightness" in body["msg"]


def test_pack_binding_without_any_eol_record_is_422(client, api_keys, unique_code):
    mod_code = new_ok_module(client, api_keys, unique_code)
    r = pack_bind(client, api_keys, mod_code, new_pack(client, api_keys, unique_code))
    body = r.json()
    assert body["rtnCode"] == 422
    assert "no module-eol-test record" in body["msg"]


def test_pack_binding_after_ng_eol_is_422(client, api_keys, unique_code):
    mod_code = new_ok_module(client, api_keys, unique_code)
    eol_test(client, api_keys, mod_code, result="NG")

    r = pack_bind(client, api_keys, mod_code, new_pack(client, api_keys, unique_code))
    body = r.json()
    assert body["rtnCode"] == 422
    assert "NG" in body["msg"]


def test_pack_binding_after_ok_eol_succeeds(client, api_keys, unique_code):
    mod_code = new_ok_module(client, api_keys, unique_code)
    eol_test(client, api_keys, mod_code, result="OK")

    r = pack_bind(client, api_keys, mod_code, new_pack(client, api_keys, unique_code))
    assert r.json()["rtnCode"] == 200


def test_pack_binding_to_pack_whose_plate_retested_ng_is_422(client, api_keys, unique_code):
    mod_code = new_ok_module(client, api_keys, unique_code)
    eol_test(client, api_keys, mod_code, result="OK")
    plate, pack_code = unique_code("CP"), unique_code("PACK")
    liquid_cooling(client, api_keys, pack_code, cooled_code=plate)
    assert liquid_cooling(client, api_keys, None, result="NG", cooled_code=plate).json()["rtnCode"] == 201

    body = pack_bind(client, api_keys, mod_code, pack_code).json()
    assert body["rtnCode"] == 422
    assert f"{pack_code} (liquid-cooling-airtightness result NG)" in body["msg"]


def test_pack_binding_after_plate_retested_ok_again_succeeds(client, api_keys, unique_code):
    mod_code = new_ok_module(client, api_keys, unique_code)
    eol_test(client, api_keys, mod_code, result="OK")
    plate, pack_code = unique_code("CP"), unique_code("PACK")
    liquid_cooling(client, api_keys, pack_code, cooled_code=plate)
    liquid_cooling(client, api_keys, None, result="NG", cooled_code=plate)
    assert liquid_cooling(client, api_keys, pack_code, cooled_code=plate).json()["rtnCode"] == 200

    assert pack_bind(client, api_keys, mod_code, pack_code).json()["rtnCode"] == 200


def test_pack_binding_to_pack_without_liquid_cooling_record_is_422(client, api_keys, unique_code):
    # A pack created before the station reorder, when module-pack-binding
    # still registered packs itself.
    mod_code = new_ok_module(client, api_keys, unique_code)
    eol_test(client, api_keys, mod_code, result="OK")
    pack_code = unique_code("PACK")
    with SessionLocal() as db:
        db.add(Pack(pack_code=pack_code, proline_code="L1", first_station_code="MPB-01"))
        db.commit()

    body = pack_bind(client, api_keys, mod_code, pack_code).json()
    assert body["rtnCode"] == 422
    assert "no liquid-cooling-airtightness record" in body["msg"]


def _module_eol_result(mod_code):
    with SessionLocal() as db:
        return db.scalar(select(Module.eol_pass_information).where(Module.mod_code == mod_code))


def test_cell_binding_retry_after_eol_keeps_eol_result(client, api_keys, unique_code):
    # Regression: a cell-module-binding resubmission for an already
    # EOL-tested module used to reset modules.eol_pass_information to NULL
    # (upsert_all overwrote columns the caller never supplied), so the module
    # was then rejected at module-pack-binding with 422 "no module-eol-test
    # record".
    cell_code = unique_code("CELL")
    mod_code = unique_code("MOD")
    sort_cell(client, api_keys, cell_code, result="OK")
    assert bind(client, api_keys, cell_code, mod_code).json()["rtnCode"] == 200
    eol_test(client, api_keys, mod_code, result="OK")

    assert bind(client, api_keys, cell_code, mod_code).json()["rtnCode"] == 200  # identical device retry
    assert _module_eol_result(mod_code) == "OK"

    r = pack_bind(client, api_keys, mod_code, new_pack(client, api_keys, unique_code))
    assert r.json()["rtnCode"] == 200


def test_binding_extra_cell_after_eol_keeps_eol_result(client, api_keys, unique_code):
    # Same bug, other trigger: a late binding record for another cell of a
    # module that has already passed EOL.
    mod_code = new_ok_module(client, api_keys, unique_code)
    eol_test(client, api_keys, mod_code, result="OK")

    late_cell = unique_code("CELL")
    sort_cell(client, api_keys, late_cell, result="OK")
    assert bind(client, api_keys, late_cell, mod_code, cell_index=2).json()["rtnCode"] == 200
    assert _module_eol_result(mod_code) == "OK"


def test_cell_binding_retry_after_ng_eol_keeps_ng_gate(client, api_keys, unique_code):
    # The fix must preserve an NG result too, not just OK — a retry must not
    # turn a failed module back into an untested one.
    cell_code = unique_code("CELL")
    mod_code = unique_code("MOD")
    sort_cell(client, api_keys, cell_code, result="OK")
    bind(client, api_keys, cell_code, mod_code)
    eol_test(client, api_keys, mod_code, result="NG")

    bind(client, api_keys, cell_code, mod_code)
    assert _module_eol_result(mod_code) == "NG"

    body = pack_bind(client, api_keys, mod_code, new_pack(client, api_keys, unique_code)).json()
    assert body["rtnCode"] == 422
    assert "module-eol-test result NG" in body["msg"]


def test_resubmitting_same_module_slot_is_idempotent(client, api_keys, unique_code):
    mod_code = new_ok_module(client, api_keys, unique_code)
    eol_test(client, api_keys, mod_code, result="OK")
    pack_code = new_pack(client, api_keys, unique_code)

    r1 = pack_bind(client, api_keys, mod_code, pack_code, mod_index=1)
    assert r1.json()["rtnCode"] == 200

    r2 = pack_bind(client, api_keys, mod_code, pack_code, mod_index=1)
    assert r2.json()["rtnCode"] == 200


def test_different_module_claiming_same_slot_is_409(client, api_keys, unique_code):
    pack_code = new_pack(client, api_keys, unique_code)

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

    pack_a = new_pack(client, api_keys, unique_code)
    pack_b = new_pack(client, api_keys, unique_code)

    r1 = pack_bind(client, api_keys, mod_code, pack_a, mod_index=1)
    assert r1.json()["rtnCode"] == 200

    r2 = pack_bind(client, api_keys, mod_code, pack_b, mod_index=1)
    body = r2.json()
    assert body["rtnCode"] == 409
    assert pack_a in body["msg"]
