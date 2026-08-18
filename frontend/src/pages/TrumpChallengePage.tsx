import { useState, useEffect, useCallback } from "react";
import { useGameStore } from "../store/gameStore";
import { SUIT_SYMBOLS, SUIT_NAMES } from "../types/game";
import { GameTable } from "../components/GameTable";
import { Hand } from "../components/Hand";
import { ActivityLog } from "../components/ActivityLog";

export function TrumpChallengePage() {
  const { gameState, hand, seat, sendFn } = useGameStore();

  const isDuelActive = gameState?.challenge_duel_seats !== null && gameState?.challenge_duel_seats !== undefined;
  const isInDuel = isDuelActive && gameState?.challenge_duel_seats!.includes(seat as number);
  const isMyTurnInDuel = isDuelActive && gameState?.turn_seat === seat && isInDuel;
  const iAmBidder = gameState?.bidder_seat === seat;

  // ─── Countdown Timer ───
  const [countdown, setCountdown] = useState<number | null>(null);

  useEffect(() => {
    if (!gameState?.challenge_deadline || isDuelActive) {
      setCountdown(null);
      return;
    }

    setCountdown(10);
    const interval = setInterval(() => {
      setCountdown((prev) => {
        if (prev === null || prev <= 1) {
          clearInterval(interval);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    
    return () => clearInterval(interval);
  }, [gameState?.challenge_deadline, isDuelActive]);

  // ─── Actions ───
  const handleChallenge = useCallback(() => {
    sendFn?.({ type: "challenge_accept" });
  }, [sendFn]);

  const handleDuelRaise = useCallback(() => {
    sendFn?.({ type: "challenge_bid" });
  }, [sendFn]);

  const handleDuelPass = useCallback(() => {
    sendFn?.({ type: "challenge_pass" });
  }, [sendFn]);

  if (!gameState || seat === null) return null;

  const game = gameState;
  const seatLabel = (s: number) => game.players[s]?.name || `Seat ${s}`;

  // ─── Phase: Duel winner picks new trump ───
  if (
    game.status === "trump" &&
    game.trump_challenge_used &&
    !game.trump_suit
  ) {
    // This case is handled by TrumpSelectPage actually,
    // but the status will be "trump" not "trump_challenge"
    return null;
  }

  return (
    <>
      <div className="status-bar">
        <span className="badge target">Target: {game.bid_target}</span>
        {game.trump_suit && (
          <span className="badge trump">
            Trump: {SUIT_SYMBOLS[game.trump_suit]}
          </span>
        )}
      </div>

      {/* ═══════ CHALLENGE COUNTDOWN PHASE ═══════ */}
      {!isDuelActive && (
        <div className="challenge-popup">
          <div className="challenge-popup-inner">
            <div className="challenge-icon">⚔️</div>
            <h2 className="challenge-title">Trump Challenge!</h2>
            <p className="challenge-desc">
              <strong>{seatLabel(game.bidder_seat!)}</strong> selects{" "}
              <span
                className={`challenge-suit ${game.trump_suit === "H" || game.trump_suit === "D"
                    ? "red"
                    : "ink"
                  }`}
              >
                {SUIT_SYMBOLS[game.trump_suit!]} {SUIT_NAMES[game.trump_suit!]}
              </span>{" "}
              as trump at{" "}
              <strong>{game.bid_target} points</strong>
            </p>

            {countdown !== null && countdown > 0 && (
              <div className="challenge-countdown">
                <div
                  className="challenge-countdown-bar"
                  style={{ width: `${(countdown / 10) * 100}%` }}
                />
                <span className="challenge-countdown-text">
                  {countdown}s remaining
                </span>
              </div>
            )}

            {!iAmBidder && countdown !== null && countdown > 0 ? (
              <button
                className="btn btn-challenge"
                onClick={handleChallenge}
              >
                🔥 Take the bid at {game.bid_target! + 20}!
              </button>
            ) : iAmBidder ? (
              <p className="challenge-waiting">
                Waiting for challengers…
              </p>
            ) : (
              <p className="challenge-waiting">Time's up!</p>
            )}
          </div>
        </div>
      )}

      {/* ═══════ DUEL PHASE ═══════ */}
      {isDuelActive && (
        <div className="challenge-duel">
          <div className="challenge-duel-inner">
            <div className="challenge-icon">⚔️</div>
            <h2 className="challenge-title">Challenge Duel!</h2>
            <p className="challenge-desc">
              <strong>{seatLabel(game.challenge_duel_seats![0])}</strong>
              {" vs "}
              <strong>{seatLabel(game.challenge_duel_seats![1])}</strong>
            </p>
            <div className="challenge-bid-display">
              Current bid:{" "}
              <strong>{game.bid_target}</strong> by{" "}
              <strong>{seatLabel(game.bidder_seat!)}</strong>
            </div>

            {isMyTurnInDuel ? (
              <div className="challenge-duel-actions">
                <button
                  className="btn btn-challenge"
                  onClick={handleDuelRaise}
                >
                  Raise to {game.bid_target! + 20}
                </button>
                <button
                  className="btn btn-pass"
                  onClick={handleDuelPass}
                >
                  Pass
                </button>
              </div>
            ) : isInDuel ? (
              <p className="challenge-waiting">
                Waiting for {seatLabel(game.turn_seat!)} to respond…
              </p>
            ) : (
              <p className="challenge-waiting">
                {seatLabel(game.turn_seat!)}'s turn to respond…
              </p>
            )}
          </div>
        </div>
      )}

      <GameTable game={game} mySeat={seat} showTrick={false} />

      <Hand cards={hand} label="Your hand" />

      <div style={{ marginTop: "14px" }}>
        <ActivityLog log={game.log} />
      </div>
    </>
  );
}
