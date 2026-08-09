import { PlayerSeat } from "./PlayerSeat";
import { TrickArea } from "./TrickArea";
import type { GameState } from "../types/game";

interface GameTableProps {
  game: GameState;
  mySeat: number;
  showTrick?: boolean;
}

export function GameTable({ game, mySeat, showTrick }: GameTableProps) {
  const n = game.players.length;

  // Arrange seats around the table relative to the current player
  // For any player count, put "me" at the bottom and distribute others
  const otherSeats: number[] = [];
  for (let i = 1; i < n; i++) {
    otherSeats.push((mySeat + i) % n);
  }

  // Position assignments based on player count
  const getPositions = (): { seat: number; pos: string }[] => {
    if (n <= 4) {
      // 4 players: top, left, right
      const positions = ["seat-top", "seat-left", "seat-right"];
      return otherSeats.map((s, i) => ({
        seat: s,
        pos: positions[i] || "seat-top",
      }));
    }
    // 5-8 players: distribute around
    return otherSeats.map((s, i) => {
      const angle = i / (n - 1);
      if (angle < 0.25) return { seat: s, pos: "seat-left" };
      if (angle < 0.75) return { seat: s, pos: "seat-top" };
      return { seat: s, pos: "seat-right" };
    });
  };

  const positions = getPositions();
  const topSeats = positions.filter((p) => p.pos === "seat-top");
  const leftSeats = positions.filter((p) => p.pos === "seat-left");
  const rightSeats = positions.filter((p) => p.pos === "seat-right");

  return (
    <div className="table-grid">
      {/* Top row */}
      <div style={{ gridColumn: "2", gridRow: "1", display: "flex", gap: "8px", justifyContent: "center" }}>
        {topSeats.map(({ seat }) => (
          <PlayerSeat
            key={seat}
            player={game.players[seat]}
            game={game}
            isActive={game.turn_seat === seat}
            position=""
          />
        ))}
      </div>

      {/* Left */}
      <div style={{ gridColumn: "1", gridRow: "2", display: "flex", flexDirection: "column", gap: "4px", justifyContent: "center" }}>
        {leftSeats.map(({ seat }) => (
          <PlayerSeat
            key={seat}
            player={game.players[seat]}
            game={game}
            isActive={game.turn_seat === seat}
            position=""
          />
        ))}
      </div>

      {/* Center — trick area */}
      <div className="seat-center" style={{ gridColumn: "2", gridRow: "2" }}>
        {showTrick && game.trick ? (
          <TrickArea
            cardsPlayed={game.trick.cards_played}
            numPlayers={n}
          />
        ) : (
          <div className="trick-area">
            <span className="muted" style={{ fontSize: "12px" }}>
              Table
            </span>
          </div>
        )}
      </div>

      {/* Right */}
      <div style={{ gridColumn: "3", gridRow: "2", display: "flex", flexDirection: "column", gap: "4px", justifyContent: "center" }}>
        {rightSeats.map(({ seat }) => (
          <PlayerSeat
            key={seat}
            player={game.players[seat]}
            game={game}
            isActive={game.turn_seat === seat}
            position=""
          />
        ))}
      </div>
    </div>
  );
}
