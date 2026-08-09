import { SUIT_SYMBOLS, SUIT_COLORS } from "../types/game";
import type { Card as CardType } from "../types/game";

interface CardProps {
  card: CardType;
  small?: boolean;
  disabled?: boolean;
  onClick?: () => void;
}

export function Card({ card, small, disabled, onClick }: CardProps) {
  const color = SUIT_COLORS[card.suit] || "ink";
  const sym = SUIT_SYMBOLS[card.suit] || card.suit;
  const isTeeri = card.rank === "3" && card.suit === "S";

  return (
    <button
      type="button"
      className={`card${small ? " card-sm" : ""}${disabled ? " disabled" : ""}`}
      disabled={disabled}
      onClick={disabled ? undefined : onClick}
    >
      <div className={`card-face ${color}${isTeeri ? " teeri" : ""}`}>
        <span className="pip pip-tl">
          {card.rank}
          <br />
          {sym}
        </span>
        <span className="pip-center">{sym}</span>
        <span className="pip pip-br">
          {card.rank}
          <br />
          {sym}
        </span>
        {isTeeri && <span className="teeri-badge">30</span>}
      </div>
    </button>
  );
}

export function CardBack({ small }: { small?: boolean }) {
  return (
    <div className={`card${small ? " card-sm" : ""}`}>
      <div className="card-back" />
    </div>
  );
}
