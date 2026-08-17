from pydantic import Field

from app.schemas.common import (
    CodeStr,
    JudgmentStr,
    MESBaseModel,
    MesTimestamp,
    NonNegFloat,
    OptionalEmployeeCode,
    ProductionDataRequest,
)


class CellModuleBindingRecord(MESBaseModel):
    proline_code: CodeStr
    mod_code: CodeStr
    cell_code: CodeStr
    cell_index: int = Field(ge=1)
    station_code: CodeStr
    usercode: CodeStr
    employee_code: OptionalEmployeeCode = None


class CellModuleBindingRequest(ProductionDataRequest[CellModuleBindingRecord]):
    pass


class AutoStackingRecord(MESBaseModel):
    proline_code: CodeStr
    mod_code: CodeStr
    start_pressure: NonNegFloat
    end_pressure: NonNegFloat
    average_pressure: NonNegFloat
    end_time: MesTimestamp


class AutoStackingRequest(ProductionDataRequest[AutoStackingRecord]):
    pass


class PolarityDetectionRecord(MESBaseModel):
    station_code: CodeStr
    mod_code: CodeStr
    col_coord: CodeStr
    mark_info: CodeStr
    pass_information: JudgmentStr
    usercode: CodeStr
    employee_code: OptionalEmployeeCode = None


class PolarityDetectionRequest(ProductionDataRequest[PolarityDetectionRecord]):
    pass


class LaserCleaningRecord(MESBaseModel):
    station_code: CodeStr
    mod_code: CodeStr
    cell_coord: CodeStr
    cleaning_power: NonNegFloat
    speed: NonNegFloat
    pass_information: JudgmentStr
    usercode: CodeStr
    employee_code: OptionalEmployeeCode = None


class LaserCleaningRequest(ProductionDataRequest[LaserCleaningRecord]):
    pass


class LaserWeldingRecord(MESBaseModel):
    station_code: CodeStr
    mod_code: CodeStr
    cell_coord: CodeStr
    welding_power: NonNegFloat
    speed: NonNegFloat
    pass_information: JudgmentStr
    usercode: CodeStr
    employee_code: OptionalEmployeeCode = None


class LaserWeldingRequest(ProductionDataRequest[LaserWeldingRecord]):
    pass


class ModuleEolTestRecord(MESBaseModel):
    station_code: CodeStr
    mod_code: CodeStr
    mod_V: NonNegFloat
    mod_V_Result: JudgmentStr
    mod_R: NonNegFloat
    mod_R_Result: JudgmentStr
    mod_IR: NonNegFloat
    mod_IR_Result: JudgmentStr
    mod_DWV: NonNegFloat
    mod_DWV_Result: JudgmentStr
    pass_information: JudgmentStr
    usercode: CodeStr
    employee_code: OptionalEmployeeCode = None


class ModuleEolTestRequest(ProductionDataRequest[ModuleEolTestRecord]):
    pass
