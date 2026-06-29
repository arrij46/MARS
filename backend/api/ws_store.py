# api/ws_store.py
from fastapi import WebSocket

# dict[conv_id -> WebSocket]
ws_connections: dict[str, WebSocket] = {}
