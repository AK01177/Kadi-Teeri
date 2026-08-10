import { useEffect, useState } from "react";
import { CardBack } from "./Card";

interface DealingAnimationProps {
  onComplete: () => void;
}

export function DealingAnimation({ onComplete }: DealingAnimationProps) {
  const [cards, setCards] = useState<{ id: number; target: string; delay: number }[]>([]);

  useEffect(() => {
    // Generate 24 cards flying to the seats to simulate dealing
    const directions = ["bottom", "left", "top", "right"];
    const newCards = Array.from({ length: 24 }).map((_, i) => ({
      id: i,
      target: directions[i % 4],
      delay: i * 0.08, // 80ms between each card
    }));
    setCards(newCards);

    // Complete after last card finishes animating (1.92s + 0.5s animation)
    const timer = setTimeout(onComplete, 2400);
    return () => clearTimeout(timer);
  }, [onComplete]);

  return (
    <div className="dealing-overlay">
      {cards.map((c) => (
        <div
          key={c.id}
          className={`dealt-card to-${c.target}`}
          style={{ animationDelay: `${c.delay}s` }}
        >
          <CardBack small />
        </div>
      ))}
    </div>
  );
}
