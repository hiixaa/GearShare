"""Every engine exception becomes an HTTP status + {"error": code, "message": text}.

The message is the exact console text (e.message); the code is the rule number
for rule violations (R3) and the class name for the others. See DECISIONS D28.
"""

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from errors import (
    CustomerNotFoundError,
    GearShareError,
    InvalidSKUError,
    ItemNotFoundError,
    RentalNotFoundError,
    StorageError,
)

# 404: the thing doesn't exist. 422: the input itself makes no sense.
# 503: the server can't save right now. Everything else is a rule saying
# "it exists, but its state conflicts with your request": 409.
STATUS = {
    InvalidSKUError: 422,
    CustomerNotFoundError: 404,
    ItemNotFoundError: 404,
    RentalNotFoundError: 404,
    StorageError: 503,
}
DEFAULT_RULE_STATUS = 409


def error_body(code, message):
    return {"error": code, "message": message}


def status_for(exc):
    for cls in type(exc).__mro__:            # most specific class first
        if cls in STATUS:
            return STATUS[cls]
    return DEFAULT_RULE_STATUS


async def gearshare_error_handler(request: Request, exc: GearShareError):
    return JSONResponse(status_code=status_for(exc),
                        content=error_body(exc.code, exc.message))


async def validation_error_handler(request: Request, exc: RequestValidationError):
    """A missing or wrongly typed JSON field: same body shape as every other error."""
    first = exc.errors()[0]
    field = ".".join(str(part) for part in first["loc"] if part != "body")
    return JSONResponse(status_code=422,
                        content=error_body("ValidationError", f"{field}: {first['msg']}"))


def register(app):
    app.add_exception_handler(GearShareError, gearshare_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
