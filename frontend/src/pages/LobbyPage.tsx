import { useGameStore } from "../store/gameStore";

export function LobbyPage() {
  const { gameState, isHost, roomId, sendFn, showToast } =
    useGameStore();

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
            <div className="row">
              {[4, 5, 6, 7, 8].map((n) => (
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
