"""App using APIRouter + include_router, plus a class-based dependency —
the pattern that broke route detection on recent Starlette versions (see
inspect.py:_iter_resolved_routes), because routes included via a router
stopped showing up as flat ``APIRoute`` objects in ``app.routes``.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI


class RateLimiter:
    def __call__(self) -> str:
        return "checked"


check_rate_limit = RateLimiter()


def get_settings() -> str:
    return "settings"


router = APIRouter(prefix="/items")


@router.get("/")
def list_items(
    settings: Annotated[str, Depends(get_settings)],
    limited: Annotated[str, Depends(check_rate_limit)],
):
    return {"settings": settings, "limited": limited}


app = FastAPI()
app.include_router(router)


@app.get("/health")
def health():
    return {"ok": True}
