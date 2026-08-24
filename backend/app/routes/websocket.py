"""
WebSocket endpoint for live alert streaming.
/ws/live — Pushes new alerts to dashboard in real time.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.websocket_manager import ws_manager

router = APIRouter()


@router.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    """
    Dashboard connects here to receive live alert pushes.
    Each message is a JSON-serialized Alert object.
    """
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive — wait for client messages (pings/close)
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
