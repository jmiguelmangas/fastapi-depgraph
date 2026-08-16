"""App con una ruta WebSocket junto a una HTTP normal — regresión para
confirmar que WebSocket no se cuela en el árbol (tiene ``dependant`` y
``path`` igual que una ruta HTTP, pero no ``methods``).
"""

from fastapi import FastAPI, WebSocket

app = FastAPI()


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()


@app.get("/x")
def x():
    return {}
