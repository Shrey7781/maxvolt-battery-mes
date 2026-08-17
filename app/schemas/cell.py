from app.schemas.common import CodeStr, JudgmentStr, MESBaseModel, NonNegFloat, OptionalEmployeeCode, ProductionDataRequest


class CellSortingRecord(MESBaseModel):
    proline_code: CodeStr
    cell_code: CodeStr
    station_code: CodeStr
    voltage: NonNegFloat
    inter_res: NonNegFloat
    nnr: NonNegFloat
    pass_information: JudgmentStr
    usercode: CodeStr
    employee_code: OptionalEmployeeCode = None


class CellSortingRequest(ProductionDataRequest[CellSortingRecord]):
    pass
