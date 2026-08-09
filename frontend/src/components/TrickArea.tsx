import { Card } from "./Card";
import type { TrickPlay } from "../types/game";

interface TrickAreaProps {
  cardsPlayed: TrickPlay[];
  numPlayers: number;
}

export function TrickArea({ cardsPlayed, numPlayers }: TrickAreaProps) {
  return (
    <div className="trick-area">
      {Array.from({ length: numPlayers }, (_, i) => {
        const play = cardsPlayed.find((cp) => cp.seat === i);
        if (play) {
          return <Card key={i} card={play.card} small />;
        }
        return <div key={i} className="trick-empty-slot" />;
      })}
    </div>
  );
}
