// utils/websocket.js
let ws = null;

/**
 * Connect to a WebSocket for a specific conversation.
 * @param {string} conv_id - Conversation ID
 * @param {function} onMessage - Callback when a message is received
 */
export const connectWebSocket = (conv_id, onMessage, onOpen) => {
  if (!conv_id) return;

  ws = new WebSocket(`ws://localhost:8000/api/ws/${conv_id}`);

  ws.onopen = () => {
    console.log("[WebSocket] Connected:", conv_id);
    if (onOpen) onOpen();
  };

  ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    if (onMessage) onMessage(message);
  };

  ws.onclose = () => {
    console.log("[WebSocket] Closed:", conv_id);
    ws = null;
  };

  ws.onerror = (err) => {
    console.error("[WebSocket] Error:", err);
  };

  return ws;
};

/**
 * Send a JSON message to the backend via WebSocket
 */
export const sendWebSocketMessage = (message) => {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(message));
  }
};

/**
 * Close the WebSocket connection
 */
export const closeWebSocket = () => {
  if (ws) ws.close();
};
