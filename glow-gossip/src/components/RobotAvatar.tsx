import { useRef, useEffect, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Float } from '@react-three/drei';
import * as THREE from 'three';

type EmotionState = 'neutral' | 'happy' | 'sad' | 'angry' | 'surprised' | 'fearful' | 'disgusted';
type BehaviorState = 'idle' | 'typing' | 'analyzing' | 'explaining' | 'celebrating' | 'thinking';

interface RobotAvatarProps {
  emotion?: EmotionState;
  behavior?: BehaviorState;
  isActive?: boolean;
}

function RobotMesh({ emotion = 'neutral', behavior = 'idle', isActive = false }: RobotAvatarProps) {
  const robotRef = useRef<THREE.Group>(null);
  const headRef = useRef<THREE.Mesh>(null);
  const leftEyeRef = useRef<THREE.Mesh>(null);
  const rightEyeRef = useRef<THREE.Mesh>(null);
  const bodyRef = useRef<THREE.Mesh>(null);
  const leftArmRef = useRef<THREE.Group>(null);
  const rightArmRef = useRef<THREE.Group>(null);

  const [glowColor, setGlowColor] = useState('#00ffff');
  const [eyeScale, setEyeScale] = useState(1);

  // Map emotions to glow colors
  useEffect(() => {
    const colorMap: Record<EmotionState, string> = {
      neutral: '#00ffff',    // Blue - Calm
      happy: '#00ff00',      // Green - Happy/Confident
      sad: '#4444ff',        // Darker Blue - Sad
      angry: '#ff0000',      // Red - Alert/Error
      surprised: '#ffff00',  // Yellow - Curious
      fearful: '#ff00ff',    // Magenta - Fearful
      disgusted: '#ff8800',  // Orange - Disgusted
    };
    setGlowColor(colorMap[emotion]);
  }, [emotion]);

  // Animation loop
  useFrame((state) => {
    if (!robotRef.current) return;
    const time = state.clock.getElapsedTime();

    // Map emotion to behavior for automatic animations
    let activeBehavior = behavior;
    if (behavior === 'idle') {
      if (emotion === 'happy') activeBehavior = 'celebrating';
      else if (emotion === 'surprised') activeBehavior = 'analyzing';
      else if (emotion === 'sad') activeBehavior = 'thinking';
    }

    // Idle floating animation
    if (activeBehavior === 'idle') {
      robotRef.current.position.y = Math.sin(time * 0.5) * 0.1;
      robotRef.current.rotation.y = Math.sin(time * 0.3) * 0.1;
    }

    // Typing animation - head nod
    if (activeBehavior === 'typing' && headRef.current) {
      headRef.current.rotation.x = Math.sin(time * 3) * 0.1;
    }

    // Analyzing animation - head scanning (surprised)
    if (activeBehavior === 'analyzing' && headRef.current) {
      headRef.current.rotation.y = Math.sin(time * 2) * 0.3;
      headRef.current.rotation.x = Math.sin(time * 1.5) * 0.15;
    }

    // Explaining animation - arm gestures
    if (activeBehavior === 'explaining') {
      if (leftArmRef.current) {
        leftArmRef.current.rotation.z = Math.sin(time * 2) * 0.3 + 0.5;
      }
      if (rightArmRef.current) {
        rightArmRef.current.rotation.z = Math.sin(time * 2 + Math.PI) * 0.3 - 0.5;
      }
    }

    // Celebrating animation - jump and wave (happy)
    if (activeBehavior === 'celebrating') {
      robotRef.current.position.y = Math.abs(Math.sin(time * 4)) * 0.3;
      if (rightArmRef.current) {
        rightArmRef.current.rotation.z = Math.sin(time * 8) * 0.5 - 0.8;
      }
    }

    // Thinking animation - slow head tilt (sad)
    if (activeBehavior === 'thinking' && headRef.current) {
      headRef.current.rotation.z = Math.sin(time * 0.8) * 0.2;
      robotRef.current.position.y = Math.sin(time * 0.3) * 0.05; // Slower droop
    }

    // Eye blinking
    const blinkFrequency = behavior === 'idle' ? 0.3 : 0.5;
    const blink = Math.sin(time * blinkFrequency);
    if (blink > 0.95) {
      setEyeScale(0.1);
    } else {
      setEyeScale(1);
    }

    // Emotion-based eye reactions
    if (emotion === 'surprised') {
      setEyeScale(1.5);
    } else if (emotion === 'sad') {
      setEyeScale(0.8);
    }
  });

  return (
    <group ref={robotRef}>
      {/* Body */}
      <mesh ref={bodyRef} position={[0, -0.3, 0]}>
        <boxGeometry args={[0.6, 0.8, 0.4]} />
        <meshStandardMaterial 
          color="#1a1a2e" 
          emissive={glowColor}
          emissiveIntensity={0.3}
          metalness={0.8}
          roughness={0.2}
        />
      </mesh>

      {/* Chest Glow Panel */}
      <mesh position={[0, -0.3, 0.21]}>
        <boxGeometry args={[0.3, 0.3, 0.02]} />
        <meshStandardMaterial 
          color={glowColor}
          emissive={glowColor}
          emissiveIntensity={1.5}
          toneMapped={false}
        />
      </mesh>

      {/* Head */}
      <mesh ref={headRef} position={[0, 0.5, 0]}>
        <boxGeometry args={[0.5, 0.5, 0.5]} />
        <meshStandardMaterial 
          color="#2a2a3e" 
          emissive={glowColor}
          emissiveIntensity={0.2}
          metalness={0.9}
          roughness={0.1}
        />
      </mesh>

      {/* Left Eye */}
      <mesh ref={leftEyeRef} position={[-0.12, 0.55, 0.26]} scale={[1, eyeScale, 1]}>
        <sphereGeometry args={[0.08, 16, 16]} />
        <meshStandardMaterial 
          color={glowColor}
          emissive={glowColor}
          emissiveIntensity={3}
          toneMapped={false}
        />
      </mesh>

      {/* Right Eye */}
      <mesh ref={rightEyeRef} position={[0.12, 0.55, 0.26]} scale={[1, eyeScale, 1]}>
        <sphereGeometry args={[0.08, 16, 16]} />
        <meshStandardMaterial 
          color={glowColor}
          emissive={glowColor}
          emissiveIntensity={3}
          toneMapped={false}
        />
      </mesh>

      {/* Antenna */}
      <mesh position={[0, 0.8, 0]}>
        <cylinderGeometry args={[0.02, 0.02, 0.3, 8]} />
        <meshStandardMaterial 
          color={glowColor}
          emissive={glowColor}
          emissiveIntensity={1}
        />
      </mesh>
      <mesh position={[0, 0.95, 0]}>
        <sphereGeometry args={[0.06, 16, 16]} />
        <meshStandardMaterial 
          color={glowColor}
          emissive={glowColor}
          emissiveIntensity={2}
          toneMapped={false}
        />
      </mesh>

      {/* Left Arm */}
      <group ref={leftArmRef} position={[-0.4, -0.1, 0]}>
        <mesh>
          <cylinderGeometry args={[0.08, 0.08, 0.6, 8]} />
          <meshStandardMaterial 
            color="#2a2a3e" 
            metalness={0.8}
            roughness={0.3}
          />
        </mesh>
        <mesh position={[0, -0.35, 0]}>
          <sphereGeometry args={[0.1, 16, 16]} />
          <meshStandardMaterial 
            color={glowColor}
            emissive={glowColor}
            emissiveIntensity={0.5}
          />
        </mesh>
      </group>

      {/* Right Arm */}
      <group ref={rightArmRef} position={[0.4, -0.1, 0]}>
        <mesh>
          <cylinderGeometry args={[0.08, 0.08, 0.6, 8]} />
          <meshStandardMaterial 
            color="#2a2a3e" 
            metalness={0.8}
            roughness={0.3}
          />
        </mesh>
        <mesh position={[0, -0.35, 0]}>
          <sphereGeometry args={[0.1, 16, 16]} />
          <meshStandardMaterial 
            color={glowColor}
            emissive={glowColor}
            emissiveIntensity={0.5}
          />
        </mesh>
      </group>

      {/* Point Light for glow effect */}
      <pointLight 
        position={[0, 0.5, 0.5]} 
        color={glowColor} 
        intensity={isActive ? 2 : 1} 
        distance={3}
      />
    </group>
  );
}

export const RobotAvatar = ({ emotion, behavior, isActive }: RobotAvatarProps) => {
  return (
    <div className="w-full h-full">
      <Canvas camera={{ position: [0, 0, 3], fov: 50 }}>
        <ambientLight intensity={0.3} />
        <directionalLight position={[5, 5, 5]} intensity={0.5} />
        <Float
          speed={1.5}
          rotationIntensity={0.3}
          floatIntensity={0.5}
        >
          <RobotMesh emotion={emotion} behavior={behavior} isActive={isActive} />
        </Float>
        <OrbitControls 
          enableZoom={false} 
          enablePan={false}
          minPolarAngle={Math.PI / 3}
          maxPolarAngle={Math.PI / 1.5}
        />
      </Canvas>
    </div>
  );
};
