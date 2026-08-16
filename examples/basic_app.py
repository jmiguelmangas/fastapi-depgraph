"""A more realistic example: an app with layers (config, db, auth,
services) and several routes sharing dependencies, to see the report with
some actual substance.

Run:
    PYTHONPATH=examples depgraph show basic_app:app --shared --uncached
"""

from typing import Annotated

from fastapi import Depends, FastAPI, Header


class Settings:
    db_url: str = "postgresql://localhost/demo"


def get_settings() -> Settings:
    return Settings()


async def get_db(settings: Annotated[Settings, Depends(get_settings)]):
    # simulates a per-request DB session
    yield f"session({settings.db_url})"


def get_request_id(x_request_id: Annotated[str | None, Header()] = None) -> str:
    # each request has a different id: caching it wouldn't make sense
    return x_request_id or "generated-id"


def get_current_user(
    db: Annotated[str, Depends(get_db)],
    request_id: Annotated[str, Depends(get_request_id, use_cache=False)],
):
    return {"id": 1, "request_id": request_id}


def require_admin(user: Annotated[dict, Depends(get_current_user)]):
    if user["id"] != 1:
        raise PermissionError("not an admin")
    return user


async def get_users_service(db: Annotated[str, Depends(get_db)]):
    return {"db": db, "service": "users"}


async def get_orders_service(
    db: Annotated[str, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    return {"db": db, "settings": settings.db_url, "service": "orders"}


app = FastAPI()


@app.get("/users/me")
def read_current_user(user: Annotated[dict, Depends(get_current_user)]):
    return user


@app.get("/users")
async def list_users(service: Annotated[dict, Depends(get_users_service)]):
    return service


@app.get("/orders")
async def list_orders(service: Annotated[dict, Depends(get_orders_service)]):
    return service


@app.post("/orders")
async def create_order(
    service: Annotated[dict, Depends(get_orders_service)],
    user: Annotated[dict, Depends(get_current_user)],
):
    return {"order": "created", "by": user, "via": service}


@app.delete("/orders/{order_id}")
async def delete_order(
    order_id: int,
    admin: Annotated[dict, Depends(require_admin)],
    service: Annotated[dict, Depends(get_orders_service)],
):
    return {"deleted": order_id, "by": admin, "via": service}
