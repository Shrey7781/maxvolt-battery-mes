from pydantic import ConfigDict, Field, model_validator

from app.schemas.common import (
    CodeStr,
    JudgmentStr,
    MESBaseModel,
    NonNegFloat,
    OptionalCodeStr,
    OptionalEmployeeCode,
    ProductionDataRequest,
    SignedFloat,
)


class ModulePackBindingRecord(MESBaseModel):
    proline_code: CodeStr
    mod_code: CodeStr
    pack_code: CodeStr
    mod_index: int = Field(ge=1)
    bms_code: CodeStr
    station_code: CodeStr
    usercode: CodeStr
    employee_code: OptionalEmployeeCode = None


class ModulePackBindingRequest(ProductionDataRequest[ModulePackBindingRecord]):
    pass


class LiquidCoolingAirtightnessRecord(MESBaseModel):
    proline_code: CodeStr
    # The station only generates pack_code when the plate passes, so it's
    # absent/empty on an NG result (vendor, 2026-10-27). Required on OK.
    pack_code: OptionalCodeStr = None
    # Liquid cooling plate barcode — the natural key. Always sent, OK or NG;
    # it's stuck on the plate, so a retest of the same plate sends the same
    # cooled_code (vendor, 2026-10-27).
    cooled_code: CodeStr
    chargetime: NonNegFloat  # seconds
    holdtime: NonNegFloat  # seconds
    testtime: NonNegFloat  # seconds
    pressure: NonNegFloat  # kPa
    leakage: SignedFloat  # Pa — can legitimately be negative, see SignedFloat
    result: JudgmentStr
    station_code: CodeStr
    usercode: CodeStr
    employee_code: OptionalEmployeeCode = None

    @model_validator(mode="after")
    def _pack_code_required_on_ok(self):
        if self.result == "OK" and self.pack_code is None:
            raise ValueError("pack_code is required when result is OK")
        return self


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

    # Required, min 1 item — matches openapi.yaml's documented contract. A
    # test_file_data with zero measured items would be a final-inspection
    # record with nothing actually measured, so an empty array is rejected
    # rather than silently accepted as "OK, no test items".
    test_items: list[PackEolTestItem] = Field(min_length=1)


class PackEolTestRecord(MESBaseModel):
    station_code: CodeStr
    pack_code: CodeStr
    test_file_data: PackEolTestData
    pass_information: JudgmentStr
    usercode: CodeStr
    employee_code: OptionalEmployeeCode = None


class PackEolTestRequest(ProductionDataRequest[PackEolTestRecord]):
    pass


class PackAirtightnessRecord(MESBaseModel):
    proline_code: CodeStr
    pack_code: CodeStr
    chargetime: NonNegFloat  # seconds
    holdtime: NonNegFloat  # seconds
    testtime: NonNegFloat  # seconds
    pressure: NonNegFloat  # kPa
    leakage: SignedFloat  # Pa — can legitimately be negative, see SignedFloat
    result: JudgmentStr
    station_code: CodeStr
    usercode: CodeStr
    employee_code: OptionalEmployeeCode = None


class PackAirtightnessRequest(ProductionDataRequest[PackAirtightnessRecord]):
    pass
