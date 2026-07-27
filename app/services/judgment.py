from app.envelope import RTN


def rtn_for_judgments(*values: str | None) -> tuple[int, str]:
    """A batch is reported as 201 (rework) if any judgment field in it came
    back NG, so the device/robot knows to route the physical unit to rework
    rather than treating the upload as a plain success."""
    if any(v == "NG" for v in values if v is not None):
        return RTN.REWORK, "Recorded — one or more results are NG, route unit(s) to rework"
    return RTN.SUCCESS, "Upload successful"
