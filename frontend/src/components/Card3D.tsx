import { useMemo, useEffect, useState } from "react";
import { useSpring, a } from "@react-spring/three";
import { useThree } from "@react-three/fiber";
import { useGLTF } from "@react-three/drei";
import type { Card as CardType } from "../types/game";
import * as THREE from "three";

interface Card3DProps {
  card: CardType;
  position: [number, number, number];
  rotation: [number, number, number];
  index: number;
  /** If true, show the card back on the upward-facing side */
  faceDown?: boolean;
  /** Uniform scale multiplier (default 1) */
  scale?: number;
}

const SUIT_PREFIX_MAP: Record<string, string> = {
  S: "spades",
  H: "hearts",
  D: "diamonds",
  C: "clubs",
};

const RANK_NUM_MAP: Record<string, string> = {
  "A": "01",
  "2": "02",
  "3": "03",
  "4": "04",
  "5": "05",
  "6": "06",
  "7": "07",
  "8": "08",
  "9": "09",
  "10": "10",
  "J": "11",
  "Q": "12",
  "K": "13",
};

export function Card3D({
  card,
  position,
  rotation,
  index,
  faceDown = false,
  scale: targetScale = 1,
}: Card3DProps) {
  const { nodes, materials } = useGLTF("/models/cards.glb");
  const invalidate = useThree((s) => s.invalidate);

  const [dealt, setDealt] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => {
      setDealt(true);
      invalidate();
    }, 60 + index * 50);
    return () => clearTimeout(t);
  }, [index, invalidate]);

  const nodeName = `${SUIT_PREFIX_MAP[card.suit]}${RANK_NUM_MAP[card.rank]}_playingCards_Mat_0`;
  const safeNodeName = nodes[nodeName] ? nodeName : "spades01_playingCards_Mat_0";

  const geometry = useMemo(() => {
    const origGeom = (nodes[safeNodeName] as THREE.Mesh).geometry;
    const cloned = origGeom.clone();
    cloned.center();
    // Scale 0.125 converts the 8x12 unit model to exactly 1.0 x 1.5 units
    // which perfectly matches our old 1.0 x 1.4 size.
    cloned.scale(0.125, 0.125, 0.125);
    // Rotate to match our original orientation so it lays flat on the table when rotation is [-PI/2, 0, 0]
    cloned.rotateX(Math.PI / 2);
    return cloned;
  }, [nodes, safeNodeName]);

  /* ── Spring: deal-in animation ── */
  // If faceDown is true, we flip the card over by adding PI to the Y-axis rotation
  // This will show the back of the card.
  const finalRotation = [
    rotation[0],
    rotation[1] + (faceDown ? Math.PI : 0),
    rotation[2],
  ] as [number, number, number];

  const spring = useSpring({
    pos: dealt
      ? position
      : ([position[0], position[1] - 2, position[2] + 1.5] as [number, number, number]),
    rot: dealt
      ? finalRotation
      : ([finalRotation[0] - 0.4, finalRotation[1], finalRotation[2]] as [number, number, number]),
    scl: dealt ? targetScale : 0.12,
    config: { mass: 0.65, tension: 190, friction: 22 },
    onChange: () => invalidate(),
  });

  return (
    <a.mesh
      castShadow
      receiveShadow
      geometry={geometry}
      material={materials.playingCards_Mat}
      position={spring.pos as any}
      rotation={spring.rot as any}
      scale={spring.scl as any}
    />
  );
}

useGLTF.preload("/models/cards.glb");
