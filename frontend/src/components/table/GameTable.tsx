import { PlayerSeat } from "../player/PlayerSeat";
import { TrickArea } from "../ui/TrickArea";
import type { GameState } from "../../types/game";
interface GameTableProps {
  game: GameState;
  mySeat: number;
  showTrick?: boolean;
}

export function GameTable({ game, mySeat, showTrick }: GameTableProps) {
  const n = game.players.length;
  const isLarge = n >= 6;
  const compact = n >= 6;

  // Elliptical radii — stretch horizontally for more seats
  const radiusX = isLarge ? 44 : 42;
  const radiusY = isLarge ? 38 : 42;

  const seats = [];
  for (let i = 0; i < n; i++) {
    const seatIndex = (mySeat + i) % n;
    const angle = (Math.PI / 2) + (i * 2 * Math.PI) / n;
    const x = 50 + radiusX * Math.cos(angle);
    const y = 50 + radiusY * Math.sin(angle);

    seats.push({
      seatIndex,
      player: game.players[seatIndex],
      x,
      y
    });
  }

  const tableClass = `round-table${isLarge ? " round-table-large" : ""}`;

  return (
    <div className={tableClass}>
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
              compact={compact}
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
            players={game.players}
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