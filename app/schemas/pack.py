from pydantic import ConfigDict, Field

from app.schemas.common import CodeStr, JudgmentStr, MESBaseModel, NonNegFloat, ProductionDataRequest


class ModulePackBindingRecord(MESBaseModel):
    proline_code: CodeStr
    mod_code: CodeStr
    pack_code: CodeStr
    mod_index: int = Field(ge=1)
    bms_code: CodeStr
    station_code: CodeStr
    usercode: CodeStr
    employee_code: str | None = None


class ModulePackBindingRequest(ProductionDataRequest[ModulePackBindingRecord]):
    pass


class LiquidCoolingAirtightnessRecord(MESBaseModel):
    proline_code: CodeStr
    pack_code: CodeStr
    cooled_code: CodeStr
    chargetime: NonNegFloat
    holdtime: NonNegFloat
    testtime: NonNegFloat
    pressure: NonNegFloat
    leakage: NonNegFloat
    result: JudgmentStr
    station_code: CodeStr
    usercode: CodeStr
    employee_code: str | None = None


class LiquidCoolingAirtightnessRequest(ProductionDataRequest[LiquidCoolingAirtightnessRecord]):
    pass


class PackEolTestItem(MESBaseModel):
    """One measured parameter within the EOL test, e.g. open-circuit voltage
    or AC internal resistance."""

    desc: CodeStr
    value: str
    unit: str | None = None
    up_limit_value: str | None = None
    down_limit_value: str | None = None


class PackEolTestData(MESBaseModel):
    """Structured EOL payload. Shape confirmed with the vendor (2026-07-27):
    they can't give a fixed field-by-field list yet since the battery
    product and its EOL test steps aren't finalized on their side, but gave
    the structural pattern they use for this situation — a self-describing
    array of test items rather than fixed named fields, so new parameters
    don't require a schema change. Revisit once their product team
    finalizes the actual EOL test parameter list."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="allow")

    test_items: list[PackEolTestItem] = Field(default_factory=list)


class PackEolTestRecord(MESBaseModel):
    station_code: CodeStr
    pack_code: CodeStr
    test_file_data: PackEolTestData
    pass_information: JudgmentStr
    usercode: CodeStr
    employee_code: str | None = None


class PackEolTestRequest(ProductionDataRequest[PackEolTestRecord]):
    pass


class PackAirtightnessRecord(MESBaseModel):
    proline_code: CodeStr
    pack_code: CodeStr
    chargetime: NonNegFloat
    holdtime: NonNegFloat
    testtime: NonNegFloat
    pressure: NonNegFloat
    leakage: NonNegFloat
    result: JudgmentStr
    station_code: CodeStr
    usercode: CodeStr
    employee_code: str | None = None


class PackAirtightnessRequest(ProductionDataRequest[PackAirtightnessRecord]):
    pass
