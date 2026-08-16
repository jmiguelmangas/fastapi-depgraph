from typing import Annotated

from fastapi import Depends, FastAPI


class Settings:
    pass


def get_settings() -> Settings:
    return Settings()


def get_request_id() -> str:
    return "req-abc"


async def get_db():
    yield "db-session"


def get_current_user(
    settings: Annotated[Settings, Depends(get_settings)],
    request_id: Annotated[str, Depends(get_request_id, use_cache=False)],
):
    return {"user": "jose"}


async def get_items_service(
    db: Annotated[str, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    return {"db": db}


app = FastAPI()


@app.get("/me")
def me(user: Annotated[dict, Depends(get_current_user)]):
    return user


@app.get("/items")
async def items(
    service: Annotated[dict, Depends(get_items_service)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    return service
