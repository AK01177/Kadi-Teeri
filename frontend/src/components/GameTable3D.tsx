import { Suspense, useMemo } from "react";
import { Canvas } from "@react-three/fiber";
import { PerspectiveCamera, Html, Environment, ContactShadows } from "@react-three/drei";
import type { GameState, Card as CardType } from "../types/game";
import { Card3D } from "./Card3D";

interface GameTable3DProps {
  game: GameState;
  mySeat: number;
  showTrick?: boolean;
  hand?: CardType[];
  legalCards?: CardType[];
  isMyTurn?: boolean;
  onPlayCard?: (card: CardType) => void;
}

export function GameTable3D({ game, mySeat, showTrick, hand = [], legalCards = [], isMyTurn = false, onPlayCard }: GameTable3DProps) {
  const n = game.players.length;

  const otherPlayers = useMemo(() => {
    const arr = [];
    for (let i = 0; i < n; i++) {
      const seatIndex = (mySeat + i) % n;
      if (seatIndex === mySeat) continue; // Skip local player
      
      const otherIndex = i - 1; // 0 to n-2
      const numOthers = n - 1;
      
      let angle = -Math.PI / 2; // Default for 1 other
      if (numOthers > 1) {
        angle = Math.PI - (otherIndex * Math.PI / (numOthers - 1));
      }
      
      const radius = 3.8;
      const x = radius * Math.cos(angle);
      const z = radius * Math.sin(angle);
      const adjustedZ = -Math.abs(z);
      
      arr.push({ seatIndex, player: game.players[seatIndex], position: [x, 0.4, adjustedZ - 1.5], angle });
    }
    return arr;
  }, [game.players, mySeat, n]);

  const cardsPlayed = game.trick?.cards_played || [];
  
  // Create a legal set for fast lookup
  const legalSet = useMemo(() => {
    return new Set(legalCards.map(c => `${c.rank}:${c.suit}:${c.deck_index}`));
  }, [legalCards]);

  return (
    <div style={{ width: "100%", height: "600px", margin: "10px 0", borderRadius: "16px", overflow: "hidden", border: "1px solid var(--border)", position: "relative" }}>
      <Canvas shadows>
        {/* Adjusted camera to see the hand properly at the bottom */}
        <PerspectiveCamera makeDefault position={[0, 5.5, 6.5]} fov={50} rotation={[-0.8, 0, 0]} />
        <ambientLight intensity={0.6} />
        <directionalLight position={[5, 10, 5]} intensity={1.5} castShadow />
        
        <Environment preset="city" />

        {/* The Table */}
        <mesh receiveShadow position={[0, -0.1, -1]}>
          <cylinderGeometry args={[5, 5, 0.2, 64]} />
          <meshStandardMaterial color="#1b4b39" roughness={0.8} />
        </mesh>
        
        {/* Table Edge */}
        <mesh receiveShadow position={[0, -0.1, -1]}>
          <cylinderGeometry args={[5.2, 5.2, 0.25, 64]} />
          <meshStandardMaterial color="#3e1f10" roughness={0.5} />
        </mesh>

        <ContactShadows position={[0, 0, -1]} opacity={0.4} scale={10} blur={2} far={4} />

        <Suspense fallback={null}>
          {/* Render Trick Cards */}
          {showTrick && cardsPlayed.map((play, i) => {
            const angle = (i * Math.PI * 2) / cardsPlayed.length;
            const radius = 0.5;
            const x = radius * Math.cos(angle);
            const z = radius * Math.sin(angle) - 1;
            const rotZ = -angle + Math.PI / 2;
            return (
              <Card3D 
                key={`trick-${play.card.suit}-${play.card.rank}-${play.seat}`}
                card={play.card}
                position={[x, 0.02 + i * 0.01, z]} 
                rotation={[-Math.PI / 2, 0, rotZ]}
                index={i}
              />
            );
          })}

          {/* Render 3D Hand */}
          {hand.map((card, i) => {
            const total = hand.length;
            // Arc logic for the fan
            // The more cards, the wider the fan.
            const maxArc = Math.PI / 2.5; 
            const arc = total > 1 ? Math.min(maxArc, (total - 1) * 0.15) : 0; 
            const startAngle = arc / 2;
            const step = total > 1 ? arc / (total - 1) : 0;
            const currentAngle = startAngle - i * step;

            // Position along the arc. Center is at bottom screen [0, y, 4.5]
            const radius = 4;
            const x = Math.sin(currentAngle) * radius;
            // To make a curve, Z is slightly pushed forward for cards in the middle, and Y is dropped on the edges.
            const zOffset = (1 - Math.cos(currentAngle)) * radius; 
            
            // Adjust Z to place the hand near the camera
            const z = 4.5 + zOffset; 
            // Drop Y slightly on the edges of the fan
            const y = 1 - Math.abs(currentAngle) * 1.2;
            
            // Cards overlap. To avoid Z-fighting and ensure the rightmost card is on top (or leftmost depending on standard), 
            // we give a tiny Z or Y step per index. Let's just use tiny Y stacking.
            const stackingY = i * 0.005;

            const rotZ = -currentAngle; 
            // Angle the cards slightly back so they face the camera
            const rotX = -0.3;

            const isLegal = legalSet.has(`${card.rank}:${card.suit}:${card.deck_index}`);

            return (
              <Card3D 
                key={`hand-${card.suit}-${card.rank}-${card.deck_index}`}
                card={card}
                position={[x, y + stackingY, z]} 
                rotation={[rotX, 0, rotZ]}
                index={i}
                inHand={true}
                isLegal={isLegal}
                isMyTurn={isMyTurn}
                onClick={() => onPlayCard && onPlayCard(card)}
              />
            );
          })}
        </Suspense>

        {/* Opponent Avatars/Names */}
        {otherPlayers.map((p) => (
          <Html 
            key={p.seatIndex} 
            position={p.position as [number, number, number]} 
            center 
            transform
            sprite
          >
            <div className="seat-box" style={{ background: "rgba(14, 21, 18, 0.8)", backdropFilter: "blur(8px)", pointerEvents: "none" }}>
              <div className="nm">{p.player ? p.player.name : "Empty"}</div>
              <div className="tags">
                {game.dealer === p.seatIndex && <span className="mini-tag dealer">Dealer</span>}
                {game.bidder_seat === p.seatIndex && <span className="mini-tag bidder">Bidder</span>}
                {game.bherus.filter((b) => b.revealed && b.holder_seat === p.seatIndex).map((_, i) => (
                  <span key={i} className="mini-tag partner">Bheru</span>
                ))}
              </div>
              {game.status === "playing" && (
                <div style={{ fontSize: "10px", color: "var(--muted)", fontFamily: "var(--font-mono)", display: "flex", gap: "8px", justifyContent: "center", marginTop: "4px" }}>
                  <span>{game.hand_sizes?.[p.seatIndex] ?? 0} cards</span>
                  <span>{game.captured_points?.[p.seatIndex] ?? 0} pts</span>
                </div>
              )}
            </div>
          </Html>
        ))}
      </Canvas>
    </div>
  );
}
