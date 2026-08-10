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

  // We want to render all players in a circle.
  const seats = [];
  for (let i = 0; i < n; i++) {
    // Offset relative to mySeat
    const seatIndex = (mySeat + i) % n;
    
    // Calculate angle in radians.
    // mySeat (i=0) is at the bottom (90 degrees, or Math.PI / 2).
    // Proceeding clockwise increases the angle.
    const angle = (Math.PI / 2) + (i * 2 * Math.PI) / n;
    
    // Radius in percentage from center. 
    // 42% keeps the seats inside the container.
    const radius = 42; 
    const x = 50 + radius * Math.cos(angle);
    const y = 50 + radius * Math.sin(angle);

    seats.push({
      seatIndex,
      player: game.players[seatIndex],
      x,
      y
    });
  }

  return (
    <div className="round-table">
      {seats.map(({ seatIndex, player, x, y }) => (
        <div 
          key={seatIndex}
          className="seat-wrapper"
          style={{
            position: "absolute",
            left: `${x}%`,
            top: `${y}%`,
            transform: "translate(-50%, -50%)",
            zIndex: 10
          }}
        >
          {player ? (
            <PlayerSeat
              player={player}
              game={game}
              isActive={game.turn_seat === seatIndex}
              position=""
            />
          ) : (
            <div className="seat-box empty">Empty</div>
          )}
        </div>
      ))}

      {/* Center — trick area */}
      <div className="seat-center" style={{
        position: "absolute",
        left: "50%",
        top: "50%",
        transform: "translate(-50%, -50%)",
        zIndex: 5
      }}>
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
    </div>
  );
}