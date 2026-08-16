"""App que usa APIRouter + include_router, y una dependencia basada en
clase — el patrón que rompía la detección de rutas en versiones recientes
de Starlette (ver inspect.py:_iter_api_routes) porque las rutas incluidas
vía router dejaron de aparecer como ``APIRoute`` planas en ``app.routes``.
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
