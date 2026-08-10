import { useTexture } from "@react-three/drei";
import { useSpring, a } from "@react-spring/three";
import type { Card as CardType } from "../types/game";
import { useEffect, useState } from "react";
import * as THREE from "three";

interface Card3DProps {
  card: CardType;
  position: [number, number, number];
  rotation: [number, number, number];
  index: number;
  isLegal?: boolean;
  isMyTurn?: boolean;
  inHand?: boolean;
  onClick?: () => void;
}

export function Card3D({ card, position, rotation, index, isLegal = true, isMyTurn = false, inHand = false, onClick }: Card3DProps) {
  const suitNameMap: Record<string, string> = {
    C: "clubs",
    D: "diamonds",
    H: "hearts",
    S: "spades",
  };
  const suitName = suitNameMap[card.suit];
  const imgSrc = `/CardsPNG/${suitName}_${card.rank}.png`;
  const backSrc = `/CardsPNG/back_light.png`;

  const [frontTex, backTex] = useTexture([imgSrc, backSrc]);
  
  const [hovered, setHovered] = useState(false);
  const [played, setPlayed] = useState(false);

  useEffect(() => {
    // Staggered entry animation
    const t = setTimeout(() => setPlayed(true), 50 + index * 50);
    return () => clearTimeout(t);
  }, [index]);

  // Adjust position and rotation on hover for hand cards
  const targetPosition = [...position];
  const targetRotation = [...rotation];
  let targetScale = 1;

  if (inHand && hovered && isLegal) {
    // Lift the card up and forward towards the camera
    targetPosition[1] += 0.5; // Y up
    targetPosition[2] += 0.2; // Z forward
    targetRotation[0] = 0; // Stand it up slightly more
    targetScale = 1.1;
  }
  
  if (!isLegal) {
    targetPosition[1] -= 0.2; // Dim/lower illegal cards
  }

  const spring = useSpring({
    position: played ? targetPosition : [0, -4, 4], // Fly from bottom
    rotation: played ? targetRotation : [-Math.PI / 4, 0, 0],
    scale: played ? targetScale : 1.5,
    config: { mass: 1, tension: 200, friction: 20 },
  });

  const edgeMaterial = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.8 });
  const frontMaterial = new THREE.MeshStandardMaterial({ map: frontTex, transparent: true, alphaTest: 0.5, roughness: 0.4 });
  const backMaterial = new THREE.MeshStandardMaterial({ map: backTex, transparent: true, alphaTest: 0.5, roughness: 0.4 });

  // In Three.js, BoxGeometry faces are:
  // 0: right, 1: left, 2: top, 3: bottom, 4: front(+z), 5: back(-z)
  const materials = [
    edgeMaterial, // right
    edgeMaterial, // left
    edgeMaterial, // top
    edgeMaterial, // bottom
    frontMaterial, // front
    backMaterial, // back
  ];

  return (
    <a.mesh
      position={spring.position as any}
      rotation={spring.rotation as any}
      scale={spring.scale as any}
      castShadow
      receiveShadow
      onPointerOver={(e) => {
        if (inHand && isLegal && isMyTurn) {
          e.stopPropagation();
          document.body.style.cursor = 'pointer';
          setHovered(true);
        }
      }}
      onPointerOut={() => {
        if (inHand) {
          document.body.style.cursor = 'auto';
          setHovered(false);
        }
      }}
      onClick={(e) => {
        if (inHand && isLegal && isMyTurn && onClick) {
          e.stopPropagation();
          document.body.style.cursor = 'auto';
          setHovered(false);
          onClick();
        }
      }}
    >
      <boxGeometry args={[1, 1.42, 0.01]} />
      {materials.map((mat, i) => (
        <primitive key={i} object={mat} attach={`material-${i}`} />
      ))}
    </a.mesh>
  );
}
