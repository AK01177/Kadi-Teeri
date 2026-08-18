import { useEffect, useCallback } from "react";
import { useGameStore } from "./store/gameStore";
import { useWebSocket } from "./hooks/useWebSocket";
import type { ServerMessage } from "./types/game";

import { HomePage } from "./features/HomePage";
import { LobbyPage } from "./features/LobbyPage";
import { BiddingPage } from "./features/BiddingPage";
import { TrumpSelectPage } from "./features/trump/TrumpSelectPage";
import { TrumpChallengePage } from "./features/trump/TrumpChallengePage";
import { BheruSelectPage } from "./features/BheruSelectPage";
import { PlayingPage } from "./features/PlayingPage";
import { RoundEndPage } from "./features/RoundEndPage";

const WS_BASE =
  import.meta.env.VITE_WS_URL ||
  `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}`;

function App() {
  const {
    roomId,
    gameState,
    toast,
    clearToast,
    setIdentity,
    setGameState,
    setConnected,
    setSendFn,
    showToast,
    leaveRoom,
    is3DView,
    setIs3DView,
    isRefreshing,
    setIsRefreshing,
    isReconnecting,
    setIsReconnecting,
  } = useGameStore();

  const onMessage = useCallback(
    (msg: ServerMessage) => {
      switch (msg.type) {
        case "welcome":
          setIdentity({
            playerId: msg.player_id,
            roomId: msg.room_id,
            seat: msg.seat,
            isHost: msg.is_host,
          });
          // Save session for reconnect
          localStorage.setItem(
            "kadi_session",
            JSON.stringify({
              roomId: msg.room_id,
              playerId: msg.player_id,
              playerName: useGameStore.getState().playerName,
            })
          );
          break;
        case "game_state":
          setGameState(msg.game, msg.hand);
          break;
        case "trick_winner":
          useGameStore.getState().setTrickWinner({
            name: msg.name as string,
            points: msg.points as number,
          });
          break;
        case "ping_update":
          useGameStore.getState().setPingUpdate(msg.player_id as string, msg.ping_ms as number);
          break;
        case "error":
          showToast(msg.error);
          setIsRefreshing(false);
          setIsReconnecting(false);
          break;
      }
    },
    [setIdentity, setGameState, showToast, setIsRefreshing, setIsReconnecting]
  );

  const { send, isConnected, connect, disconnect } = useWebSocket({
    onMessage,
    onConnect: () => setConnected(true),
    onDisconnect: () => setConnected(false),
  });

  // Store the send function in zustand so pages can use it
  useEffect(() => {
    setSendFn(send);
  }, [send, setSendFn]);

  // Auto-rejoin on reconnect
  useEffect(() => {
    if (isConnected) {
      const state = useGameStore.getState();
      // If we already have a playerId and gameState, it means we were in a session and just reconnected
      if (state.playerId && state.roomId && state.gameState && send) {
        send({
          type: "rejoin",
          name: state.playerName || "Player",
          player_id: state.playerId,
        });
      }
    }
  }, [isConnected, send]);

  // Expose connect function for HomePage
  useEffect(() => {
    (window as any).__kadiConnect = (
      roomIdToJoin: string,
      playerId: string | null,
      name: string
    ) => {
      const wsUrl = `${WS_BASE}/ws/${roomIdToJoin}`;
      connect(wsUrl);

      // Send join message once connected
      const interval = setInterval(() => {
        const joinMsg: Record<string, unknown> = {
          type: playerId ? "rejoin" : "join",
          name,
        };
        if (playerId) {
          joinMsg.player_id = playerId;
        }
        // Cast to any since the type signature in the store might not include the quiet flag or boolean return
        const success = (send as any)(joinMsg, true);
        if (success) {
          clearInterval(interval);
        }
      }, 100);

      // Timeout after 5 seconds
      setTimeout(() => clearInterval(interval), 5000);
    };

    return () => {
      delete (window as any).__kadiConnect;
    };
  }, [connect, send]);

  // Try to reconnect from saved session on mount
  useEffect(() => {
    try {
      const saved = localStorage.getItem("kadi_session");
      if (saved && !roomId) {
        const session = JSON.parse(saved);
        if (session.roomId && session.playerId && session.playerName) {
          const wsUrl = `${WS_BASE}/ws/${session.roomId}`;
          connect(wsUrl);

          // Send rejoin once connected
          setTimeout(() => {
            send({
              type: "rejoin",
              name: session.playerName,
              player_id: session.playerId,
            });
          }, 500);
        }
      }
    } catch {
      // No saved session
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleRefresh = useCallback(() => {
    if (isRefreshing || isReconnecting) return;
    if (!isConnected) {
      showToast("Cannot refresh: connection is offline.");
      return;
    }
    setIsRefreshing(true);
    const sent = send({ type: "fetch_state" });
    if (!sent) {
      setIsRefreshing(false);
      showToast("Failed to send refresh request.");
      return;
    }
    setTimeout(() => {
      if (useGameStore.getState().isRefreshing) {
        setIsRefreshing(false);
        showToast("Refresh request timed out.");
      }
    }, 4000);
  }, [isRefreshing, isReconnecting, isConnected, send, setIsRefreshing, showToast]);

  const handleLeave = () => {
    disconnect();
    leaveRoom();
    localStorage.removeItem("kadi_session");
  };

  // Copy room code
  const copyCode = () => {
    if (navigator.clipboard && roomId) {
      navigator.clipboard
        .writeText(roomId)
        .then(() => showToast("Code copied!"))
        .catch(() => showToast(roomId));
    } else {
      showToast(roomId || "");
    }
  };

  // Render the appropriate page based on game status
  const renderPage = () => {
    if (!roomId || !gameState) {
      return <HomePage />;
    }

    switch (gameState.status) {
      case "lobby":
        return <LobbyPage />;
      case "bidding":
        return <BiddingPage />;
      case "trump":
        return <TrumpSelectPage />;
      case "trump_challenge":
        return <TrumpChallengePage />;
      case "bheru":
        return <BheruSelectPage />;
      case "playing":
        return <PlayingPage />;
      case "round_end":
        return <RoundEndPage />;
      default:
        return <div className="panel">Loading…</div>;
    }
  };

  const wins = gameState?.wins || {};

  return (
    <div id="app">
      {/* UI Overlay for reconnecting state */}
      {!isConnected && roomId && (
        <div style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          backgroundColor: "var(--danger)",
          color: "white",
          textAlign: "center",
          padding: "8px",
          zIndex: 9999,
          fontWeight: "bold",
          fontSize: "14px",
          boxShadow: "0 2px 10px rgba(0,0,0,0.5)"
        }}>
          Reconnecting to game server...
        </div>
      )}
      {/* Top bar (shown when in a room) */}
      {roomId && gameState && (
        <div className="topbar">
          <span
            className="code-chip"
            role="button"
            onClick={copyCode}
            style={{ cursor: "pointer" }}
          >
            {roomId}
          </span>
          <div className="leaderboard">
            {gameState.players.map((p) => {
              const w = wins[p.id] || 0;
              const isMe =
                p.id === useGameStore.getState().playerId;
              return (
                <span
                  key={p.id}
                  className={`lb-pill${isMe ? " me" : ""}`}
                >
                  {p.name} · {w}
                </span>
              );
            })}
          </div>
          <span className="spacer" />
          <button
            className="btn btn-ghost btn-sm"
            onClick={handleRefresh}
            disabled={isRefreshing || isReconnecting}
            title="Re-fetch latest room state & re-render UI"
          >
            {isRefreshing ? "Refreshing…" : "Refresh"}
          </button>
          <button
            className="btn btn-ghost btn-sm"
            onClick={() => setIs3DView(!is3DView)}
            title="Toggle 3D View"
          >
            {is3DView ? "2D View" : "3D View"}
          </button>
          {!isConnected && (
            <span
              style={{
                color: "var(--danger)",
                fontSize: "11px",
                fontFamily: "var(--font-mono)",
              }}
            >
              Reconnecting…
            </span>
          )}
          <button className="btn btn-ghost btn-sm" onClick={handleLeave}>
            Leave
          </button>
        </div>
      )}

      {renderPage()}

      {/* Toast */}
      {toast && (
        <div className="toast" onClick={clearToast}>
          {toast}
        </div>
      )}
    </div>
  );
}

export default App;
