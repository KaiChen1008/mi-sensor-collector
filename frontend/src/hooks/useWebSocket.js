import { useEffect, useRef, useCallback } from "react";

export function useWebSocket(onMessage) {
  const ws = useRef(null);
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  const connect = useCallback(() => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${protocol}//${window.location.host}/ws`;
    ws.current = new WebSocket(url);

    ws.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessageRef.current(data);
      } catch {
        // ignore malformed frames
      }
    };

    ws.current.onclose = () => {
      // Reconnect after 3 s on unexpected close
      setTimeout(connect, 3000);
    };
  }, []);

  useEffect(() => {
    connect();
    const interval = setInterval(() => {
      if (ws.current?.readyState === WebSocket.OPEN) {
        ws.current.send("ping");
      }
    }, 20000);

    return () => {
      clearInterval(interval);
      ws.current?.close();
    };
  }, [connect]);
}
