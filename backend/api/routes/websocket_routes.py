from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from api.ws_store import ws_connections
from orchestrator.shared_state import get_shared_state

router = APIRouter()


@router.websocket("/ws/{conv_id}")
async def websocket_endpoint(websocket: WebSocket, conv_id: str):
    await websocket.accept()
    ws_connections[conv_id] = websocket
    print(f"[WS] Connected (conv={conv_id})")

    # Flush any messages the orchestrator sent before the WS was open
    shared_state = get_shared_state()
    buffered = shared_state.flush_buffer(conv_id)
    if buffered:
        print(f"[WS] Flushing {len(buffered)} buffered messages (conv={conv_id})")
        for message in buffered:
            try:
                await websocket.send_json(message)
                print(f"[WS] Flushed: {message}")
            except Exception as e:
                print(f"[WS] Failed to flush message: {e}")

    try:
        while True:
            # Keep connection alive — we only send from server to client
            # but we still need to listen to detect disconnects
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_connections.pop(conv_id, None)
        print(f"[WS] Disconnected (conv={conv_id})")