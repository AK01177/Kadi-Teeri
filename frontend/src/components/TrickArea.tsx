import { Card } from "./Card";
import type { TrickPlay, Player } from "../types/game";

interface TrickAreaProps {
  cardsPlayed: TrickPlay[];
  numPlayers: number;
  players?: Player[];
}

export function TrickArea({ cardsPlayed, numPlayers, players }: TrickAreaProps) {
  return (
    <div className="trick-area">
      {Array.from({ length: numPlayers }, (_, i) => {
        const play = cardsPlayed.find((cp) => cp.seat === i);
        if (play) {
          const playerName = players?.[i]?.name || `Player ${i + 1}`;
          return (
            <div key={i} className="trick-card-wrapper">
              <Card card={play.card} small />
              <div className="trick-card-player-label">{playerName}</div>
            </div>
          );
        }
        return <div key={i} className="trick-empty-slot" />;
      })}
    </div>
  );
}
