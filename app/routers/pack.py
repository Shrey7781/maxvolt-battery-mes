from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.envelope import StandardResponse
from app.models.pack import (
    LiquidCoolingAirtightnessReading,
    ModulePackBinding,
    PackAirtightnessReading,
    PackEolTestReading,
)
from app.schemas.pack import (
    LiquidCoolingAirtightnessRequest,
    ModulePackBindingRequest,
    PackAirtightnessRequest,
    PackEolTestRequest,
)
from app.security import require_station_access
from app.services.genealogy import (
    ensure_modules_exist,
    ensure_modules_not_rebound,
    ensure_modules_passed_eol,
    ensure_pack_slots_available,
    ensure_packs_exist,
    ensure_packs_have_one_plate,
    ensure_packs_passed_liquid_cooling,
    ensure_plates_not_rebound,
    register_packs,
)
from app.services.judgment import rtn_for_judgments
from app.services.operators import register_operators
from app.services.upsert import dedupe_by_keys, upsert_all

router = APIRouter(prefix="/stations", tags=["Pack Processing"])

# Routes are declared in line order (08 Liquid Cooling Plate Airtightness,
# 09 Module-Pack Code Bonding, 10 PACK EOL, 11 PACK Airtightness) — FastAPI
# lists them in /docs in declaration order.


@router.post("/liquid-cooling-airtightness/data", response_model=StandardResponse)
def upload_liquid_cooling_airtightness(
    payload: LiquidCoolingAirtightnessRequest,
    db: Session = Depends(get_db),
    api_key=Depends(require_station_access("liquid-cooling-airtightness")),
):
    rows = []
    for record in payload.productionDataList:
        data = record.model_dump()
        rows.append({**data, "api_key_id": api_key.id, "raw_payload": record.model_dump(mode="json")})

    # Keyed on the plate. Dedupe up front so every check below sees only the
    # record per plate that actually gets persisted.
    conflict_cols = ["cooled_code"]
    persisted = dedupe_by_keys(rows, conflict_cols)

    # First pack station: an OK result creates the pack identity (the
    # station's PC software generates pack_code), so there is no upstream
    # gate. An NG result has no pack_code and creates no pack.
    with_pack = [r for r in persisted if r["pack_code"] is not None]
    # Leaving pack_code out of NG rows (rather than passing None) means a
    # retest NG of a plate that already passed keeps its pack link, so the
    # pack's NG still shows up by pack_code (e.g. the work order summary).
    # Split in two upserts since one multi-row INSERT needs the same columns
    # on every row.
    without_pack = [{k: v for k, v in r.items() if k != "pack_code"} for r in persisted if r["pack_code"] is None]

    ensure_plates_not_rebound(db, with_pack)
    ensure_packs_have_one_plate(db, with_pack)
    register_packs(db, with_pack)
    register_operators(db, persisted)
    upsert_all(db, LiquidCoolingAirtightnessReading, with_pack, conflict_cols=conflict_cols)
    upsert_all(db, LiquidCoolingAirtightnessReading, without_pack, conflict_cols=conflict_cols)
    db.commit()

    rtn_code, msg = rtn_for_judgments(*(r["result"] for r in persisted))
    return StandardResponse(rtnCode=rtn_code, msg=msg, data=None)


@router.post("/module-pack-binding/data", response_model=StandardResponse)
def upload_module_pack_binding(
    payload: ModulePackBindingRequest,
    db: Session = Depends(get_db),
    api_key=Depends(require_station_access("module-pack-binding")),
):
    rows = []
    for record in payload.productionDataList:
        data = record.model_dump()
        rows.append({**data, "api_key_id": api_key.id, "raw_payload": record.model_dump(mode="json")})

    # The pack identity is created upstream by liquid-cooling-airtightness
    # (station 08, ahead of this one since the vendor's 2026-10 spec
    # revision), so this station only checks that it exists.
    ensure_modules_exist(db, [r["mod_code"] for r in rows])
    ensure_packs_exist(db, [r["pack_code"] for r in rows])
    ensure_modules_passed_eol(db, [r["mod_code"] for r in rows])
    ensure_packs_passed_liquid_cooling(db, [r["pack_code"] for r in rows])
    ensure_modules_not_rebound(db, rows)
    ensure_pack_slots_available(db, rows)
    register_operators(db, rows)
    upsert_all(db, ModulePackBinding, rows, conflict_cols=["mod_code"])
    db.commit()

    rtn_code, msg = rtn_for_judgments()
    return StandardResponse(rtnCode=rtn_code, msg=msg, data=None)


@router.post("/pack-eol-test/data", response_model=StandardResponse)
def upload_pack_eol_test(
    payload: PackEolTestRequest,
    db: Session = Depends(get_db),
    api_key=Depends(require_station_access("pack-eol-test")),
):
    rows = []
    for record in payload.productionDataList:
        data = record.model_dump()
        rows.append(
            {
                "station_code": data["station_code"],
                "pack_code": data["pack_code"],
                "test_file_data": data["test_file_data"],
                "pass_information": data["pass_information"],
                "usercode": data["usercode"],
                "employee_code": data["employee_code"],
                "api_key_id": api_key.id,
                "raw_payload": record.model_dump(mode="json"),
            }
        )

    ensure_packs_exist(db, [r["pack_code"] for r in rows])
    register_operators(db, rows)
    conflict_cols = ["pack_code"]
    upsert_all(db, PackEolTestReading, rows, conflict_cols=conflict_cols)
    db.commit()

    persisted = dedupe_by_keys(rows, conflict_cols)
    rtn_code, msg = rtn_for_judgments(*(r["pass_information"] for r in persisted))
    return StandardResponse(rtnCode=rtn_code, msg=msg, data=None)


@router.post("/pack-airtightness/data", response_model=StandardResponse)
def upload_pack_airtightness(
    payload: PackAirtightnessRequest,
    db: Session = Depends(get_db),
    api_key=Depends(require_station_access("pack-airtightness")),
):
    rows = []
    for record in payload.productionDataList:
        data = record.model_dump()
        rows.append({**data, "api_key_id": api_key.id, "raw_payload": record.model_dump(mode="json")})

    ensure_packs_exist(db, [r["pack_code"] for r in rows])
    register_operators(db, rows)
    conflict_cols = ["pack_code"]
    upsert_all(db, PackAirtightnessReading, rows, conflict_cols=conflict_cols)
    db.commit()

    persisted = dedupe_by_keys(rows, conflict_cols)
    rtn_code, msg = rtn_for_judgments(*(r["result"] for r in persisted))
    return StandardResponse(rtnCode=rtn_code, msg=msg, data=None)
