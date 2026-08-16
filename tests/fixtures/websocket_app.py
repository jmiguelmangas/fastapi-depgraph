"""App with a WebSocket route alongside a regular HTTP one — regression to
confirm WebSocket doesn't leak into the tree (it has ``dependant`` and
``path`` just like an HTTP route, but no ``methods``).
"""

from fastapi import FastAPI, WebSocket

app = FastAPI()


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()


@app.get("/x")
def x():
    return {}
