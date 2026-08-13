import type { Player, GameState } from "../types/game";

interface PlayerSeatProps {
  player: Player;
  game: GameState;
  isActive: boolean;
  position: string;
  compact?: boolean;
}

export function PlayerSeat({ player, game, isActive, position, compact }: PlayerSeatProps) {
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
      <div className="nm">{player.name}</div>
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
    </div>
  );
}
