from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.envelope import StandardResponse
from app.models.cell import CellSortingReading
from app.schemas.cell import CellSortingRequest
from app.security import require_station_access
from app.services.genealogy import register_cells
from app.services.judgment import rtn_for_judgments
from app.services.operators import register_operators
from app.services.upsert import upsert_all

router = APIRouter(prefix="/stations", tags=["Cell Processing"])

STATION = "cell-sorting"


@router.post("/cell-sorting/data", response_model=StandardResponse)
def upload_cell_sorting(
    payload: CellSortingRequest,
    db: Session = Depends(get_db),
    api_key=Depends(require_station_access(STATION)),
):
    rows, judgments = [], []
    for record in payload.productionDataList:
        data = record.model_dump()
        judgments.append(data["pass_information"])
        rows.append({**data, "api_key_id": api_key.id, "raw_payload": record.model_dump(mode="json")})

    register_cells(db, rows)
    register_operators(db, rows)
    upsert_all(db, CellSortingReading, rows, conflict_cols=["cell_code", "station_code"])
    db.commit()

    rtn_code, msg = rtn_for_judgments(*judgments)
    return StandardResponse(rtnCode=rtn_code, msg=msg, data=None)
