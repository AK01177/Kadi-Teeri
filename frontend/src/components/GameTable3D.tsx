import { Suspense, useMemo, useCallback, useState, useEffect } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { PerspectiveCamera, Html, useGLTF } from "@react-three/drei";
import * as THREE from "three";
import type { GameState, Card as CardType } from "../types/game";
import { SUIT_SYMBOLS, SUIT_NAMES } from "../types/game";
import { Card3D } from "./Card3D";
import { Card } from "./Card";

/* ──────────────────────────────────────────────────────────────
   GameTable3D — Fullscreen first-person 3D card table
   ────────────────────────────────────────────────────────────── */

interface GameTable3DProps {
  game: GameState;
  mySeat: number;
  showTrick?: boolean;
  hand: CardType[];
  legalCards: CardType[];
  isMyTurn: boolean;
  onPlayCard: (card: CardType) => void;
  trickWinner: { name: string; points: number } | null;
  onClose: () => void;
}

/* ── Helper: trigger a frame in demand mode ── */
function InvalidateOnMount() {
  const invalidate = useThree((s) => s.invalidate);
  invalidate();
  return null;
}



export function GameTable3D({
  game,
  mySeat,
  showTrick,
  hand,
  legalCards,
  isMyTurn,
  onPlayCard,
  trickWinner,
  onClose,
}: GameTable3DProps) {
  const n = game.players.length;
  const isCompact = n >= 6;

  const [isFullscreen, setIsFullscreen] = useState(false);

  const toggleFullscreen = useCallback(() => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch((err) => {
        console.warn(`Error attempting to enable fullscreen: ${err.message}`);
      });
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen();
      }
    }
  }, []);

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };
    document.addEventListener("fullscreenchange", handleFullscreenChange);
    return () => {
      document.removeEventListener("fullscreenchange", handleFullscreenChange);
    };
  }, []);

  const { nodes: tableNodes, materials: tableMaterials } = useGLTF("/models/table.glb") as any;

  const tableGeometry = useMemo(() => {
    if (!tableNodes.Chair_Table_Mat_0) return null;
    const orig = (tableNodes.Chair_Table_Mat_0 as THREE.Mesh).geometry;
    const cloned = orig.clone();
    cloned.center(); // Center at origin. Original height is 359 units.
    // We want the diameter to be ~9 units (matches old 4.5 radius).
    // The original X/Y size is ~284.5. Scale = 9 / 284.5 ≈ 0.0316
    cloned.scale(0.0316, 0.0316, 0.0316);
    // Rotate so it's Y-up
    cloned.rotateX(-Math.PI / 2);
    // Add a slight decorative rotation for the table legs
    cloned.rotateY(Math.PI / 8);
    return cloned;
  }, [tableNodes]);

  /* ═══════════════════════════════════════════
     Opponent positions — 180° arc on far side
     Dynamic radius and wider arc for many players
     ═══════════════════════════════════════════ */
  const otherPlayers = useMemo(() => {
    const arr: {
      seatIndex: number;
      player: (typeof game.players)[0];
      px: number;
      pz: number;
    }[] = [];
    const numOthers = n - 1;

    // Dynamic radius: grows with player count to prevent overlap
    const radius = n <= 4 ? 3.2 : 3.2 + (n - 4) * 0.35;
    // Wider arc for more players
    const startA = n <= 4 ? 0.82 * Math.PI : 0.92 * Math.PI;
    const endA = n <= 4 ? 0.18 * Math.PI : 0.08 * Math.PI;

    for (let i = 1; i < n; i++) {
      const seatIndex = (mySeat + i) % n;
      let angle: number;
      if (numOthers === 1) {
        angle = Math.PI / 2; // directly across
      } else {
        angle = startA + ((i - 1) / (numOthers - 1)) * (endA - startA);
      }
      const px = Math.cos(angle) * radius;
      // Stagger Z slightly per opponent so overlays don't align
      const zStagger = numOthers > 4 ? (i % 2 === 0 ? 0.25 : -0.25) : 0;
      const pz = -Math.sin(angle) * radius - 0.5 + zStagger;
      arr.push({ seatIndex, player: game.players[seatIndex], px, pz });
    }
    return arr;
  }, [game.players, mySeat, n]);

  /* ═══════════════════════════════════════════
     Trick card layout — spread in the centre
     ═══════════════════════════════════════════ */
  const cardsPlayed = game.trick?.cards_played || [];

  const trickLayout = useMemo(() => {
    const count = cardsPlayed.length;
    if (count === 0) return [];

    // Tighter spacing for many cards
    const spacing = count > 5 ? 0.95 : 1.35;
    const totalWidth = (count - 1) * spacing;
    const startX = -totalWidth / 2;

    return cardsPlayed.map((play, i) => ({
      play,
      position: [
        startX + i * spacing,
        0.02 + i * 0.02,
        -0.5 + (i - (count - 1) / 2) * 0.12,
      ] as [number, number, number],
      rotation: [
        -Math.PI / 2 + 0.05, // Flatter, less extreme upward tilt
        0,
        (i - (count - 1) / 2) * 0.06, // slight fan
      ] as [number, number, number],
    }));
  }, [cardsPlayed]);

  /* ═══════════════════════════════════════════
     Legal card set for hand rendering
     ═══════════════════════════════════════════ */
  const legalSet = useMemo(
    () =>
      new Set(
        (legalCards || []).map(
          (c) => `${c.rank}:${c.suit}:${c.deck_index}`
        )
      ),
    [legalCards]
  );

  /* ═══════════════════════════════════════════
     Helpers
     ═══════════════════════════════════════════ */
  const seatLabel = useCallback(
    (s: number) => game.players[s]?.name || `Seat ${s}`,
    [game.players]
  );

  /* ── Bheru info ── */
  const mySecretBherus = useMemo(
    () =>
      game.bherus.filter((b) => {
        if (b.revealed) return false;
        return hand.some(
          (c) => c.rank === b.call.rank && c.suit === b.call.suit
        );
      }),
    [game.bherus, hand]
  );
  const amIBheru = !game.is_solo && mySecretBherus.length > 0;

  const revealedBherus = useMemo(
    () =>
      game.bherus.filter(
        (b) => b.revealed && b.holder_seat !== undefined
      ),
    [game.bherus]
  );

  /* ── My stats ── */
  const myCardCount = game.hand_sizes?.[mySeat] ?? hand.length;
  const myPoints = game.captured_points?.[mySeat] ?? 0;

  /* ═══════════════════════════════════════════════════════════════
     RENDER
     ═══════════════════════════════════════════════════════════════ */
  return (
    <div className="game3d-fullscreen">
      {/* ════════════════════════ 3D CANVAS ════════════════════════ */}
      <Canvas
        shadows
        flat
        frameloop="demand"
        dpr={[1, 1.5]}
        gl={{ antialias: true, powerPreference: "default" }}
        style={{ position: "absolute", inset: 0 }}
      >
        {/*
          Camera: first-person seated view
          Position [0, 5, 4.5] — elevated above our seat
          Rotation [-PI/4, 0, 0] — looking 45° down at the table centre
          FOV 55 — wide enough to see the full table in landscape
        */}
        <PerspectiveCamera
          makeDefault
          position={[0, 5, 4.5]}
          rotation={[-Math.PI / 4, 0, 0]}
          fov={55}
        />
        <InvalidateOnMount />

        {/* ── Lighting: bright for vivid cards, with shadows ── */}
        <ambientLight intensity={1.1} />
        <directionalLight 
          position={[3, 8, 5]} 
          intensity={0.9} 
          castShadow 
          shadow-mapSize={[1024, 1024]}
          shadow-camera-left={-8}
          shadow-camera-right={8}
          shadow-camera-top={8}
          shadow-camera-bottom={-8}
        />
        <directionalLight position={[-3, 6, -3]} intensity={0.4} />

        {/* ═════════════ TABLE ═════════════ */}
        {tableGeometry && (
          <mesh
            receiveShadow
            castShadow
            geometry={tableGeometry}
            material={tableMaterials.Table_Mat}
            // Since the table is centered and its scaled height is ~11.35,
            // placing it at Y = -5.675 positions the table top exactly at Y = 0.
            position={[0, -5.675, -0.5]}
          />
        )}

        {/* ═════════════ TRICK CARDS ═════════════ */}
        <Suspense fallback={null}>
          {showTrick &&
            trickLayout.map(({ play, position, rotation }, i) => (
              <group
                key={`trick-${play.card.suit}-${play.card.rank}-${play.seat}-${i}`}
              >
                <Card3D
                  card={play.card}
                  position={position}
                  rotation={rotation}
                  index={i}
                  scale={isCompact ? 0.9 : 1.15}
                />
                {/* Player name label below the card */}
                <Html
                  position={[
                    position[0],
                    0.06,
                    position[2] + 0.95,
                  ]}
                  center
                  sprite
                  style={{ pointerEvents: "none" }}
                >
                  <div className="game3d-card-label">
                    {seatLabel(play.seat)} —{" "}
                    {play.card.rank}
                    {SUIT_SYMBOLS[play.card.suit]}
                  </div>
                </Html>
              </group>
            ))}
        </Suspense>

        {/* ═════════════ OPPONENT SEATS ═════════════ */}
        {otherPlayers.map((p) => (
          <group key={p.seatIndex}>
            {/* Face-down card indicator */}
            {game.status === "playing" &&
              (game.hand_sizes?.[p.seatIndex] ?? 0) > 0 && (
                <Suspense fallback={null}>
                  <Card3D
                    card={{ rank: "A", suit: "S", deck_index: -1 }}
                    position={[p.px, 0.01, p.pz + 0.3]}
                    rotation={[
                      -Math.PI / 2,
                      0,
                      p.seatIndex * 0.4 - 0.6,
                    ]}
                    index={0}
                    faceDown
                    scale={isCompact ? 0.4 : 0.55}
                  />
                </Suspense>
              )}

            {/* Active turn glow ring */}
            {game.turn_seat === p.seatIndex && (
              <mesh
                position={[p.px, 0.008, p.pz + 0.3]}
                rotation={[-Math.PI / 2, 0, 0]}
              >
                <ringGeometry args={[0.55, 0.7, 32]} />
                <meshBasicMaterial
                  color="#f0a500"
                  transparent
                  opacity={0.5}
                  side={THREE.DoubleSide}
                />
              </mesh>
            )}

            {/* Opponent info overlay */}
            <Html
              position={[p.px, 0.6, p.pz - (isCompact ? 0.3 : 0.5)]}
              center
              sprite
              style={{ pointerEvents: "none" }}
            >
              <div
                className={`game3d-opponent${
                  isCompact ? " compact" : ""
                }${
                  game.turn_seat === p.seatIndex ? " active" : ""
                }`}
              >
                <div className="game3d-opponent-name">
                  {p.player?.name || "Empty"}
                </div>

                <div className="game3d-opponent-tags">
                  {game.dealer === p.seatIndex && (
                    <span className="game3d-tag dealer">
                      {isCompact ? "D" : "Dealer"}
                    </span>
                  )}
                  {game.bidder_seat === p.seatIndex && (
                    <span className="game3d-tag bidder">
                      {isCompact ? "B" : "Bidder"}
                    </span>
                  )}
                  {game.bherus
                    .filter(
                      (b) =>
                        b.revealed &&
                        b.holder_seat === p.seatIndex
                    )
                    .map((_, bi) => (
                      <span key={bi} className="game3d-tag bheru">
                        {isCompact ? "P" : "Bheru"}
                      </span>
                    ))}
                  {!p.player?.is_connected && (
                    <span className="game3d-tag offline">
                      {isCompact ? "⚠" : "Offline"}
                    </span>
                  )}
                </div>

                {game.status === "playing" && (
                  <div className="game3d-opponent-stats">
                    <span>
                      {game.hand_sizes?.[p.seatIndex] ?? 0} 🃏
                    </span>
                    <span className="game3d-pts">
                      {game.captured_points?.[p.seatIndex] ?? 0}{" "}
                      {isCompact ? "p" : "pts"}
                    </span>
                  </div>
                )}
              </div>
            </Html>
          </group>
        ))}

        {/* ═════════════ YOUR SEAT LABEL ═════════════ */}
        <Html
          position={[0, 0.1, 3.2]}
          center
          sprite
          style={{ pointerEvents: "none" }}
        >
          <div className="game3d-you-label">
            {game.players[mySeat]?.name || "You"} · {myCardCount}{" "}
            🃏 · {myPoints} pts
          </div>
        </Html>
      </Canvas>

      {/* ════════════════════════ HUD OVERLAY ════════════════════════ */}
      <div className="game3d-hud">
        <div className="game3d-hud-left">
          {game.trump_suit && (
            <span className="game3d-badge trump">
              Trump {SUIT_SYMBOLS[game.trump_suit]}
            </span>
          )}
          <span className="game3d-badge target">
            Target {game.bid_target}
          </span>
          <span className="game3d-badge">
            Trick {game.trick_number}/
            {game.hand_sizes
              ? Math.max(...Object.values(game.hand_sizes)) +
                game.trick_number -
                1
              : "?"}
          </span>
          {!game.is_solo && game.bherus.length > 0 && (
            <span className="game3d-badge calls">
              Calls:{" "}
              {game.bherus
                .map(
                  (b) =>
                    `${b.call.rank}${SUIT_SYMBOLS[b.call.suit]}`
                )
                .join(", ")}
            </span>
          )}
        </div>
        <div style={{ display: 'flex', gap: '8px', pointerEvents: 'auto' }}>
          <button
            className="game3d-close-btn"
            onClick={toggleFullscreen}
            title="Toggle Fullscreen"
          >
            {isFullscreen ? "↙" : "⤢"}
          </button>
          <button
            className="game3d-close-btn"
            onClick={onClose}
            title="Exit 3D View"
          >
            ✕
          </button>
        </div>
      </div>

      {/* ════════════════════════ INFO BANNERS ════════════════════════ */}
      <div className="game3d-banners">
        {game.is_solo && game.bidder_seat === mySeat && (
          <div className="game3d-info-banner">
            Playing solo against the table
          </div>
        )}
        {amIBheru && (
          <div className="game3d-info-banner">
            {mySecretBherus.some((b) => b.call.mode !== "second")
              ? "You are the secret partner!"
              : "You can be the secret partner if you play it second!"}
          </div>
        )}
        {revealedBherus.length > 0 && !game.is_solo && (
          <div className="game3d-info-banner">
            Partner revealed:{" "}
            {revealedBherus
              .map((b) => seatLabel(b.holder_seat!))
              .join(", ")}
          </div>
        )}
      </div>

      {/* ════════════════════════ TURN INDICATOR ════════════════════════ */}
      <div className={`game3d-turn${isMyTurn ? " mine" : ""}`}>
        {isMyTurn ? (
          <>
            Your turn
            {game.trick?.lead_suit
              ? ` — follow ${SUIT_NAMES[game.trick.lead_suit]}`
              : ""}
          </>
        ) : (
          <>Waiting on {seatLabel(game.turn_seat!)}…</>
        )}
      </div>

      {/* ════════════════════════ HAND STRIP ════════════════════════ */}
      <div className="game3d-hand">
        <div className="game3d-hand-scroll">
          {hand.map((card, i) => {
            const key = `${card.rank}-${card.suit}-${card.deck_index}-${i}`;
            const isLegal =
              isMyTurn &&
              legalSet.has(
                `${card.rank}:${card.suit}:${card.deck_index}`
              );
            return (
              <Card
                key={key}
                card={card}
                disabled={!isLegal}
                onClick={
                  isLegal ? () => onPlayCard(card) : undefined
                }
              />
            );
          })}
        </div>
      </div>

      {/* ════════════════════════ TRICK WINNER ════════════════════════ */}
      {trickWinner && (
        <div className="game3d-trick-winner">
          <h2>{trickWinner.name} gets the trick!</h2>
          <p>+{trickWinner.points} points</p>
        </div>
      )}
    </div>
  );
}

