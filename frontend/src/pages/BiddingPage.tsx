import { useGameStore } from "../store/gameStore";
import { GameTable } from "../components/GameTable";
import { Hand } from "../components/Hand";
import { ActivityLog } from "../components/ActivityLog";

export function BiddingPage() {
  const { gameState, hand, seat, pendingBid, setPendingBid, sendFn } =
    useGameStore();

  if (!gameState || seat === null || !gameState.bidding) return null;

  const game = gameState;
  const b = game.bidding!;
  const myTurn = game.turn_seat === seat;
  const minReq = Math.max(150, b.highest_bid + 5);
  const maxBid = 250 * game.config.deck_count;

  // Initialize pending bid
  const currentBid = pendingBid ?? minReq;

  const seatLabel = (s: number) => game.players[s]?.name || `Seat ${s}`;

  const adjustBid = (delta: number) => {
    const newVal = Math.max(minReq, Math.min(maxBid, currentBid + delta));
    setPendingBid(newVal);
  };

  const confirmBid = () => {
    sendFn?.({ type: "bid", amount: currentBid });
    setPendingBid(null);
  };

  const passBid = () => {
    sendFn?.({ type: "pass" });
    setPendingBid(null);
  };

  return (
    <>
      <div className="status-bar">
        <span className="badge">Dealer: {seatLabel(game.dealer)}</span>
        <span className="badge">Bidding phase</span>
      </div>

      {myTurn ? (
        <div className="turn-banner mine">
          Your turn to bid — highest so far:{" "}
          {b.highest_bid || "none"}
          {b.highest_bidder_seat !== null &&
            ` by ${seatLabel(b.highest_bidder_seat)}`}
        </div>
      ) : (
        <div className="turn-banner">
          Waiting on {seatLabel(game.turn_seat!)} to bid or pass…
          (highest: {b.highest_bid || "none"}
          {b.highest_bidder_seat !== null &&
            ` by ${seatLabel(b.highest_bidder_seat)}`}
          )
        </div>
      )}

      <GameTable game={game} mySeat={seat} showTrick={false} />

      <Hand cards={hand} label="Your hand" />

      {myTurn && (
        <div className="panel" style={{ marginTop: "14px" }}>
          <div className="stepper">
            <button
              className="step-btn"
              onClick={() => adjustBid(-5)}
              disabled={currentBid <= minReq}
            >
              −
            </button>
            <div className="amount">{currentBid}</div>
            <button
              className="step-btn"
              onClick={() => adjustBid(5)}
              disabled={currentBid >= maxBid}
            >
              +
            </button>
          </div>
          <div className="row">
            <button
              className="btn btn-primary btn-block"
              onClick={confirmBid}
            >
              Bid {currentBid}
            </button>
          </div>
          <div className="row" style={{ marginTop: "8px" }}>
            <button className="btn btn-ghost btn-block" onClick={passBid}>
              Pass
            </button>
          </div>
        </div>
      )}

      <div style={{ marginTop: "14px" }}>
        <ActivityLog log={game.log} />
      </div>
    </>
  );
}
