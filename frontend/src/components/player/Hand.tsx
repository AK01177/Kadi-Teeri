import { Card } from "../card/Card";
import type { Card as CardType } from "../../types/game";

interface HandProps {
  cards: CardType[];
  legalCards?: CardType[];
  isMyTurn?: boolean;
  onPlayCard?: (card: CardType) => void;
  label?: string;
}

export function Hand({
  cards,
  legalCards,
  isMyTurn,
  onPlayCard,
  label,
}: HandProps) {
  const legalSet = new Set(
    (legalCards || []).map(
      (c) => `${c.rank}:${c.suit}:${c.deck_index}`
    )
  );

  return (
    <div className="hand-wrap">
      {label && <div className="hand-label">{label}</div>}
      <div className="hand-row">
        {cards.map((card, i) => {
          const key = `${card.rank}-${card.suit}-${card.deck_index}-${i}`;
          const isLegal =
            isMyTurn && legalSet.has(`${card.rank}:${card.suit}:${card.deck_index}`);
          return (
            <Card
              key={key}
              card={card}
              disabled={!isLegal}
              onClick={isLegal && onPlayCard ? () => onPlayCard(card) : undefined}
            />
          );
        })}
      </div>
    </div>
  );
}
