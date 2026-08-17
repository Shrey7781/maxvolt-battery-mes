import math
from datetime import datetime
from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

T = TypeVar("T")

_OK_VALUES = {"ok", "pass", "passed", "true", "1", "yes"}
_NG_VALUES = {"ng", "fail", "failed", "false", "0", "no"}


def normalize_judgment(value: object) -> str:
    """Accepts the vendor's original OK/NG plus common equivalents
    (1/0, true/false, pass/fail) and normalizes to 'OK' / 'NG'.

    Devices in the field don't always comply with the documented contract,
    so this is deliberately permissive on input while being strict on output.
    """
    if isinstance(value, bool):
        return "OK" if value else "NG"
    text = str(value).strip().lower()
    if text in _OK_VALUES:
        return "OK"
    if text in _NG_VALUES:
        return "NG"
    raise ValueError(f"invalid judgment value {value!r}; expected OK/NG or a recognized equivalent")


def coerce_float(value: object) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{value!r} is not a valid number")
    if isinstance(value, (int, float)):
        result = float(value)
    else:
        try:
            result = float(str(value).strip())
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{value!r} is not a valid number") from exc
    if not math.isfinite(result):
        # float() accepts "inf"/"nan" (case-insensitively) as valid input,
        # but Postgres's JSON parser rejects them outright when this value
        # is later serialized into raw_payload — reject here instead of
        # surfacing that as an unhandled 500.
        raise ValueError(f"{value!r} is not a finite number")
    return result


def parse_mes_timestamp(value: object) -> datetime:
    """Parses the vendor's documented 'yyyy-MM-dd HH:mm:ss' format, with
    ISO 8601 accepted as a fallback for forward compatibility."""
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"{value!r} does not match expected timestamp format yyyy-MM-dd HH:mm:ss")


JudgmentStr = Annotated[str, BeforeValidator(normalize_judgment)]
NonNegFloat = Annotated[float, BeforeValidator(coerce_float), Field(ge=0)]
MesTimestamp = Annotated[datetime, BeforeValidator(parse_mes_timestamp)]
CodeStr = Annotated[str, Field(min_length=1, max_length=120)]
# employee_code is optional everywhere it appears, but still backed by a
# String(120) column — unlike CodeStr, no min_length, since None/absent is
# the normal case.
OptionalEmployeeCode = Annotated[str, Field(max_length=120)] | None


class MESBaseModel(BaseModel):
    # str_strip_whitespace applies to every str field on subclasses, so
    # CodeStr's min_length=1 check runs against the already-stripped value.
    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")


class ProductionDataRequest(MESBaseModel, Generic[T]):
    productionDataList: list[T] = Field(min_length=1)
