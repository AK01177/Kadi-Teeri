import type { Player, GameState } from "../types/game";

interface PlayerSeatProps {
  player: Player;
  game: GameState;
  isActive: boolean;
  position: string;
}

export function PlayerSeat({ player, game, isActive, position }: PlayerSeatProps) {
  return (
    <div className={`seat-box ${position}${isActive ? " active" : ""}`}>
      <div className="nm">{player.name}</div>
      <div className="tags">
        {game.dealer === player.seat && (
          <span className="mini-tag dealer">Dealer</span>
        )}
        {game.bidder_seat === player.seat && (
          <span className="mini-tag bidder">Bidder</span>
        )}
        {game.bherus
          .filter((b) => b.revealed && b.holder_seat === player.seat)
          .map((_, i) => (
            <span key={i} className="mini-tag partner">
              Bheru
            </span>
          ))}
        {!player.is_connected && (
          <span className="mini-tag" style={{ borderColor: "var(--danger)", color: "var(--danger)" }}>
            Offline
          </span>
        )}
      </div>
      {game.status === "playing" && (
        <div style={{ fontSize: "10px", color: "var(--muted)", fontFamily: "var(--font-mono)", display: "flex", gap: "8px", justifyContent: "center" }}>
          <span>{game.hand_sizes?.[player.seat] ?? 0} cards</span>
          <span>{game.captured_points?.[player.seat] ?? 0} pts</span>
        </div>
      )}
    </div>
  );
}
