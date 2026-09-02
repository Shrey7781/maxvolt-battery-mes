"""Work Order — this project's own addition (not in the vendor's original
interface spec), pushed manually from one or two station devices whose
identity isn't finalized yet. Deliberately independent of the cell/module/
pack genealogy tables: no ensure_packs_exist gate runs against pack_barcode.

The batch-summary tests below build a real cell -> module -> pack genealogy
chain (reusing helpers from test_cell_module_binding / test_module_pack_flow)
so pack_barcode lines up with an actual pack_code and its NG signals."""

from tests.test_cell_module_binding import bind, sort_cell
from tests.test_module_pack_flow import eol_test, new_ok_module, pack_bind


def pack_eol_test(client, api_keys, pack_code, result="OK"):
    payload = {
        "productionDataList": [
            {
                "station_code": "S1",
                "pack_code": pack_code,
                "test_file_data": {"test_items": [{"desc": "OCV", "value": "51.2", "unit": "V"}]},
                "pass_information": result,
                "usercode": "OP-TEST-1",
            }
        ]
    }
    r = client.post("/stations/pack-eol-test/data", json=payload, headers={"X-API-Key": api_keys["pack-eol-test"]})
    assert r.json()["rtnCode"] in (200, 201)


def new_ok_pack(client, api_keys, unique_code):
    """Cell OK -> module OK (EOL) -> bound to a fresh pack. Returns pack_code."""
    mod_code = new_ok_module(client, api_keys, unique_code)
    eol_test(client, api_keys, mod_code, result="OK")
    pack_code = unique_code("PACK")
    r = pack_bind(client, api_keys, mod_code, pack_code)
    assert r.json()["rtnCode"] == 200
    return mod_code, pack_code


def _payload(pack_barcode, batch_number="BATCH-1", work_order_id="WO-1", **overrides):
    record = {
        "work_order_id": work_order_id,
        "product_name": "MV-100Ah-LFP",
        "series_configuration": "16S",
        "parallel_configuration": "1P",
        "category": "ESS",
        "quantity": 10,
        "batch_number": batch_number,
        "pack_barcode": pack_barcode,
        "current_status": "pending",
    }
    record.update(overrides)
    return {"productionDataList": [record]}


def test_success(client, api_keys, unique_code):
    r = client.post(
        "/stations/work-order/data",
        json=_payload(unique_code("PACKBC")),
        headers={"X-API-Key": api_keys["work-order"]},
    )
    assert r.json() == {"rtnCode": 200, "msg": "Upload successful", "data": None}


def test_no_genealogy_gate_against_packs_table(client, api_keys, unique_code):
    # pack_barcode need not correspond to any existing packs.pack_code row —
    # work orders can arrive before, after, or without a module-pack-binding
    # ever landing for it.
    r = client.post(
        "/stations/work-order/data",
        json=_payload(unique_code("NEVER-BOUND")),
        headers={"X-API-Key": api_keys["work-order"]},
    )
    assert r.json()["rtnCode"] == 200


def test_resubmit_same_barcode_overwrites_in_place(client, api_keys, unique_code):
    barcode = unique_code("PACKBC")
    headers = {"X-API-Key": api_keys["work-order"]}

    r1 = client.post("/stations/work-order/data", json=_payload(barcode, current_status="pending"), headers=headers)
    assert r1.json()["rtnCode"] == 200

    r2 = client.post("/stations/work-order/data", json=_payload(barcode, current_status="completed"), headers=headers)
    assert r2.json()["rtnCode"] == 200


def test_optional_time_fields_can_be_omitted(client, api_keys, unique_code):
    r = client.post(
        "/stations/work-order/data",
        json=_payload(unique_code("PACKBC")),
        headers={"X-API-Key": api_keys["work-order"]},
    )
    assert r.json()["rtnCode"] == 200


def test_time_fields_accepted_when_present(client, api_keys, unique_code):
    r = client.post(
        "/stations/work-order/data",
        json=_payload(
            unique_code("PACKBC"),
            actual_time="2026-09-01 08:00:00",
            completion_time="2026-09-01 10:30:00",
        ),
        headers={"X-API-Key": api_keys["work-order"]},
    )
    assert r.json()["rtnCode"] == 200


def test_missing_required_field_is_400(client, api_keys, unique_code):
    payload = _payload(unique_code("PACKBC"))
    del payload["productionDataList"][0]["product_name"]
    r = client.post(
        "/stations/work-order/data",
        json=payload,
        headers={"X-API-Key": api_keys["work-order"]},
    )
    assert r.json()["rtnCode"] == 400


def test_zero_quantity_is_400(client, api_keys, unique_code):
    r = client.post(
        "/stations/work-order/data",
        json=_payload(unique_code("PACKBC"), quantity=0),
        headers={"X-API-Key": api_keys["work-order"]},
    )
    assert r.json()["rtnCode"] == 400


def test_invalid_current_status_is_400(client, api_keys, unique_code):
    r = client.post(
        "/stations/work-order/data",
        json=_payload(unique_code("PACKBC"), current_status="in-progress"),
        headers={"X-API-Key": api_keys["work-order"]},
    )
    assert r.json()["rtnCode"] == 400


def test_current_status_normalized_case_insensitively(client, api_keys, unique_code):
    r = client.post(
        "/stations/work-order/data",
        json=_payload(unique_code("PACKBC"), current_status="COMPLETED"),
        headers={"X-API-Key": api_keys["work-order"]},
    )
    assert r.json()["rtnCode"] == 200


def _summary(client, api_keys, batch_number):
    return client.get(
        f"/stations/work-order/batches/{batch_number}/summary", headers={"X-API-Key": api_keys["work-order"]}
    )


def _order_summary(client, api_keys, work_order_id):
    return client.get(
        f"/stations/work-order/orders/{work_order_id}/summary", headers={"X-API-Key": api_keys["work-order"]}
    )


def test_summary_unknown_batch_is_404(client, api_keys, unique_code):
    r = _summary(client, api_keys, unique_code("NO-SUCH-BATCH"))
    assert r.json()["rtnCode"] == 404


def test_summary_counts_reported_completed_pending(client, api_keys, unique_code):
    batch = unique_code("BATCH")
    headers = {"X-API-Key": api_keys["work-order"]}
    client.post(
        "/stations/work-order/data",
        json=_payload(unique_code("PACKBC"), batch_number=batch, quantity=50, current_status="completed"),
        headers=headers,
    )
    client.post(
        "/stations/work-order/data",
        json=_payload(unique_code("PACKBC"), batch_number=batch, quantity=50, current_status="pending"),
        headers=headers,
    )

    body = _summary(client, api_keys, batch).json()["data"]
    assert body["target_quantity"] == 50
    assert body["reported_quantity"] == 2
    assert body["completed_quantity"] == 1
    assert body["pending_quantity"] == 1
    # Neither barcode matches any real pack_code, so no NG signal exists —
    # unmatched barcodes count as good, not rejected.
    assert body["good_quantity"] == 2
    assert body["rejected_quantity"] == 0


def test_summary_pack_level_ng_marks_rejected(client, api_keys, unique_code):
    _, pack_code = new_ok_pack(client, api_keys, unique_code)
    pack_eol_test(client, api_keys, pack_code, result="NG")

    batch = unique_code("BATCH")
    client.post(
        "/stations/work-order/data",
        json=_payload(pack_code, batch_number=batch, quantity=1),
        headers={"X-API-Key": api_keys["work-order"]},
    )

    body = _summary(client, api_keys, batch).json()["data"]
    assert body["good_quantity"] == 0
    assert body["rejected_quantity"] == 1


def test_rebind_barcode_to_different_batch_is_409(client, api_keys, unique_code):
    barcode = unique_code("PACKBC")
    batch_a = unique_code("BATCH")
    batch_b = unique_code("BATCH")
    headers = {"X-API-Key": api_keys["work-order"]}

    r1 = client.post("/stations/work-order/data", json=_payload(barcode, batch_number=batch_a), headers=headers)
    assert r1.json()["rtnCode"] == 200

    r2 = client.post("/stations/work-order/data", json=_payload(barcode, batch_number=batch_b), headers=headers)
    body = r2.json()
    assert body["rtnCode"] == 409
    assert batch_a in body["msg"]

    # The original batch must still show the barcode -- it wasn't moved.
    original = _summary(client, api_keys, batch_a).json()["data"]
    assert original["reported_quantity"] == 1


def test_rebind_barcode_to_different_work_order_is_409(client, api_keys, unique_code):
    barcode = unique_code("PACKBC")
    batch = unique_code("BATCH")
    headers = {"X-API-Key": api_keys["work-order"]}

    r1 = client.post(
        "/stations/work-order/data", json=_payload(barcode, batch_number=batch, work_order_id="WO-A"), headers=headers
    )
    assert r1.json()["rtnCode"] == 200

    r2 = client.post(
        "/stations/work-order/data", json=_payload(barcode, batch_number=batch, work_order_id="WO-B"), headers=headers
    )
    assert r2.json()["rtnCode"] == 409


def test_missing_work_order_id_is_400(client, api_keys, unique_code):
    payload = _payload(unique_code("PACKBC"))
    del payload["productionDataList"][0]["work_order_id"]
    r = client.post(
        "/stations/work-order/data",
        json=payload,
        headers={"X-API-Key": api_keys["work-order"]},
    )
    assert r.json()["rtnCode"] == 400


def test_order_summary_unknown_id_is_404(client, api_keys, unique_code):
    r = _order_summary(client, api_keys, unique_code("NO-SUCH-ORDER"))
    assert r.json()["rtnCode"] == 404


def test_order_summary_rolls_up_multiple_batches(client, api_keys, unique_code):
    # One work_order_id split across two batches, matching a real
    # production scenario.
    work_order_id = unique_code("WO")
    batch_a = unique_code("BATCH")
    batch_b = unique_code("BATCH")
    headers = {"X-API-Key": api_keys["work-order"]}

    client.post(
        "/stations/work-order/data",
        json=_payload(
            unique_code("PACKBC"),
            batch_number=batch_a,
            work_order_id=work_order_id,
            quantity=30,
            current_status="completed",
        ),
        headers=headers,
    )
    client.post(
        "/stations/work-order/data",
        json=_payload(
            unique_code("PACKBC"),
            batch_number=batch_b,
            work_order_id=work_order_id,
            quantity=20,
            current_status="pending",
        ),
        headers=headers,
    )

    body = _order_summary(client, api_keys, work_order_id).json()["data"]
    assert body["work_order_id"] == work_order_id
    assert body["batch_count"] == 2
    # Sum of each distinct batch's own target quantity, not per-pack-row.
    assert body["target_quantity"] == 50
    assert body["reported_quantity"] == 2
    assert body["completed_quantity"] == 1
    assert body["pending_quantity"] == 1
    assert body["good_quantity"] == 2
    assert body["rejected_quantity"] == 0


def test_summary_cell_level_ng_marks_rejected(client, api_keys, unique_code):
    cell_code = unique_code("CELL")
    mod_code = unique_code("MOD")
    sort_cell(client, api_keys, cell_code, result="OK")
    assert bind(client, api_keys, cell_code, mod_code).json()["rtnCode"] == 200
    eol_test(client, api_keys, mod_code, result="OK")
    pack_code = unique_code("PACK")
    assert pack_bind(client, api_keys, mod_code, pack_code).json()["rtnCode"] == 200

    # A later re-sort flips the already-bound cell to NG — the pack it's
    # part of should now be counted as rejected even with no pack-level
    # test result at all.
    sort_cell(client, api_keys, cell_code, result="NG")

    batch = unique_code("BATCH")
    client.post(
        "/stations/work-order/data",
        json=_payload(pack_code, batch_number=batch, quantity=1),
        headers={"X-API-Key": api_keys["work-order"]},
    )

    body = _summary(client, api_keys, batch).json()["data"]
    assert body["good_quantity"] == 0
    assert body["rejected_quantity"] == 1
