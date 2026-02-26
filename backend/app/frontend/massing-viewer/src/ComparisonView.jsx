import React, { useMemo } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Text, Line } from '@react-three/drei';
import * as THREE from 'three';
import BuildingMesh from './BuildingMesh';
import LotPlane from './LotPlane';
import ZoningEnvelope from './ZoningEnvelope';

/**
 * Side-by-side comparison of two scenarios.
 * Renders both buildings offset on duplicate lots.
 */
export default function ComparisonView({
  massingData,
  scenarioA,
  scenarioB,
  showEnvelope,
  showLotBoundary,
  showSetbacks,
  showFloorLabels,
}) {
  const lot = massingData.lot;
  const scenarios = massingData.scenarios;
  const scA = scenarios[scenarioA];
  const scB = scenarios[scenarioB] || scenarios[0];

  const w = lot.frontage_ft || 50;
  const d = lot.depth_ft || 100;
  const gap = 20; // Gap between the two buildings
  const offsetB = w + gap;

  const { center, cameraPos } = useMemo(() => {
    const totalW = w * 2 + gap;
    const cx = totalW / 2;
    const cz = d / 2;
    const camDist = Math.max(totalW, d) * 1.6;
    return {
      center: [cx, 0, cz],
      cameraPos: [cx + camDist * 0.5, camDist * 0.5, cz + camDist * 0.5],
    };
  }, [w, d, gap]);

  return (
    <Canvas
      gl={{ preserveDrawingBuffer: true, antialias: true }}
      camera={{ position: cameraPos, fov: 45, near: 0.1, far: 5000 }}
      shadows
    >
      <ambientLight intensity={0.5} />
      <directionalLight
        position={[150, 200, 100]}
        intensity={0.8}
        castShadow
        shadow-mapSize-width={2048}
        shadow-mapSize-height={2048}
      />
      <directionalLight position={[-50, 80, -50]} intensity={0.3} />

      <OrbitControls
        target={center}
        enableDamping
        dampingFactor={0.1}
        maxPolarAngle={Math.PI / 2 - 0.05}
        minDistance={20}
        maxDistance={1500}
      />

      {/* Ground */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.1, 0]} receiveShadow>
        <planeGeometry args={[600, 600]} />
        <meshStandardMaterial color="#d4d8dc" />
      </mesh>

      {/* Scenario A (left) */}
      <group position={[0, 0, 0]}>
        {showLotBoundary && <LotPlane lot={lot} showSetbacks={showSetbacks} />}
        <BuildingMesh
          scenario={scA}
          showFloorLabels={showFloorLabels}
          onFloorClick={() => {}}
          onFloorHover={() => {}}
        />
        {showEnvelope && scA.zoning_envelope && (
          <ZoningEnvelope envelope={scA.zoning_envelope} lot={lot} />
        )}
        <Text
          position={[w / 2, -3, -6]}
          rotation={[-Math.PI / 2, 0, 0]}
          fontSize={3}
          color="#333"
          anchorX="center"
        >
          {scA.name || 'Scenario A'}
        </Text>
      </group>

      {/* Scenario B (right) */}
      <group position={[offsetB, 0, 0]}>
        {showLotBoundary && <LotPlane lot={lot} showSetbacks={showSetbacks} />}
        <BuildingMesh
          scenario={scB}
          showFloorLabels={showFloorLabels}
          onFloorClick={() => {}}
          onFloorHover={() => {}}
        />
        {showEnvelope && scB.zoning_envelope && (
          <ZoningEnvelope envelope={scB.zoning_envelope} lot={lot} />
        )}
        <Text
          position={[w / 2, -3, -6]}
          rotation={[-Math.PI / 2, 0, 0]}
          fontSize={3}
          color="#333"
          anchorX="center"
        >
          {scB.name || 'Scenario B'}
        </Text>
      </group>

      {/* Divider label */}
      <Text
        position={[w + gap / 2, 1, -10]}
        rotation={[-Math.PI / 2, 0, 0]}
        fontSize={2.5}
        color="#999"
        anchorX="center"
      >
        vs
      </Text>
    </Canvas>
  );
}
