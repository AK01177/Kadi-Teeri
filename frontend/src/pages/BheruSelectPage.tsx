import { useGameStore } from "../store/gameStore";
import {
  SUITS,
  RANKS,
  SUIT_SYMBOLS,
  SUIT_NAMES,
} from "../types/game";
import type { BheruCallMode } from "../types/game";
import { GameTable } from "../components/GameTable";
import { Hand } from "../components/Hand";
import { ActivityLog } from "../components/ActivityLog";

export function BheruSelectPage() {
  const {
    gameState,
    hand,
    seat,
    bheruTabSuit,
    setBheruTabSuit,
    selectedBheruCalls,
    addBheruCall,
    removeBheruCall,
    setSelectedBheruCalls,
    sendFn,
    showToast,
  } = useGameStore();

  if (!gameState || seat === null) return null;

  const game = gameState;
  const isMe = game.bidder_seat === seat;
  const deckCount = game.config.deck_count;
  const numPlayers = game.players.length;
  const maxBherus = Math.floor(numPlayers / 2) - 1;
  const totalBherusRequested = selectedBheruCalls.reduce((sum, call) => sum + (call.mode === "both" ? 2 : 1), 0);

  const seatLabel = (s: number) => game.players[s]?.name || `Seat ${s}`;

  // Cards in the player's hand
  const ownCards = new Set(hand.map((c) => `${c.rank}:${c.suit}`));

  const handleSelectCard = (rank: string, suit: string) => {
    // Check if already selected
    const existing = selectedBheruCalls.find(
      (c) => c.rank === rank && c.suit === suit
    );
    if (existing) {
      removeBheruCall(rank, suit);
      return;
    }

    // Determine mode
    let mode: BheruCallMode;
    if (deckCount === 1) {
      mode = "simple";
    } else {
      // 2-deck: default to "fix" if player owns one copy, otherwise "both"
      const hasCard = ownCards.has(`${rank}:${suit}`);
      mode = hasCard ? "fix" : "both";
      if (mode === "both" && totalBherusRequested + 2 > maxBherus) {
        mode = "second";
      }
    }

    const cost = mode === "both" ? 2 : 1;
    if (totalBherusRequested + cost > maxBherus) {
      showToast(`You can call at most ${maxBherus} bheru(s).`);
      return;
    }

    addBheruCall({ rank, suit, mode });
  };

  const handleModeChange = (rank: string, suit: string, mode: BheruCallMode) => {
    const existing = selectedBheruCalls.find(
      (c) => c.rank === rank && c.suit === suit
    );
    if (existing) {
      const currentCost = existing.mode === "both" ? 2 : 1;
      const newCost = mode === "both" ? 2 : 1;
      if (totalBherusRequested - currentCost + newCost > maxBherus) {
        showToast(`You can call at most ${maxBherus} bheru(s).`);
        return;
      }
      removeBheruCall(rank, suit);
      addBheruCall({ rank, suit, mode });
    }
  };

  const confirmBherus = () => {
    sendFn?.({
      type: "select_bherus",
      calls: selectedBheruCalls,
    });
    setSelectedBheruCalls([]);
  };

  const goSolo = () => {
    sendFn?.({
      type: "select_bherus",
      calls: [],
    });
    setSelectedBheruCalls([]);
  };

  return (
    <>
      <div className="status-bar">
        <span className="badge trump">
          Trump: {SUIT_SYMBOLS[game.trump_suit!]}{" "}
          {SUIT_NAMES[game.trump_suit!]}
        </span>
        <span className="badge target">Target: {game.bid_target}</span>
      </div>

      {isMe ? (
        <div className="turn-banner mine">
          Call up to {maxBherus} bheru card(s). Whoever holds them becomes your
          secret partner(s) — or go solo.
        </div>
      ) : (
        <div className="turn-banner">
          Waiting on {seatLabel(game.bidder_seat!)} to call bheru card(s)…
        </div>
      )}

      <GameTable game={game} mySeat={seat} showTrick={false} />

      <Hand cards={hand} label="Your hand" />

      {isMe && (
        <div className="panel" style={{ marginTop: "14px" }}>
          {/* Suit tabs */}
          <div className="tabs">
            {SUITS.map((s) => (
              <button
                key={s}
                className={`tab-btn${bheruTabSuit === s ? " selected" : ""}`}
                data-suit={s}
                onClick={() => setBheruTabSuit(s)}
              >
                {SUIT_SYMBOLS[s]}
              </button>
            ))}
          </div>

          {/* Rank grid */}
          <div className="rank-grid">
            {RANKS.map((r) => {
              const isOwn = ownCards.has(`${r}:${bheruTabSuit}`);
              const isSelected = selectedBheruCalls.some(
                (c) => c.rank === r && c.suit === bheruTabSuit
              );
              return (
                <button
                  key={r}
                  className={`rank-btn${isSelected ? " selected" : ""}${isOwn ? " own" : ""
                    }`}
                  onClick={() => handleSelectCard(r, bheruTabSuit)}
                >
                  {r}
                </button>
              );
            })}
          </div>

          {/* Selected calls with mode selector (2-deck only) */}
          {selectedBheruCalls.length > 0 && (
            <div style={{ marginBottom: "10px" }}>
              {selectedBheruCalls.map((call) => {
                const hasCard = ownCards.has(`${call.rank}:${call.suit}`);
                return (
                  <div
                    key={`${call.rank}:${call.suit}`}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                      padding: "8px",
                      background: "var(--panel)",
                      borderRadius: "8px",
                      marginBottom: "4px",
                      fontSize: "13px",
                    }}
                  >
                    <span style={{ color: "var(--amber)", fontFamily: "var(--font-mono)" }}>
                      {call.rank}{SUIT_SYMBOLS[call.suit]}
                    </span>

                    {deckCount === 2 && (
                      <div className="row" style={{ gap: "4px" }}>
                        {hasCard && (
                          <button
                            className={`btn btn-sm${call.mode === "fix" ? " btn-primary" : ""}`}
                            onClick={() => handleModeChange(call.rank, call.suit, "fix")}
                            style={{ padding: "4px 8px", fontSize: "11px" }}
                          >
                            Fix
                          </button>
                        )}
                        <button
                          className={`btn btn-sm${call.mode === "both" ? " btn-primary" : ""}`}
                          onClick={() => handleModeChange(call.rank, call.suit, "both")}
                          disabled={call.mode !== "both" && totalBherusRequested + 1 > maxBherus}
                          style={{ padding: "4px 8px", fontSize: "11px" }}
                        >
                          Both
                        </button>
                        <button
                          className={`btn btn-sm${call.mode === "second" ? " btn-primary" : ""}`}
                          onClick={() => handleModeChange(call.rank, call.suit, "second")}
                          style={{ padding: "4px 8px", fontSize: "11px" }}
                        >
                          2nd
                        </button>
                      </div>
                    )}

                    <button
                      className="btn btn-sm btn-ghost"
                      onClick={() => removeBheruCall(call.rank, call.suit)}
                      style={{ marginLeft: "auto", padding: "4px 8px" }}
                    >
                      ✕
                    </button>
                  </div>
                );
              })}
            </div>
          )}

          {/* Info text */}
          <p className="muted" style={{ fontSize: "12.5px", margin: "8px 0" }}>
            You must select exactly {maxBherus} bheru(s).
          </p>

          <div className="row" style={{ gap: "8px" }}>
            <button
              className="btn btn-primary"
              onClick={confirmBherus}
              disabled={totalBherusRequested !== maxBherus}
              style={{ flex: 2 }}
            >
              Confirm {maxBherus} bheru(s)
            </button>
            <button
              className="btn btn-ghost"
              onClick={goSolo}
              style={{ flex: 1 }}
            >
              Go Solo
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
