import { Card } from "./Card";
import type { TrickPlay, Player } from "../types/game";

interface TrickAreaProps {
  cardsPlayed: TrickPlay[];
  numPlayers: number;
  players?: Player[];
}

export function TrickArea({ cardsPlayed, numPlayers, players }: TrickAreaProps) {
  const isMany = numPlayers >= 6;
  const areaClass = isMany ? "trick-area trick-area-grid" : "trick-area";

  return (
    <div className={areaClass}>
      {Array.from({ length: numPlayers }, (_, i) => {
        const play = cardsPlayed.find((cp) => cp.seat === i);
        if (play) {
          const playerName = players?.[i]?.name || `P${i + 1}`;
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

