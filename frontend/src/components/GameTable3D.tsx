import { Suspense, useMemo, useCallback } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { PerspectiveCamera, Html } from "@react-three/drei";
import type { GameState } from "../types/game";
import { SUIT_SYMBOLS } from "../types/game";
import { Card3D } from "./Card3D";

interface GameTable3DProps {
  game: GameState;
  mySeat: number;
  showTrick?: boolean;
}

/* ── Invalidation helper: any child can call this to trigger a frame ── */
function InvalidateOnMount() {
  const invalidate = useThree((s) => s.invalidate);
  invalidate();
  return null;
}

export function GameTable3D({ game, mySeat, showTrick }: GameTable3DProps) {
  const n = game.players.length;

  /* ── Compute opponent positions around the far side of the table ── */
  const otherPlayers = useMemo(() => {
    const arr: { seatIndex: number; player: typeof game.players[0]; px: number; pz: number }[] = [];
    for (let i = 1; i < n; i++) {
      const seatIndex = (mySeat + i) % n;
      const numOthers = n - 1;

      // Spread opponents in a 180° arc across the far side of the table
      let angle: number;
      if (numOthers === 1) {
        angle = Math.PI / 2; // directly across
      } else {
        angle = (Math.PI * 0.15) + (i - 1) * (Math.PI * 0.7) / (numOthers - 1);
      }

      const radius = 3.2;
      const px = Math.cos(angle) * radius;
      const pz = -Math.sin(angle) * radius;

      arr.push({ seatIndex, player: game.players[seatIndex], px, pz });
    }
    return arr;
  }, [game.players, mySeat, n]);

  const cardsPlayed = game.trick?.cards_played || [];

  /* ── Compute trick card positions — spread them clearly ── */
  const trickLayout = useMemo(() => {
    const count = cardsPlayed.length;
    if (count === 0) return [];

    // Lay cards in a neat row for 1-4 cards, or a slight arc for more
    const spacing = 1.3;
    const totalWidth = (count - 1) * spacing;
    const startX = -totalWidth / 2;

    return cardsPlayed.map((play, i) => {
      const x = startX + i * spacing;
      const z = 0; // center of table
      const y = 0.01 + i * 0.005; // tiny stack offset to prevent z-fighting
      // Slight random rotation for realism
      const rotZ = (play.seat * 0.3) - 0.45;
      return {
        play,
        position: [x, y, z] as [number, number, number],
        rotation: [-Math.PI / 2, 0, rotZ] as [number, number, number],
      };
    });
  }, [cardsPlayed]);

  const seatLabel = useCallback((s: number) => {
    return game.players[s]?.name || `Seat ${s}`;
  }, [game.players]);

  return (
    <div style={{
      width: "100%",
      height: "45vh",
      minHeight: "260px",
      maxHeight: "400px",
      borderRadius: "16px",
      overflow: "hidden",
      border: "1px solid var(--border)",
      position: "relative",
      background: "linear-gradient(180deg, #0a1510 0%, #0e1912 100%)",
    }}>
      <Canvas
        frameloop="demand"
        dpr={[1, 1.5]}
        gl={{ antialias: true, powerPreference: "low-power" }}
      >
        {/* First-person seated view: looking down at the table */}
        <PerspectiveCamera makeDefault position={[0, 5.5, 3.5]} fov={50} />

        {/* Simple flat lighting — no expensive PBR shadows */}
        <ambientLight intensity={0.9} />
        <directionalLight position={[0, 8, 2]} intensity={0.6} />

        <InvalidateOnMount />

        {/* ── The Table ── */}
        {/* Felt surface */}
        <mesh receiveShadow position={[0, -0.15, -0.5]} rotation={[0, 0, 0]}>
          <cylinderGeometry args={[4.5, 4.5, 0.15, 32]} />
          <meshBasicMaterial color="#1a5c3a" />
        </mesh>
        {/* Wooden rim */}
        <mesh position={[0, -0.15, -0.5]}>
          <cylinderGeometry args={[4.7, 4.7, 0.2, 32]} />
          <meshBasicMaterial color="#4a2812" />
        </mesh>
        {/* Inner felt detail ring */}
        <mesh position={[0, -0.06, -0.5]}>
          <ringGeometry args={[3.8, 4.5, 32]} />
          <meshBasicMaterial color="#155230" side={2} />
        </mesh>

        <Suspense fallback={null}>
          {/* ── Trick Cards — large, clearly visible ── */}
          {showTrick && trickLayout.map(({ play, position, rotation }, i) => (
            <group key={`trick-${play.card.suit}-${play.card.rank}-${play.seat}`}>
              <Card3D
                card={play.card}
                position={position}
                rotation={rotation}
                index={i}
              />
              {/* Label showing WHO played this card */}
              <Html
                position={[position[0], 0.05, position[2] + 0.9]}
                center
                sprite
                style={{ pointerEvents: "none" }}
              >
                <div style={{
                  background: "rgba(0,0,0,0.8)",
                  color: "#fff",
                  padding: "2px 8px",
                  borderRadius: "6px",
                  fontSize: "11px",
                  fontWeight: 600,
                  fontFamily: "var(--font-mono, monospace)",
                  whiteSpace: "nowrap",
                  border: game.turn_seat === play.seat ? "1px solid var(--amber, #f0a500)" : "1px solid rgba(255,255,255,0.15)",
                }}>
                  {seatLabel(play.seat)} — {play.card.rank}{SUIT_SYMBOLS[play.card.suit]}
                </div>
              </Html>
            </group>
          ))}
        </Suspense>

        {/* ── Opponent Seats ── */}
        {otherPlayers.map((p) => (
          <group key={p.seatIndex}>
            {/* Small indicator for opponent's cards (face-down stack) */}
            {game.status === "playing" && (game.hand_sizes?.[p.seatIndex] ?? 0) > 0 && (
              <mesh position={[p.px, 0.01, p.pz - 0.2]} rotation={[-Math.PI / 2, 0, 0]}>
                <planeGeometry args={[0.5, 0.7]} />
                <meshBasicMaterial color="#2a3a30" />
              </mesh>
            )}

            {/* Opponent info overlay */}
            <Html
              position={[p.px, 0.5, p.pz - 0.8]}
              center
              sprite
              style={{ pointerEvents: "none" }}
            >
              <div style={{
                background: "rgba(8, 12, 10, 0.95)",
                backdropFilter: "blur(10px)",
                borderRadius: "10px",
                padding: "8px 14px",
                border: game.turn_seat === p.seatIndex
                  ? "2px solid var(--amber, #f0a500)"
                  : "1px solid rgba(255,255,255,0.1)",
                textAlign: "center",
                minWidth: "80px",
                boxShadow: game.turn_seat === p.seatIndex
                  ? "0 0 12px rgba(240,165,0,0.3)"
                  : "0 2px 8px rgba(0,0,0,0.4)",
              }}>
                {/* Name */}
                <div style={{
                  color: "#fff",
                  fontSize: "13px",
                  fontWeight: 700,
                  marginBottom: "4px",
                  letterSpacing: "0.02em",
                }}>
                  {p.player?.name || "Empty"}
                </div>

                {/* Tags */}
                <div style={{ display: "flex", gap: "4px", justifyContent: "center", flexWrap: "wrap", marginBottom: "4px" }}>
                  {game.dealer === p.seatIndex && (
                    <span style={{
                      background: "rgba(240,165,0,0.2)",
                      color: "#f0a500",
                      padding: "1px 6px",
                      borderRadius: "4px",
                      fontSize: "9px",
                      fontWeight: 700,
                      textTransform: "uppercase",
                      letterSpacing: "0.05em",
                    }}>Dealer</span>
                  )}
                  {game.bidder_seat === p.seatIndex && (
                    <span style={{
                      background: "rgba(56,189,248,0.2)",
                      color: "#38bdf8",
                      padding: "1px 6px",
                      borderRadius: "4px",
                      fontSize: "9px",
                      fontWeight: 700,
                      textTransform: "uppercase",
                    }}>Bidder</span>
                  )}
                  {game.bherus.filter((b) => b.revealed && b.holder_seat === p.seatIndex).map((_, bi) => (
                    <span key={bi} style={{
                      background: "rgba(168,85,247,0.2)",
                      color: "#a855f7",
                      padding: "1px 6px",
                      borderRadius: "4px",
                      fontSize: "9px",
                      fontWeight: 700,
                      textTransform: "uppercase",
                    }}>Bheru</span>
                  ))}
                </div>

                {/* Stats */}
                {game.status === "playing" && (
                  <div style={{
                    display: "flex",
                    gap: "10px",
                    justifyContent: "center",
                    fontSize: "11px",
                    fontFamily: "var(--font-mono, monospace)",
                    fontWeight: 600,
                  }}>
                    <span style={{ color: "rgba(255,255,255,0.6)" }}>
                      {game.hand_sizes?.[p.seatIndex] ?? 0}🃏
                    </span>
                    <span style={{ color: "#f0a500" }}>
                      {game.captured_points?.[p.seatIndex] ?? 0} pts
                    </span>
                  </div>
                )}
              </div>
            </Html>
          </group>
        ))}

        {/* ── "Your view" indicator at the near edge ── */}
        <Html position={[0, 0.1, 3.8]} center sprite style={{ pointerEvents: "none" }}>
          <div style={{
            background: "rgba(8,12,10,0.9)",
            color: "rgba(255,255,255,0.5)",
            padding: "4px 16px",
            borderRadius: "8px",
            fontSize: "11px",
            fontWeight: 600,
            fontFamily: "var(--font-mono, monospace)",
            border: "1px solid rgba(255,255,255,0.08)",
          }}>
            Your seat
          </div>
        </Html>
      </Canvas>
    </div>
  );
}
