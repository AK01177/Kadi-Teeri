import { useMemo, useEffect, useState } from "react";
import { useTexture } from "@react-three/drei";
import { useSpring, a } from "@react-spring/three";
import { useThree } from "@react-three/fiber";
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

const SUIT_MAP: Record<string, string> = {
  C: "clubs",
  D: "diamonds",
  H: "hearts",
  S: "spades",
};

/* ── Shared geometry: real card with thickness ── */
const CARD_W = 1;
const CARD_H = 1.4;
const CARD_D = 0.025;
const CARD_BOX = new THREE.BoxGeometry(CARD_W, CARD_H, CARD_D);

/* ── Shared edge material (cream-coloured card stock) ── */
const EDGE_MAT = new THREE.MeshStandardMaterial({
  color: "#f0e8d0",
  roughness: 0.6,
  metalness: 0,
});

export function Card3D({
  card,
  position,
  rotation,
  index,
  faceDown = false,
  scale: targetScale = 1,
}: Card3DProps) {
  const suitName = SUIT_MAP[card.suit] || "spades";
  const faceSrc = `/CardsPNG/${suitName}_${card.rank}.png`;
  const backSrc = `/CardsPNG/back_light.png`;

  const [faceTex, backTex] = useTexture([faceSrc, backSrc]);
  const invalidate = useThree((s) => s.invalidate);

  const [dealt, setDealt] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => {
      setDealt(true);
      invalidate();
    }, 60 + index * 50);
    return () => clearTimeout(t);
  }, [index, invalidate]);

  /* ── Ensure vivid colours via sRGB colour space ── */
  useMemo(() => {
    faceTex.colorSpace = THREE.SRGBColorSpace;
    backTex.colorSpace = THREE.SRGBColorSpace;
    faceTex.minFilter = THREE.LinearFilter;
    faceTex.magFilter = THREE.LinearFilter;
    backTex.minFilter = THREE.LinearFilter;
    backTex.magFilter = THREE.LinearFilter;
    faceTex.needsUpdate = true;
    backTex.needsUpdate = true;
  }, [faceTex, backTex]);

  /*
   * Materials order for BoxGeometry:
   *   [0]+x  [1]-x  [2]+y  [3]-y  [4]+z(front)  [5]-z(back)
   *
   * When laid flat with rotation [-PI/2, 0, 0]:
   *   +z → upward (visible to camera)
   *   -z → downward (hidden against table)
   *
   * faceDown=false → +z shows card face (faceTex)
   * faceDown=true  → +z shows card back (backTex)
   */
  const materials = useMemo(() => {
    const topMap = faceDown ? backTex : faceTex;
    const botMap = faceDown ? faceTex : backTex;

    const topMat = new THREE.MeshStandardMaterial({
      map: topMap,
      roughness: 0.3,
      metalness: 0,
    });
    const botMat = new THREE.MeshStandardMaterial({
      map: botMap,
      roughness: 0.4,
      metalness: 0,
    });

    return [EDGE_MAT, EDGE_MAT, EDGE_MAT, EDGE_MAT, topMat, botMat];
  }, [faceTex, backTex, faceDown]);

  /* ── Spring: deal-in animation ── */
  const spring = useSpring({
    pos: dealt
      ? position
      : ([position[0], position[1] - 2, position[2] + 1.5] as [number, number, number]),
    rot: dealt
      ? rotation
      : ([rotation[0] - 0.4, rotation[1], rotation[2]] as [number, number, number]),
    scl: dealt ? targetScale : 0.12,
    config: { mass: 0.65, tension: 190, friction: 22 },
    onChange: () => invalidate(),
  });

  return (
    <a.mesh
      castShadow
      receiveShadow
      geometry={CARD_BOX}
      material={materials}
      position={spring.pos as any}
      rotation={spring.rot as any}
      scale={spring.scl as any}
    />
  );
}
