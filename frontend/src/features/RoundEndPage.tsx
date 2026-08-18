import { useGameStore } from "../store/gameStore";
import { ScoreBar } from "../components/ui/ScoreBar";
import { ActivityLog } from "../components/ui/ActivityLog";

export function RoundEndPage() {
  const { gameState, isHost, sendFn } = useGameStore();

  if (!gameState || !gameState.round_result) return null;

  const game = gameState;
  const r = game.round_result!;
  const totalPoints = 250 * game.config.deck_count;

  const seatLabel = (s: number) => game.players[s]?.name || `Seat ${s}`;

  const biddingNames = r.bidding_seats.map((s) => seatLabel(s)).join(" & ");

  const handleNextRound = () => {
    sendFn?.({ type: "restart" });
  };

  return (
    <>
      <div className={`result-banner ${r.bidding_won ? "won" : "lost"}`}>
        <h2>{r.bidding_won ? "Contract made!" : "Contract failed"}</h2>
        <p className="muted">
          {biddingNames} captured {r.bidding_points} of {r.target} needed
          {game.is_solo ? " (solo)" : ""}.
        </p>
      </div>

      <div className="panel">
        <div className="score-bars">
          <ScoreBar
            label="Bidding side"
            value={r.bidding_points}
            max={totalPoints}
          />
          <ScoreBar
            label="Defending side"
            value={r.defending_points}
            max={totalPoints}
            variant="defending"
          />
        </div>

        <div className="player-score-list">
          {game.players.map((p) => {
            const pts = r.per_seat[p.seat] || 0;
            const won = game.wins[p.id] || 0;
            const isBidder = r.bidding_seats.includes(p.seat);
            return (
              <div key={p.id} className="player-score-row">
                <span>
                  {p.name}
                  {isBidder ? " 🌀" : ""}
                </span>
                <span className="pts">
                  {pts} pts · {won} won
                </span>
              </div>
            );
          })}
        </div>

        <button
          className="btn btn-primary btn-block"
          style={{ marginTop: "16px" }}
          onClick={handleNextRound}
          disabled={!isHost}
        >
          {isHost ? "Deal next round" : "Waiting for host to deal…"}
        </button>
      </div>

      <div style={{ marginTop: "14px" }}>
        <ActivityLog log={game.log} />
      </div>
    </>
  );
}
