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
    register_packs,
)
from app.services.judgment import rtn_for_judgments
from app.services.operators import register_operators
from app.services.upsert import dedupe_by_keys, upsert_all

router = APIRouter(prefix="/stations", tags=["Pack Processing"])


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

    ensure_modules_exist(db, [r["mod_code"] for r in rows])
    ensure_modules_passed_eol(db, [r["mod_code"] for r in rows])
    ensure_modules_not_rebound(db, rows)
    ensure_pack_slots_available(db, rows)
    register_packs(db, rows)
    register_operators(db, rows)
    upsert_all(db, ModulePackBinding, rows, conflict_cols=["mod_code"])
    db.commit()

    rtn_code, msg = rtn_for_judgments()
    return StandardResponse(rtnCode=rtn_code, msg=msg, data=None)


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

    ensure_packs_exist(db, [r["pack_code"] for r in rows])
    register_operators(db, rows)
    conflict_cols = ["pack_code"]
    upsert_all(db, LiquidCoolingAirtightnessReading, rows, conflict_cols=conflict_cols)
    db.commit()

    persisted = dedupe_by_keys(rows, conflict_cols)
    rtn_code, msg = rtn_for_judgments(*(r["result"] for r in persisted))
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
