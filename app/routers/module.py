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
    ensure_cells_sorted_ok,
    ensure_modules_exist,
    mark_module_eol_result,
    register_modules,
)
from app.services.judgment import rtn_for_judgments
from app.services.operators import register_operators
from app.services.upsert import upsert_all

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
    rows, judgments = [], []
    for record in payload.productionDataList:
        data = record.model_dump()
        judgments.append(data["pass_information"])
        rows.append({**data, "api_key_id": api_key.id, "raw_payload": record.model_dump(mode="json")})

    ensure_modules_exist(db, [r["mod_code"] for r in rows])
    register_operators(db, rows)
    upsert_all(db, PolarityDetectionReading, rows, conflict_cols=["mod_code", "col_coord"])
    db.commit()

    rtn_code, msg = rtn_for_judgments(*judgments)
    return StandardResponse(rtnCode=rtn_code, msg=msg, data=None)


@router.post("/laser-cleaning/data", response_model=StandardResponse)
def upload_laser_cleaning(
    payload: LaserCleaningRequest,
    db: Session = Depends(get_db),
    api_key=Depends(require_station_access("laser-cleaning")),
):
    rows, judgments = [], []
    for record in payload.productionDataList:
        data = record.model_dump()
        judgments.append(data["pass_information"])
        rows.append({**data, "api_key_id": api_key.id, "raw_payload": record.model_dump(mode="json")})

    ensure_modules_exist(db, [r["mod_code"] for r in rows])
    register_operators(db, rows)
    upsert_all(db, LaserCleaningReading, rows, conflict_cols=["mod_code", "cell_coord"])
    db.commit()

    rtn_code, msg = rtn_for_judgments(*judgments)
    return StandardResponse(rtnCode=rtn_code, msg=msg, data=None)


@router.post("/laser-welding/data", response_model=StandardResponse)
def upload_laser_welding(
    payload: LaserWeldingRequest,
    db: Session = Depends(get_db),
    api_key=Depends(require_station_access("laser-welding")),
):
    rows, judgments = [], []
    for record in payload.productionDataList:
        data = record.model_dump()
        judgments.append(data["pass_information"])
        rows.append({**data, "api_key_id": api_key.id, "raw_payload": record.model_dump(mode="json")})

    ensure_modules_exist(db, [r["mod_code"] for r in rows])
    register_operators(db, rows)
    upsert_all(db, LaserWeldingReading, rows, conflict_cols=["mod_code", "cell_coord"])
    db.commit()

    rtn_code, msg = rtn_for_judgments(*judgments)
    return StandardResponse(rtnCode=rtn_code, msg=msg, data=None)


@router.post("/module-eol-test/data", response_model=StandardResponse)
def upload_module_eol_test(
    payload: ModuleEolTestRequest,
    db: Session = Depends(get_db),
    api_key=Depends(require_station_access("module-eol-test")),
):
    rows, judgments = [], []
    for record in payload.productionDataList:
        data = record.model_dump()
        judgments.extend(
            [
                data["mod_V_Result"],
                data["mod_R_Result"],
                data["mod_IR_Result"],
                data["mod_DWV_Result"],
                data["pass_information"],
            ]
        )
        rows.append({**data, "api_key_id": api_key.id, "raw_payload": record.model_dump(mode="json")})

    ensure_modules_exist(db, [r["mod_code"] for r in rows])
    register_operators(db, rows)
    upsert_all(db, ModuleEolTestReading, rows, conflict_cols=["mod_code"])
    mark_module_eol_result(db, rows)
    db.commit()

    rtn_code, msg = rtn_for_judgments(*judgments)
    return StandardResponse(rtnCode=rtn_code, msg=msg, data=None)
