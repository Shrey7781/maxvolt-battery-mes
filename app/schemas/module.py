from pydantic import Field

from app.schemas.common import (
    CodeStr,
    CodeStr255,
    JudgmentStr,
    LongCodeStr,
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
    col_coord: LongCodeStr
    mark_info: CodeStr255
    pass_information: JudgmentStr
    usercode: CodeStr
    employee_code: OptionalEmployeeCode = None


class PolarityDetectionRequest(ProductionDataRequest[PolarityDetectionRecord]):
    pass


class LaserCleaningRecord(MESBaseModel):
    station_code: CodeStr
    mod_code: CodeStr
    # Mark point coordinates (a visual-recognition feature pattern on the
    # cell product — short). Replaced cell_coord in the vendor's 2026-10 spec
    # revision.
    mark_info: CodeStr
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
    cell_coord: LongCodeStr
    welding_power: NonNegFloat
    speed: NonNegFloat
    pass_information: JudgmentStr
    # No usercode: the vendor's 2026-10 spec revision removed it — this
    # station only uploads the optional operator name. A device still sending
    # usercode is not rejected; it's dropped like any other unknown field
    # (MESBaseModel extra="ignore").
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
