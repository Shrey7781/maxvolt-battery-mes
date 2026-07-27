from enum import IntEnum
from typing import Any

from pydantic import BaseModel


class RTN(IntEnum):
    """rtnCode values returned in the response body.

    HTTP status is always 200 (see main.py exception handlers) — the real
    outcome is carried in rtnCode, matching the vendor's original interface
    contract and the fact that many PLC/robot HTTP clients only parse the
    JSON body, not the HTTP status line.
    """

    SUCCESS = 200
    REWORK = 201
    VALIDATION_ERROR = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    REFERENCE_NOT_FOUND = 404
    PRECONDITION_FAILED = 422
    DUPLICATE = 409
    RATE_LIMITED = 429
    INTERNAL_ERROR = 500


class StandardResponse(BaseModel):
    rtnCode: int
    msg: str
    data: Any | None = None


class MESError(Exception):
    """Raised anywhere in request handling to short-circuit to a StandardResponse."""

    def __init__(self, rtn_code: int, msg: str):
        self.rtn_code = rtn_code
        self.msg = msg
        super().__init__(msg)
