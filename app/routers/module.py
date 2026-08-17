from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.envelope import StandardResponse
from app.models.module import (
    AutoStackingReading,
    CellModuleBinding,
    LaserCleaningReading,
    LaserWeldingReading,
    ModuleEolTestReading,
    PolarityDetectionReading,
)
from app.schemas.module import (
    AutoStackingRequest,
    CellModuleBindingRequest,
    LaserCleaningRequest,
    LaserWeldingRequest,
    ModuleEolTestRequest,
    PolarityDetectionRequest,
)
from app.security import require_station_access
from app.services.genealogy import (
    ensure_cells_exist,
    ensure_cells_not_rebound,
    ensure_cells_sorted_ok,
    ensure_modules_exist,
    mark_module_eol_result,
    register_modules,
)
from app.services.judgment import rtn_for_judgments
from app.services.operators import register_operators
from app.services.upsert import dedupe_by_keys, upsert_all

router = APIRouter(prefix="/stations", tags=["Module Processing"])


@router.post("/cell-module-binding/data", response_model=StandardResponse)
def upload_cell_module_binding(
    payload: CellModuleBindingRequest,
    db: Session = Depends(get_db),
    api_key=Depends(require_station_access("cell-module-binding")),
):
    rows = []
    for record in payload.productionDataList:
        data = record.model_dump()
        rows.append({**data, "api_key_id": api_key.id, "raw_payload": record.model_dump(mode="json")})

    ensure_cells_exist(db, [r["cell_code"] for r in rows])
    ensure_cells_sorted_ok(db, [r["cell_code"] for r in rows])
    ensure_cells_not_rebound(db, rows)
    register_modules(db, rows)
    register_operators(db, rows)
    upsert_all(db, CellModuleBinding, rows, conflict_cols=["cell_code"])
    db.commit()

    rtn_code, msg = rtn_for_judgments()
    return StandardResponse(rtnCode=rtn_code, msg=msg, data=None)


@router.post("/auto-stacking/data", response_model=StandardResponse)
def upload_auto_stacking(
    payload: AutoStackingRequest,
    db: Session = Depends(get_db),
    api_key=Depends(require_station_access("auto-stacking")),
):
    rows = []
    for record in payload.productionDataList:
        data = record.model_dump()
        rows.append({**data, "api_key_id": api_key.id, "raw_payload": record.model_dump(mode="json")})

    ensure_modules_exist(db, [r["mod_code"] for r in rows])
    upsert_all(db, AutoStackingReading, rows, conflict_cols=["mod_code"])
    db.commit()

    rtn_code, msg = rtn_for_judgments()
    return StandardResponse(rtnCode=rtn_code, msg=msg, data=None)


@router.post("/polarity-detection/data", response_model=StandardResponse)
def upload_polarity_detection(
    payload: PolarityDetectionRequest,
    db: Session = Depends(get_db),
    api_key=Depends(require_station_access("polarity-detection")),
):
    rows = []
    for record in payload.productionDataList:
        data = record.model_dump()
        rows.append({**data, "api_key_id": api_key.id, "raw_payload": record.model_dump(mode="json")})

    ensure_modules_exist(db, [r["mod_code"] for r in rows])
    register_operators(db, rows)
    conflict_cols = ["mod_code", "col_coord"]
    upsert_all(db, PolarityDetectionReading, rows, conflict_cols=conflict_cols)
    db.commit()

    persisted = dedupe_by_keys(rows, conflict_cols)
    rtn_code, msg = rtn_for_judgments(*(r["pass_information"] for r in persisted))
    return StandardResponse(rtnCode=rtn_code, msg=msg, data=None)


@router.post("/laser-cleaning/data", response_model=StandardResponse)
def upload_laser_cleaning(
    payload: LaserCleaningRequest,
    db: Session = Depends(get_db),
    api_key=Depends(require_station_access("laser-cleaning")),
):
    rows = []
    for record in payload.productionDataList:
        data = record.model_dump()
        rows.append({**data, "api_key_id": api_key.id, "raw_payload": record.model_dump(mode="json")})

    ensure_modules_exist(db, [r["mod_code"] for r in rows])
    register_operators(db, rows)
    conflict_cols = ["mod_code", "cell_coord"]
    upsert_all(db, LaserCleaningReading, rows, conflict_cols=conflict_cols)
    db.commit()

    persisted = dedupe_by_keys(rows, conflict_cols)
    rtn_code, msg = rtn_for_judgments(*(r["pass_information"] for r in persisted))
    return StandardResponse(rtnCode=rtn_code, msg=msg, data=None)


@router.post("/laser-welding/data", response_model=StandardResponse)
def upload_laser_welding(
    payload: LaserWeldingRequest,
    db: Session = Depends(get_db),
    api_key=Depends(require_station_access("laser-welding")),
):
    rows = []
    for record in payload.productionDataList:
        data = record.model_dump()
        rows.append({**data, "api_key_id": api_key.id, "raw_payload": record.model_dump(mode="json")})

    ensure_modules_exist(db, [r["mod_code"] for r in rows])
    register_operators(db, rows)
    conflict_cols = ["mod_code", "cell_coord"]
    upsert_all(db, LaserWeldingReading, rows, conflict_cols=conflict_cols)
    db.commit()

    persisted = dedupe_by_keys(rows, conflict_cols)
    rtn_code, msg = rtn_for_judgments(*(r["pass_information"] for r in persisted))
    return StandardResponse(rtnCode=rtn_code, msg=msg, data=None)


@router.post("/module-eol-test/data", response_model=StandardResponse)
def upload_module_eol_test(
    payload: ModuleEolTestRequest,
    db: Session = Depends(get_db),
    api_key=Depends(require_station_access("module-eol-test")),
):
    rows = []
    for record in payload.productionDataList:
        data = record.model_dump()
        rows.append({**data, "api_key_id": api_key.id, "raw_payload": record.model_dump(mode="json")})

    ensure_modules_exist(db, [r["mod_code"] for r in rows])
    register_operators(db, rows)
    conflict_cols = ["mod_code"]
    upsert_all(db, ModuleEolTestReading, rows, conflict_cols=conflict_cols)
    mark_module_eol_result(db, rows)
    db.commit()

    persisted = dedupe_by_keys(rows, conflict_cols)
    judgments = [
        v
        for r in persisted
        for v in (r["mod_V_Result"], r["mod_R_Result"], r["mod_IR_Result"], r["mod_DWV_Result"], r["pass_information"])
    ]
    rtn_code, msg = rtn_for_judgments(*judgments)
    return StandardResponse(rtnCode=rtn_code, msg=msg, data=None)
