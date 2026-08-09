import { useEffect, useRef, useCallback, useState } from "react";
import type { ServerMessage } from "../types/game";

interface UseWebSocketOptions {
  onMessage: (msg: ServerMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
}

interface UseWebSocketReturn {
  send: (data: Record<string, unknown>) => void;
  isConnected: boolean;
  disconnect: () => void;
  connect: (url: string) => void;
}

const MAX_RECONNECT_DELAY = 10000;
const INITIAL_RECONNECT_DELAY = 1000;

export function useWebSocket(options: UseWebSocketOptions): UseWebSocketReturn {
  const wsRef = useRef<WebSocket | null>(null);
  const urlRef = useRef<string>("");
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const reconnectDelayRef = useRef(INITIAL_RECONNECT_DELAY);
  const intentionalCloseRef = useRef(false);
  const [isConnected, setIsConnected] = useState(false);

  const optionsRef = useRef(options);
  optionsRef.current = options;

  const cleanup = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = undefined;
    }
  }, []);

  const doConnect = useCallback(
    (url: string) => {
      cleanup();
      urlRef.current = url;
      intentionalCloseRef.current = false;

      try {
        const ws = new WebSocket(url);
        wsRef.current = ws;

        ws.onopen = () => {
          setIsConnected(true);
          reconnectDelayRef.current = INITIAL_RECONNECT_DELAY;
          optionsRef.current.onConnect?.();
        };

        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data) as ServerMessage;
            optionsRef.current.onMessage(msg);
          } catch (e) {
            console.error("Failed to parse WebSocket message:", e);
          }
        };

        ws.onclose = () => {
          setIsConnected(false);
          wsRef.current = null;
          optionsRef.current.onDisconnect?.();

          // Auto-reconnect unless intentionally closed
          if (!intentionalCloseRef.current && urlRef.current) {
            const delay = reconnectDelayRef.current;
            reconnectDelayRef.current = Math.min(
              delay * 1.5,
              MAX_RECONNECT_DELAY
            );
            reconnectTimerRef.current = setTimeout(() => {
              doConnect(urlRef.current);
            }, delay);
          }
        };

        ws.onerror = (event) => {
          console.error("WebSocket error:", event);
        };
      } catch (e) {
        console.error("Failed to create WebSocket:", e);
      }
    },
    [cleanup]
  );

  const disconnect = useCallback(() => {
    intentionalCloseRef.current = true;
    cleanup();
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
  }, [cleanup]);

  const send = useCallback((data: Record<string, unknown>) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    } else {
      console.warn("WebSocket not connected, cannot send:", data);
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      intentionalCloseRef.current = true;
      cleanup();
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [cleanup]);

  return {
    send,
    isConnected,
    disconnect,
    connect: doConnect,
  };
}
