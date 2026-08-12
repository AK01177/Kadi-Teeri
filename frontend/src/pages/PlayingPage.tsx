import { useGameStore } from "../store/gameStore";
import { SUIT_SYMBOLS, SUIT_NAMES } from "../types/game";
import type { Card as CardType } from "../types/game";
import { GameTable } from "../components/GameTable";
import { Hand } from "../components/Hand";
import { ActivityLog } from "../components/ActivityLog";

export function PlayingPage() {
  const { gameState, hand, seat, sendFn, trickWinner, is3DView } = useGameStore();

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

  // Check if we hold any of the unrevealed bherus
  const mySecretBherus = game.bherus.filter(b => {
    if (b.revealed) return false;
    return hand.some(c => c.rank === b.call.rank && c.suit === b.call.suit);
  });
  
  const amIBheru = !game.is_solo && mySecretBherus.length > 0;
  
  const bheruMessage = () => {
    if (mySecretBherus.some(b => b.call.mode !== "second")) {
      return "You are the secret partner!";
    }
    // All our held bherus are 'second' mode
    return "You can be the secret partner if you play it second!";
  };

  const revealedBherus = game.bherus.filter((b) => b.revealed && b.holder_seat !== undefined);

  return (
    <>
      {trickWinner && (
        <div className="trick-winner-overlay">
          <div className="winner-content">
            <h2>{trickWinner.name} gets the trick!</h2>
            <p>+{trickWinner.points} points</p>
          </div>
        </div>
      )}

      <div className="status-bar" style={{ flexWrap: "wrap" }}>
        <span className="badge trump">
          Trump {SUIT_SYMBOLS[game.trump_suit!]}
        </span>
        
        {/* Show Bheru Calls */}
        {!game.is_solo && game.bherus.length > 0 && (
          <span className="badge" style={{ background: "rgba(63, 185, 166, 0.2)", color: "var(--teal)", borderColor: "var(--teal)" }}>
            Calls: {game.bherus.map(b => `${b.call.rank}${SUIT_SYMBOLS[b.call.suit]}`).join(", ")}
          </span>
        )}

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
          {bheruMessage()}
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

      <GameTable 
        game={game} 
        mySeat={seat} 
        showTrick 
        hand={hand} 
        legalCards={legalCards} 
        isMyTurn={myTurn} 
        onPlayCard={handlePlayCard} 
      />

      {/* Spacer for 3D View to push the hand to the bottom of the screen */}
      {is3DView && <div style={{ flex: 1, minHeight: "45vh" }} />}

      <Hand
        cards={hand}
        legalCards={legalCards}
        isMyTurn={myTurn}
        onPlayCard={handlePlayCard}
        label={
          game.trick?.lead_suit
            ? `Must follow ${SUIT_NAMES[game.trick.lead_suit]} if you can`
            : "Your hand"
        }
      />

      <div style={{ marginTop: "auto" }}>
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
