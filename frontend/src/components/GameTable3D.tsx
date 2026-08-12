import { Suspense, useMemo, useCallback } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { PerspectiveCamera, Html } from "@react-three/drei";
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

  /* ═══════════════════════════════════════════
     Opponent positions — 180° arc on far side
     ═══════════════════════════════════════════ */
  const otherPlayers = useMemo(() => {
    const arr: {
      seatIndex: number;
      player: (typeof game.players)[0];
      px: number;
      pz: number;
    }[] = [];
    const numOthers = n - 1;

    for (let i = 1; i < n; i++) {
      const seatIndex = (mySeat + i) % n;
      let angle: number;
      if (numOthers === 1) {
        angle = Math.PI / 2; // directly across
      } else {
        const startA = 0.82 * Math.PI;
        const endA = 0.18 * Math.PI;
        angle = startA + ((i - 1) / (numOthers - 1)) * (endA - startA);
      }
      const radius = 3.2;
      const px = Math.cos(angle) * radius;
      const pz = -Math.sin(angle) * radius - 0.5; // offset by table center
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

    const spacing = 1.35;
    const totalWidth = (count - 1) * spacing;
    const startX = -totalWidth / 2;

    return cardsPlayed.map((play, i) => ({
      play,
      position: [
        startX + i * spacing,
        0.02 + i * 0.004,
        -0.5 + (i - (count - 1) / 2) * 0.12,
      ] as [number, number, number],
      rotation: [
        -Math.PI / 2 + 0.15, // tilted slightly toward camera
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

        {/* ── Lighting: bright for vivid cards, no shadows ── */}
        <ambientLight intensity={1.4} />
        <directionalLight position={[3, 8, 5]} intensity={0.7} />
        <directionalLight position={[-3, 6, -3]} intensity={0.3} />

        {/* ═════════════ TABLE ═════════════ */}

        {/* Felt surface */}
        <mesh position={[0, -0.08, -0.5]}>
          <cylinderGeometry args={[4.5, 4.5, 0.16, 48]} />
          <meshLambertMaterial color="#1a6b42" />
        </mesh>

        {/* Wooden rim */}
        <mesh position={[0, -0.12, -0.5]}>
          <cylinderGeometry args={[4.8, 4.8, 0.24, 48]} />
          <meshLambertMaterial color="#5a2d0c" />
        </mesh>

        {/* Inner decorative ring */}
        <mesh
          position={[0, 0.005, -0.5]}
          rotation={[-Math.PI / 2, 0, 0]}
        >
          <ringGeometry args={[3.5, 3.9, 48]} />
          <meshBasicMaterial color="#14573a" side={THREE.DoubleSide} />
        </mesh>

        {/* Centre circle */}
        <mesh
          position={[0, 0.006, -0.5]}
          rotation={[-Math.PI / 2, 0, 0]}
        >
          <circleGeometry args={[0.6, 32]} />
          <meshBasicMaterial color="#166340" side={THREE.DoubleSide} />
        </mesh>

        {/* Outer glow ring on the felt edge */}
        <mesh
          position={[0, 0.004, -0.5]}
          rotation={[-Math.PI / 2, 0, 0]}
        >
          <ringGeometry args={[4.2, 4.45, 48]} />
          <meshBasicMaterial
            color="#0f4a2e"
            side={THREE.DoubleSide}
            transparent
            opacity={0.6}
          />
        </mesh>

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
                  scale={1.15}
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
                    scale={0.55}
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
              position={[p.px, 0.6, p.pz - 0.5]}
              center
              sprite
              style={{ pointerEvents: "none" }}
            >
              <div
                className={`game3d-opponent${
                  game.turn_seat === p.seatIndex ? " active" : ""
                }`}
              >
                <div className="game3d-opponent-name">
                  {p.player?.name || "Empty"}
                </div>

                <div className="game3d-opponent-tags">
                  {game.dealer === p.seatIndex && (
                    <span className="game3d-tag dealer">Dealer</span>
                  )}
                  {game.bidder_seat === p.seatIndex && (
                    <span className="game3d-tag bidder">Bidder</span>
                  )}
                  {game.bherus
                    .filter(
                      (b) =>
                        b.revealed &&
                        b.holder_seat === p.seatIndex
                    )
                    .map((_, bi) => (
                      <span key={bi} className="game3d-tag bheru">
                        Bheru
                      </span>
                    ))}
                  {!p.player?.is_connected && (
                    <span className="game3d-tag offline">
                      Offline
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
                      pts
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
        <button
          className="game3d-close-btn"
          onClick={onClose}
          title="Exit 3D View"
        >
          ✕
        </button>
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
