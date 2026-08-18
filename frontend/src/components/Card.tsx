import type { Card as CardType } from "../types/game";

interface CardProps {
  card: CardType;
  small?: boolean;
  disabled?: boolean;
  onClick?: () => void;
}

export function Card({ card, small, disabled, onClick }: CardProps) {
  const suitNameMap: Record<string, string> = {
    C: "clubs",
    D: "diamonds",
    H: "hearts",
    S: "spades",
  };
  const suitName = suitNameMap[card.suit];
  const imgSrc = `/CardsPNG/${suitName}_${card.rank}.png`;
  const isTeeri = card.rank === "3" && card.suit === "S";

  return (
    <button
      type="button"
      className={`card${small ? " card-sm" : ""}${disabled ? " disabled" : ""}`}
      disabled={disabled}
      onClick={disabled ? undefined : onClick}
    >
      <div className={`card-face ${isTeeri ? " teeri" : ""}`} style={{ background: 'transparent', boxShadow: 'none' }}>
        <img
          src={imgSrc}
          alt={`${card.rank} of ${suitName}`}
          style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block' }}
        />
        {isTeeri && <span className="teeri-badge">30</span>}
      </div>
    </button>
  );
}

export function CardBack({ small }: { small?: boolean }) {
  return (
    <div className={`card${small ? " card-sm" : ""}`}>
      <div className="card-face" style={{ background: 'transparent', boxShadow: 'none' }}>
        <img
          src="/CardsPNG/back_light.png"
          alt="Card Back"
          style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block' }}
        />
      </div>
    </div>
  );
}
