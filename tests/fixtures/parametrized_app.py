"""App con dependencias parametrizadas (factory/closure y functools.partial)
y routers anidados con prefijo — patrones muy comunes en apps reales
(rate limiting, chequeo de rol, versionado de API por router) que
originalmente colapsaban en un único nodo indistinguible en el árbol.
"""

import functools
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI


def make_rate_limiter(times: int):
    def check() -> str:
        return f"limit={times}"

    return check


limiter_5 = make_rate_limiter(5)
limiter_10 = make_rate_limiter(10)


def require_role(role: str) -> str:
    return role


require_admin = functools.partial(require_role, role="admin")
require_editor = functools.partial(require_role, role="editor")


items_router = APIRouter(prefix="/items")


@items_router.get("/")
def list_items(
    a: Annotated[str, Depends(limiter_5)],
    b: Annotated[str, Depends(limiter_10)],
):
    return {"a": a, "b": b}


v1_router = APIRouter(prefix="/v1")
v1_router.include_router(items_router)

api_router = APIRouter(prefix="/api")
api_router.include_router(v1_router)


@api_router.get("/ping")
def ping(
    admin: Annotated[str, Depends(require_admin)],
    editor: Annotated[str, Depends(require_editor)],
):
    return {"admin": admin, "editor": editor}


app = FastAPI()
app.include_router(api_router)
