import { useState, useEffect } from "react";
import { useGameStore } from "../store/gameStore";

const API_BASE =
  import.meta.env.VITE_API_URL || "";

export function LobbyPage() {
  const { gameState, isHost, roomId, sendFn, showToast, connectionMode } =
    useGameStore();

  const [lanInfo, setLanInfo] = useState<{ lan_ips: string[]; port: number } | null>(null);

  // Fetch LAN info if in local mode
  useEffect(() => {
    if (connectionMode === "local" && !lanInfo) {
      fetch(`${API_BASE}/api/network-info`)
        .then((r) => r.json())
        .then((data) => setLanInfo(data))
        .catch(() => setLanInfo(null));
    }
  }, [connectionMode, lanInfo]);

  if (!gameState || !roomId) return null;

  const game = gameState;
  const config = game.config;

  const copyCode = () => {
    if (navigator.clipboard && roomId) {
      navigator.clipboard
        .writeText(roomId)
        .then(() => showToast("Room code copied!"))
        .catch(() => showToast(roomId));
    } else {
      showToast(roomId || "");
    }
  };

  const lanUrl = lanInfo?.lan_ips?.[0]
    ? `http://${lanInfo.lan_ips[0]}:${lanInfo.port}`
    : null;

  const copyLanLink = () => {
    if (lanUrl && navigator.clipboard) {
      const fullLink = `${lanUrl} → Code: ${roomId}`;
      navigator.clipboard
        .writeText(fullLink)
        .then(() => showToast("Link copied!"))
        .catch(() => showToast(fullLink));
    }
  };

  const setPlayerCount = (count: number) => {
    sendFn?.({ type: "configure", player_count: count });
  };

  const setDeckCount = (count: number) => {
    sendFn?.({ type: "configure", deck_count: count });
  };

  const startGame = () => {
    sendFn?.({ type: "start_game" });
  };

  const canStart =
    isHost && game.players.length === config.player_count;

  return (
    <div className="panel">
      <div className="eyebrow">Room code</div>
      <h2
        style={{
          fontSize: "34px",
          letterSpacing: ".06em",
          fontFamily: "var(--font-mono)",
          color: "var(--gold)",
          margin: "6px 0 14px",
        }}
      >
        {roomId}
      </h2>
      <div className="row" style={{ marginBottom: "16px" }}>
        <button className="btn btn-teal btn-block" onClick={copyCode}>
          Copy code to share
        </button>
      </div>

      {/* LAN share info */}
      {connectionMode === "local" && lanUrl && (
        <div className="lan-share-strip">
          <div style={{ fontSize: "11px", color: "var(--muted)", fontFamily: "var(--font-mono)", textTransform: "uppercase", letterSpacing: ".08em", marginBottom: "4px" }}>
            Local Network
          </div>
          <div className="lan-url-display" onClick={copyLanLink} role="button" style={{ fontSize: "13px", padding: "6px 10px" }}>
            {lanUrl} → <strong>{roomId}</strong>
          </div>
          <button className="btn btn-sm btn-teal" onClick={copyLanLink} style={{ width: "100%", marginTop: "6px" }}>
            Copy link + code
          </button>
        </div>
      )}

      {/* Configuration (host only) */}
      {isHost && (
        <div
          className="panel"
          style={{
            background: "var(--panel-2)",
            marginBottom: "16px",
          }}
        >
          <div className="eyebrow" style={{ marginBottom: "10px" }}>
            Game settings
          </div>

          {/* Player count */}
          <div style={{ marginBottom: "12px" }}>
            <div
              style={{
                fontSize: "13px",
                color: "var(--muted)",
                marginBottom: "6px",
              }}
            >
              Players
            </div>
            <div className="player-count-grid">
              {[4, 5, 6, 7, 8, 9, 10, 11, 12].map((n) => (
                <button
                  key={n}
                  className={`btn btn-sm${
                    config.player_count === n ? " btn-primary" : ""
                  }`}
                  onClick={() => setPlayerCount(n)}
                  disabled={n < game.players.length}
                >
                  {n}
                </button>
              ))}
            </div>
            {config.player_count >= 9 && (
              <div style={{ fontSize: "11px", color: "var(--teal)", marginTop: "6px" }}>
                ℹ️ 2 decks required for 9+ players
              </div>
            )}
          </div>

          {/* Deck count */}
          <div>
            <div
              style={{
                fontSize: "13px",
                color: "var(--muted)",
                marginBottom: "6px",
              }}
            >
              Decks
            </div>
            <div className="row">
              <button
                className={`btn btn-sm${
                  config.deck_count === 1 ? " btn-primary" : ""
                }`}
                onClick={() => setDeckCount(1)}
                style={{ flex: 1 }}
                disabled={config.player_count >= 9}
              >
                1 Deck (52 cards)
              </button>
              <button
                className={`btn btn-sm${
                  config.deck_count === 2 ? " btn-primary" : ""
                }`}
                onClick={() => setDeckCount(2)}
                style={{ flex: 1 }}
              >
                2 Decks (104 cards)
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Player list */}
      <div className="eyebrow" style={{ marginBottom: "8px" }}>
        Players ({game.players.length}/{config.player_count})
      </div>
      <div className="seat-list">
        {Array.from({ length: config.player_count }, (_, i) => {
          const p = game.players[i];
          if (p) {
            return (
              <div key={p.id} className="seat-item">
                <div className="seat-avatar">
                  {(p.name[0] || "?").toUpperCase()}
                </div>
                <span>
                  {p.name}
                  {p.id ===
                  useGameStore.getState().playerId
                    ? " (you)"
                    : ""}
                </span>
                {p.is_host && <span className="host-tag">HOST</span>}
                {isHost && p.id !== useGameStore.getState().playerId && (
                  <button
                    className="btn btn-sm btn-ghost"
                    onClick={() => sendFn?.({ type: "remove_player", target_player_id: p.id })}
                    style={{ marginLeft: "auto", color: "var(--red)", fontSize: "11px", padding: "4px 8px" }}
                  >
                    Kick
                  </button>
                )}
              </div>
            );
          }
          return (
            <div key={`empty-${i}`} className="seat-item empty">
              <div className="seat-avatar">?</div>
              <span>Waiting for a player…</span>
            </div>
          );
        })}
      </div>

      {/* Start button */}
      {isHost ? (
        <button
          className="btn btn-primary btn-block"
          onClick={startGame}
          disabled={!canStart}
        >
          {canStart
            ? "Deal the first round"
            : `Need ${config.player_count} players to start`}
        </button>
      ) : (
        <div
          className="muted"
          style={{ textAlign: "center", fontSize: "13px" }}
        >
          Waiting for the host to start the game…
        </div>
      )}
    </div>
  );
}

