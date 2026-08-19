import { useEffect, useRef, useCallback, useState } from "react";
import type { ServerMessage } from "../types/game";

interface UseWebSocketOptions {
  onMessage: (msg: ServerMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
}

interface UseWebSocketReturn {
  send: (data: Record<string, unknown>, quiet?: boolean) => boolean;
  isConnected: boolean;
  disconnect: () => void;
  connect: (url: string) => void;
  reconnect: (url?: string) => boolean;
}

const MAX_RECONNECT_DELAY = 3000;
const INITIAL_RECONNECT_DELAY = 500;
const PING_INTERVAL_MS = 3000;
const PONG_TIMEOUT_MS = 7000;

export function useWebSocket(options: UseWebSocketOptions): UseWebSocketReturn {
  const wsRef = useRef<WebSocket | null>(null);
  const urlRef = useRef<string>("");
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const pingTimerRef = useRef<ReturnType<typeof setInterval> | undefined>(undefined);
  
  const reconnectDelayRef = useRef(INITIAL_RECONNECT_DELAY);
  const intentionalCloseRef = useRef(false);
  const [isConnected, setIsConnected] = useState(false);
  const lastPongRef = useRef(0);
  const lastPingSentRef = useRef(0);
  const lastSentPingMsRef = useRef(0);
  const lastSentPingTimeRef = useRef(0);

  const optionsRef = useRef(options);
  optionsRef.current = options;

  const cleanup = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = undefined;
    }
    if (pingTimerRef.current) {
      clearInterval(pingTimerRef.current);
      pingTimerRef.current = undefined;
    }
  }, []);

  const send = useCallback((data: Record<string, unknown>, quiet = false) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
      return true;
    } else {
      if (!quiet) {
        console.warn("WebSocket not connected, cannot send:", data);
      }
      return false;
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
          lastPongRef.current = Date.now();

          // Start heartbeat
          pingTimerRef.current = setInterval(() => {
            lastPingSentRef.current = Date.now();
            send({ type: "ping" }, true);
            
            // If we haven't received a pong in a while since the last ping
            // We allow missing 1 pong, but if we miss 2 (more than 7 seconds), we disconnect.
            if (lastPongRef.current > 0 && Date.now() - lastPongRef.current > PONG_TIMEOUT_MS) {
              console.warn("WebSocket ping timeout, forcefully reconnecting...");
              ws.close(); // Triggers onclose which handles reconnection
            }
          }, PING_INTERVAL_MS);
        };

        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data) as ServerMessage;
            if (msg.type === "pong") {
              const pingMs = Date.now() - lastPingSentRef.current;
              lastPongRef.current = Date.now();
              // Only send ping update if we have a reasonable ping value
              if (pingMs >= 0 && pingMs < 5000) {
                 const prev = lastSentPingMsRef.current;
                 const now = Date.now();
                 // Throttle updates: only if it changed by >20ms or it's been 10 seconds
                 if (Math.abs(pingMs - prev) > 20 || (now - lastSentPingTimeRef.current > 10000)) {
                    send({ type: "update_ping", ping_ms: pingMs }, true);
                    lastSentPingMsRef.current = pingMs;
                    lastSentPingTimeRef.current = now;
                 }
              }
              return; // Handled heartbeat, don't pass to app
            }
            optionsRef.current.onMessage(msg);
          } catch (e) {
            console.error("Failed to parse WebSocket message:", e);
          }
        };

        ws.onclose = () => {
          setIsConnected(false);
          wsRef.current = null;
          cleanup();
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
    [cleanup, send]
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

  // Network event listeners for immediate reconnection
  useEffect(() => {
    const handleNetworkChange = () => {
      // If we come back online and we're supposed to be connected but aren't, connect immediately
      if (navigator.onLine && !intentionalCloseRef.current && urlRef.current && (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN)) {
        console.log("Network restored, reconnecting instantly...");
        doConnect(urlRef.current);
      }
    };
    
    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible" && !intentionalCloseRef.current && urlRef.current) {
        // If we come back to the foreground, check if connection is dead
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN || (Date.now() - lastPongRef.current > PONG_TIMEOUT_MS)) {
           console.log("App foregrounded, reconnecting instantly...");
           doConnect(urlRef.current);
        }
      }
    };

    window.addEventListener("online", handleNetworkChange);
    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      window.removeEventListener("online", handleNetworkChange);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [doConnect]);

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

  const reconnect = useCallback(
    (targetUrl?: string) => {
      const url = targetUrl || urlRef.current;
      if (!url) return false;
      cleanup();
      if (wsRef.current) {
        try {
          wsRef.current.close();
        } catch {
          // ignore
        }
        wsRef.current = null;
      }
      doConnect(url);
      return true;
    },
    [cleanup, doConnect]
  );

  return {
    send,
    isConnected,
    disconnect,
    connect: doConnect,
    reconnect,
  };
}
