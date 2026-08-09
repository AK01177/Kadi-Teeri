import { useGameStore } from "../store/gameStore";
import { SUIT_SYMBOLS, SUIT_NAMES } from "../types/game";
import type { Card as CardType } from "../types/game";
import { GameTable } from "../components/GameTable";
import { Hand } from "../components/Hand";
import { ActivityLog } from "../components/ActivityLog";

export function PlayingPage() {
  const { gameState, hand, seat, sendFn } = useGameStore();

  if (!gameState || seat === null) return null;

  const game = gameState;
  const myTurn = game.turn_seat === seat;

  const seatLabel = (s: number) => game.players[s]?.name || `Seat ${s}`;

  // Calculate legal plays
  const legalCards = getLegalPlays(hand, game.trick?.lead_suit ?? null);

  const handlePlayCard = (card: CardType) => {
    sendFn?.({
      type: "play_card",
      rank: card.rank,
      suit: card.suit,
      deck_index: card.deck_index,
    });
  };

  const amIBheru =
    !game.is_solo &&
    game.bherus.some(
      (b) => !b.revealed && b.holder_seat === seat
    );
  const revealedBherus = game.bherus.filter((b) => b.revealed && b.holder_seat !== undefined);

  // The server sends bherus with holder_seat only when revealed
  // We need to check if we are a secret bheru from our hand
  // This is handled by the server sending a special indicator
  // For now, we rely on the bheru being revealed or not

  return (
    <>
      <div className="status-bar">
        <span className="badge trump">
          Trump {SUIT_SYMBOLS[game.trump_suit!]}
        </span>
        <span className="badge target">Target {game.bid_target}</span>
        <span className="badge">
          Trick {game.trick_number}/
          {game.hand_sizes
            ? Math.max(...Object.values(game.hand_sizes)) + game.trick_number - 1
            : "?"}
        </span>
      </div>

      {/* Solo banner */}
      {game.is_solo && game.bidder_seat === seat && (
        <div className="secret-banner">
          You're playing solo against the table.
        </div>
      )}

      {/* Secret partner banner */}
      {amIBheru && (
        <div className="secret-banner">
          You are the secret partner!
        </div>
      )}

      {/* Revealed partner banner */}
      {revealedBherus.length > 0 && !game.is_solo && (
        <div className="secret-banner">
          Partner revealed:{" "}
          {revealedBherus.map((b) => seatLabel(b.holder_seat!)).join(", ")}
        </div>
      )}

      {/* Turn banner */}
      {myTurn ? (
        <div className="turn-banner mine">
          Your turn — play a card
          {game.trick?.lead_suit &&
            ` (${SUIT_NAMES[game.trick.lead_suit]} led)`}
        </div>
      ) : (
        <div className="turn-banner">
          Waiting on {seatLabel(game.turn_seat!)}…
        </div>
      )}

      <GameTable game={game} mySeat={seat} showTrick />

      <Hand
        cards={hand}
        legalCards={legalCards}
        isMyTurn={myTurn}
        onPlayCard={handlePlayCard}
        label={
          game.trick?.lead_suit
            ? `Your hand — must follow ${SUIT_NAMES[game.trick.lead_suit]} if you can`
            : "Your hand"
        }
      />

      <div style={{ marginTop: "14px" }}>
        <ActivityLog log={game.log} />
      </div>
    </>
  );
}

function getLegalPlays(
  hand: CardType[],
  leadSuit: string | null
): CardType[] {
  if (!leadSuit) return [...hand];
  const following = hand.filter((c) => c.suit === leadSuit);
  return following.length > 0 ? following : [...hand];
}
