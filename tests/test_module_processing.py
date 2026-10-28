"""Coverage for the module-processing stations whose fields changed in the
vendor's 2026-10 spec revision:
  - polarity-detection: col_coord may be a very long coordinate list.
  - laser-cleaning: cell_coord replaced by mark_info.
  - laser-welding: cell_coord may be very long; usercode removed.
The long-coordinate natural keys are enforced via md5-based unique indexes
(app/models/module.py), so the idempotency tests here check the row count
directly rather than just the rtnCode."""

from sqlalchemy import func, select

from app.database import SessionLocal
from app.models.module import LaserCleaningReading, LaserWeldingReading, PolarityDetectionReading
from tests.test_module_pack_flow import new_ok_module


def long_coord(length=5000):
    """A coordinate list well past a btree index entry's ~2.7KB limit,
    shaped like the vendor's example (x,y pairs separated by ':')."""
    pair = "159.101,-376.766:"
    return (pair * (length // len(pair) + 1))[:length]


def _row_count(model, mod_code):
    with SessionLocal() as db:
        return db.scalar(select(func.count()).select_from(model).where(model.mod_code == mod_code))


def polarity(client, api_keys, mod_code, col_coord, result="OK", mark_info="1024.375,-499.162;159.108,-376.760"):
    payload = {
        "productionDataList": [
            {
                "station_code": "PD-01",
                "mod_code": mod_code,
                "col_coord": col_coord,
                "mark_info": mark_info,
                "pass_information": result,
                "usercode": "OP-TEST-1",
            }
        ]
    }
    return client.post(
        "/stations/polarity-detection/data", json=payload, headers={"X-API-Key": api_keys["polarity-detection"]}
    )


def laser_cleaning(client, api_keys, mod_code, mark_info="A1", result="OK", **overrides):
    record = {
        "station_code": "LC-01",
        "mod_code": mod_code,
        "mark_info": mark_info,
        "cleaning_power": 45.0,
        "speed": 12.5,
        "pass_information": result,
        "usercode": "OP-TEST-1",
    }
    record.update(overrides)
    return client.post(
        "/stations/laser-cleaning/data",
        json={"productionDataList": [record]},
        headers={"X-API-Key": api_keys["laser-cleaning"]},
    )


def laser_welding(client, api_keys, mod_code, cell_coord, result="OK", **overrides):
    record = {
        "station_code": "LW-01",
        "mod_code": mod_code,
        "cell_coord": cell_coord,
        "welding_power": 850.0,
        "speed": 8.2,
        "pass_information": result,
        "employee_code": "somebody",
    }
    record.update(overrides)
    return client.post(
        "/stations/laser-welding/data",
        json={"productionDataList": [record]},
        headers={"X-API-Key": api_keys["laser-welding"]},
    )


# --- Polarity Detection & Addressing ---------------------------------------


def test_polarity_long_col_coord_accepted(client, api_keys, unique_code):
    mod_code = new_ok_module(client, api_keys, unique_code)
    r = polarity(client, api_keys, mod_code, long_coord(5000))
    assert r.json()["rtnCode"] == 200


def test_polarity_col_coord_at_10000_chars_accepted(client, api_keys, unique_code):
    mod_code = new_ok_module(client, api_keys, unique_code)
    r = polarity(client, api_keys, mod_code, long_coord(10000))
    assert r.json()["rtnCode"] == 200


def test_polarity_col_coord_over_10000_chars_is_400(client, api_keys, unique_code):
    mod_code = new_ok_module(client, api_keys, unique_code)
    r = polarity(client, api_keys, mod_code, long_coord(10001))
    assert r.json()["rtnCode"] == 400


def test_polarity_mark_info_up_to_255_chars_accepted(client, api_keys, unique_code):
    # Spec and DB column both allow 255; the API used to cap it at 120.
    mod_code = new_ok_module(client, api_keys, unique_code)
    r = polarity(client, api_keys, mod_code, "A1", mark_info="M" * 255)
    assert r.json()["rtnCode"] == 200

    with SessionLocal() as db:
        stored = db.scalar(
            select(PolarityDetectionReading.mark_info).where(PolarityDetectionReading.mod_code == mod_code)
        )
    assert len(stored) == 255


def test_polarity_mark_info_over_255_chars_is_400(client, api_keys, unique_code):
    mod_code = new_ok_module(client, api_keys, unique_code)
    body = polarity(client, api_keys, mod_code, "A1", mark_info="M" * 256).json()
    assert body["rtnCode"] == 400
    assert "mark_info" in body["msg"]


def test_polarity_resubmit_same_long_coord_overwrites_in_place(client, api_keys, unique_code):
    mod_code = new_ok_module(client, api_keys, unique_code)
    coord = long_coord(5000)

    assert polarity(client, api_keys, mod_code, coord, result="OK").json()["rtnCode"] == 200
    assert polarity(client, api_keys, mod_code, coord, result="NG").json()["rtnCode"] == 201
    assert _row_count(PolarityDetectionReading, mod_code) == 1

    with SessionLocal() as db:
        stored = db.scalar(
            select(PolarityDetectionReading.pass_information).where(PolarityDetectionReading.mod_code == mod_code)
        )
    assert stored == "NG"


def test_polarity_different_col_coord_is_separate_reading(client, api_keys, unique_code):
    mod_code = new_ok_module(client, api_keys, unique_code)
    polarity(client, api_keys, mod_code, long_coord(5000))
    polarity(client, api_keys, mod_code, long_coord(4000))
    assert _row_count(PolarityDetectionReading, mod_code) == 2


# --- Laser Cleaning ----------------------------------------------------------


def test_laser_cleaning_with_mark_info_succeeds(client, api_keys, unique_code):
    mod_code = new_ok_module(client, api_keys, unique_code)
    r = laser_cleaning(client, api_keys, mod_code, mark_info="A1")
    assert r.json() == {"rtnCode": 200, "msg": "Upload successful", "data": None}


def test_laser_cleaning_missing_mark_info_is_400(client, api_keys, unique_code):
    # A device still sending the pre-revision cell_coord field (and no
    # mark_info) is rejected with a message naming the missing field.
    mod_code = new_ok_module(client, api_keys, unique_code)
    legacy_record = {
        "station_code": "LC-01",
        "mod_code": mod_code,
        "cell_coord": "A1",
        "cleaning_power": 45.0,
        "speed": 12.5,
        "pass_information": "OK",
        "usercode": "OP-TEST-1",
    }
    r = client.post(
        "/stations/laser-cleaning/data",
        json={"productionDataList": [legacy_record]},
        headers={"X-API-Key": api_keys["laser-cleaning"]},
    )
    body = r.json()
    assert body["rtnCode"] == 400
    assert "mark_info" in body["msg"]


def test_laser_cleaning_resubmit_same_mark_info_overwrites_in_place(client, api_keys, unique_code):
    mod_code = new_ok_module(client, api_keys, unique_code)
    assert laser_cleaning(client, api_keys, mod_code, mark_info="A1").json()["rtnCode"] == 200
    assert laser_cleaning(client, api_keys, mod_code, mark_info="A1", result="NG").json()["rtnCode"] == 201
    assert _row_count(LaserCleaningReading, mod_code) == 1


def test_laser_cleaning_mark_info_over_120_chars_is_400(client, api_keys, unique_code):
    mod_code = new_ok_module(client, api_keys, unique_code)
    r = laser_cleaning(client, api_keys, mod_code, mark_info="X" * 121)
    assert r.json()["rtnCode"] == 400


# --- Laser Welding -----------------------------------------------------------


def test_laser_welding_without_usercode_succeeds(client, api_keys, unique_code):
    mod_code = new_ok_module(client, api_keys, unique_code)
    r = laser_welding(client, api_keys, mod_code, long_coord(5000))
    assert r.json() == {"rtnCode": 200, "msg": "Upload successful", "data": None}

    with SessionLocal() as db:
        row = db.execute(
            select(LaserWeldingReading.usercode, LaserWeldingReading.employee_code).where(
                LaserWeldingReading.mod_code == mod_code
            )
        ).one()
    assert row.usercode is None
    assert row.employee_code == "somebody"


def test_laser_welding_without_employee_code_succeeds(client, api_keys, unique_code):
    mod_code = new_ok_module(client, api_keys, unique_code)
    r = laser_welding(client, api_keys, mod_code, "A1", employee_code=None)
    assert r.json()["rtnCode"] == 200


def test_laser_welding_legacy_usercode_is_ignored_not_rejected(client, api_keys, unique_code):
    # A device that hasn't been updated yet still sends usercode — accepted,
    # with the field dropped like any other unknown field.
    mod_code = new_ok_module(client, api_keys, unique_code)
    r = laser_welding(client, api_keys, mod_code, "A1", usercode="OP-LEGACY")
    assert r.json()["rtnCode"] == 200


def test_laser_welding_cell_coord_over_10000_chars_is_400(client, api_keys, unique_code):
    mod_code = new_ok_module(client, api_keys, unique_code)
    r = laser_welding(client, api_keys, mod_code, long_coord(10001))
    assert r.json()["rtnCode"] == 400


def test_laser_welding_resubmit_same_long_coord_overwrites_in_place(client, api_keys, unique_code):
    mod_code = new_ok_module(client, api_keys, unique_code)
    coord = long_coord(8000)
    assert laser_welding(client, api_keys, mod_code, coord).json()["rtnCode"] == 200
    assert laser_welding(client, api_keys, mod_code, coord, result="NG").json()["rtnCode"] == 201
    assert _row_count(LaserWeldingReading, mod_code) == 1


def test_laser_welding_unknown_module_is_404(client, api_keys, unique_code):
    r = laser_welding(client, api_keys, unique_code("MOD"), "A1")
    assert r.json()["rtnCode"] == 404
