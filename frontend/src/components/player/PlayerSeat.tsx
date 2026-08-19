import { useState, useEffect } from "react";
import type { Player, GameState } from "../../types/game";
import { useGameStore } from "../../store/gameStore";

interface PlayerSeatProps {
  player: Player;
  game: GameState;
  isActive: boolean;
  position: string;
  compact?: boolean;
}

export function PlayerSeat({ player, game, isActive, position, compact }: PlayerSeatProps) {
  const myPlayerId = useGameStore((s) => s.playerId);
  const sendFn = useGameStore((s) => s.sendFn);

  const [cooldownSec, setCooldownSec] = useState(0);

  useEffect(() => {
    if (cooldownSec <= 0) return;
    const timer = setInterval(() => {
      setCooldownSec((prev) => (prev <= 1 ? 0 : prev - 1));
    }, 1000);
    return () => clearInterval(timer);
  }, [cooldownSec]);

  const handleNudge = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (cooldownSec > 0 || !sendFn) return;
    sendFn({ type: "nudge_player", target_player_id: player.id });
    setCooldownSec(5);
  };

  const showNudgeButton =
    isActive &&
    Boolean(myPlayerId) &&
    player.id !== myPlayerId &&
    player.is_connected &&
    game.status !== "lobby" &&
    game.status !== "round_end";

  const cls = [
    "seat-box",
    position,
    isActive ? "active" : "",
    compact ? "compact" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={cls}>
      <div className="nm">
        {player.name}
        {player.ping_ms !== undefined && (
          <span className="ping-indicator" style={{
            fontSize: "10px",
            marginLeft: "6px",
            color: player.ping_ms < 60 ? "#4ade80" : player.ping_ms < 150 ? "#fbbf24" : "#ef4444",
            fontWeight: "bold",
            display: "inline-block",
            verticalAlign: "middle",
          }}>
            {player.ping_ms}ms
          </span>
        )}
      </div>
      <div className="tags">
        {game.dealer === player.seat && (
          <span className="mini-tag dealer">
            {compact ? "D" : "Dealer"}
          </span>
        )}
        {game.bidder_seat === player.seat && (
          <span className="mini-tag bidder">
            {compact ? "B" : "Bidder"}
          </span>
        )}
        {game.bherus
          .filter((b) => b.revealed && b.holder_seat === player.seat)
          .map((_, i) => (
            <span key={i} className="mini-tag partner">
              {compact ? "P" : "Bheru"}
            </span>
          ))}
        {!player.is_connected && (
          <span className="mini-tag" style={{ borderColor: "var(--danger)", color: "var(--danger)" }}>
            {compact ? "⚠" : "Offline"}
          </span>
        )}
      </div>
      {game.status === "playing" && (
        <div className="seat-stats">
          <span>{game.hand_sizes?.[player.seat] ?? 0}{compact ? "🃏" : " cards"}</span>
          <span>{game.captured_points?.[player.seat] ?? 0}{compact ? "p" : " pts"}</span>
        </div>
      )}
      {showNudgeButton && (
        <button
          className="nudge-btn"
          onClick={handleNudge}
          disabled={cooldownSec > 0}
          aria-label={`Nudge ${player.name}`}
          title={`Nudge ${player.name}`}
          style={{
            marginTop: "4px",
            fontSize: "10px",
            padding: "2px 6px",
            borderRadius: "4px",
            background: "rgba(234, 179, 8, 0.2)",
            border: "1px solid rgba(234, 179, 8, 0.5)",
            color: "#fde047",
            cursor: cooldownSec > 0 ? "not-allowed" : "pointer",
            display: "inline-flex",
            alignItems: "center",
            gap: "3px",
            fontWeight: "bold",
            transition: "all 0.2s ease",
          }}
        >
          <span>🔔</span>
          <span>{cooldownSec > 0 ? `${cooldownSec}s` : "Nudge"}</span>
        </button>
      )}
    </div>
  );
}
