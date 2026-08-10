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
    return otherSeats.map((s, i) => {
      // Distribute seats: first ~1/3 on left, middle ~1/3 on top, last ~1/3 on right
      // This visually creates a clockwise flow: Bottom -> Left -> Top -> Right -> Bottom
      const groupSize = (n - 1) / 3;
      if (i < groupSize) return { seat: s, pos: "seat-left" };
      if (i < groupSize * 2) return { seat: s, pos: "seat-top" };
      return { seat: s, pos: "seat-right" };
    });
  };

  const positions = getPositions();
  const topSeats = positions.filter((p) => p.pos === "seat-top");
  const leftSeats = positions.filter((p) => p.pos === "seat-left");
  const rightSeats = positions.filter((p) => p.pos === "seat-right");

  return (
    <div className="table-grid" style={{ position: "relative" }}>
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