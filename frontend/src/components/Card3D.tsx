import { useTexture } from "@react-three/drei";
import { useSpring, a } from "@react-spring/three";
import { useThree } from "@react-three/fiber";
import type { Card as CardType } from "../types/game";
import { useEffect, useState, useMemo } from "react";
import * as THREE from "three";

interface Card3DProps {
  card: CardType;
  position: [number, number, number];
  rotation: [number, number, number];
  index: number;
  /** If true, show the card back instead of the face */
  faceDown?: boolean;
}

const SUIT_MAP: Record<string, string> = {
  C: "clubs",
  D: "diamonds",
  H: "hearts",
  S: "spades",
};

// Shared geometry — all cards reuse the exact same PlaneGeometry instance
const CARD_GEO = new THREE.PlaneGeometry(1, 1.4);

export function Card3D({ card, position, rotation, index, faceDown = false }: Card3DProps) {
  const suitName = SUIT_MAP[card.suit];
  const faceSrc = `/CardsPNG/${suitName}_${card.rank}.png`;
  const backSrc = `/CardsPNG/back_light.png`;

  const [faceTex, backTex] = useTexture([faceSrc, backSrc]);
  const invalidate = useThree((s) => s.invalidate);

  const [dealt, setDealt] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => {
      setDealt(true);
      invalidate(); // trigger a re-render in demand mode
    }, 80 + index * 60);
    return () => clearTimeout(t);
  }, [index, invalidate]);

  // MeshBasicMaterial: no lighting calculations, 3x faster on mobile
  const material = useMemo(() => {
    const tex = faceDown ? backTex : faceTex;
    return new THREE.MeshBasicMaterial({
      map: tex,
      side: THREE.FrontSide,
    });
  }, [faceTex, backTex, faceDown]);

  const spring = useSpring({
    position: dealt ? position : [0, -3, position[2]],
    rotation: dealt ? rotation : [-Math.PI / 6, 0, 0],
    scale: dealt ? 1 : 0.3,
    config: { mass: 0.8, tension: 180, friction: 22 },
    onChange: () => invalidate(), // re-render on each animation frame
  });

  return (
    <a.mesh
      geometry={CARD_GEO}
      material={material}
      position={spring.position as any}
      rotation={spring.rotation as any}
      scale={spring.scale as any}
    />
  );
}
