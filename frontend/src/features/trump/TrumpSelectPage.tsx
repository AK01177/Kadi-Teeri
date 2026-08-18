import { useGameStore } from "../../store/gameStore";
import { SUITS, SUIT_SYMBOLS, SUIT_NAMES } from "../../types/game";
import { GameTable } from "../../components/table/GameTable";
import { Hand } from "../../components/player/Hand";
import { ActivityLog } from "../../components/ui/ActivityLog";

export function TrumpSelectPage() {
  const {
    gameState,
    hand,
    seat,
    selectedTrump,
    setSelectedTrump,
    sendFn,
  } = useGameStore();

  if (!gameState || seat === null) return null;

  const game = gameState;
  const isMe = game.bidder_seat === seat;

  const seatLabel = (s: number) => game.players[s]?.name || `Seat ${s}`;

  const confirmTrump = () => {
    if (selectedTrump) {
      sendFn?.({ type: "select_trump", suit: selectedTrump });
      setSelectedTrump(null);
    }
  };

  return (
    <>
      <div className="status-bar">
        <span className="badge target">Target: {game.bid_target}</span>
      </div>

      {isMe ? (
        <div className="turn-banner mine">
          You won the bid at {game.bid_target}. Choose your trump suit.
        </div>
      ) : (
        <div className="turn-banner">
          Waiting on {seatLabel(game.bidder_seat!)} ({game.bid_target} points)
          to choose trump…
        </div>
      )}

      <GameTable game={game} mySeat={seat} showTrick={false} />

      <Hand cards={hand} label="Your hand" />

      {isMe && (
        <div className="panel" style={{ marginTop: "14px" }}>
          <div className="suit-grid">
            {SUITS.map((s) => (
              <button
                key={s}
                className={`suit-btn${selectedTrump === s ? " selected" : ""}`}
                data-suit={s}
                onClick={() => setSelectedTrump(s)}
              >
                {SUIT_SYMBOLS[s]}
              </button>
            ))}
          </div>
          <button
            className="btn btn-primary btn-block"
            onClick={confirmTrump}
            disabled={!selectedTrump}
          >
            Confirm {selectedTrump ? SUIT_NAMES[selectedTrump] : "trump"}
          </button>
        </div>
      )}

      <div style={{ marginTop: "14px" }}>
        <ActivityLog log={game.log} />
      </div>
    </>
  );
}
