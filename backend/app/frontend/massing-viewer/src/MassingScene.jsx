import React, { useRef, useMemo, useCallback } from 'react';
import { Canvas, useThree } from '@react-three/fiber';
import { OrbitControls, Text, Line } from '@react-three/drei';
import * as THREE from 'three';
import BuildingMesh from './BuildingMesh';
import ZoningEnvelope from './ZoningEnvelope';
import LotPlane from './LotPlane';

/**
 * Main Three.js scene for rendering a single scenario's massing.
 */
export default function MassingScene({
  massingData,
  scenario,
  showEnvelope,
  showLotBoundary,
  showSetbacks,
  showFloorLabels,
  onFloorClick,
  onFloorHover,
  hoveredFloor,
}) {
  const lot = massingData.lot;

  // Compute scene center and camera position from lot dimensions
  const { center, cameraPos } = useMemo(() => {
    const w = lot.frontage_ft || 50;
    const d = lot.depth_ft || 100;
    const cx = w / 2;
    const cz = d / 2;
    // Position camera at a comfortable distance
    const maxDim = Math.max(w, d);
    const camDist = maxDim * 1.8;
    return {
      center: [cx, 0, cz],
      cameraPos: [cx + camDist * 0.6, camDist * 0.5, cz + camDist * 0.6],
    };
  }, [lot]);

  return (
    <Canvas
      gl={{ preserveDrawingBuffer: true, antialias: true }}
      camera={{ position: cameraPos, fov: 45, near: 0.1, far: 5000 }}
      shadows
    >
      {/* Lights */}
      <ambientLight intensity={0.5} />
      <directionalLight
        position={[100, 200, 100]}
        intensity={0.8}
        castShadow
        shadow-mapSize-width={2048}
        shadow-mapSize-height={2048}
        shadow-camera-far={500}
        shadow-camera-left={-200}
        shadow-camera-right={200}
        shadow-camera-top={200}
        shadow-camera-bottom={-200}
      />
      <directionalLight position={[-50, 80, -50]} intensity={0.3} />

      {/* Controls */}
      <OrbitControls
        target={center}
        enableDamping
        dampingFactor={0.1}
        maxPolarAngle={Math.PI / 2 - 0.05}
        minDistance={20}
        maxDistance={1000}
      />

      {/* Ground plane */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.1, 0]} receiveShadow>
        <planeGeometry args={[500, 500]} />
        <meshStandardMaterial color="#d4d8dc" />
      </mesh>

      {/* Lot boundary */}
      {showLotBoundary && <LotPlane lot={lot} showSetbacks={showSetbacks} />}

      {/* Building */}
      <BuildingMesh
        scenario={scenario}
        onFloorClick={onFloorClick}
        onFloorHover={onFloorHover}
        hoveredFloor={hoveredFloor}
        showFloorLabels={showFloorLabels}
      />

      {/* Zoning envelope */}
      {showEnvelope && scenario.zoning_envelope && (
        <ZoningEnvelope
          envelope={scenario.zoning_envelope}
          lot={lot}
        />
      )}

      {/* Street label */}
      {lot.street_edges && lot.street_edges.length > 0 && (
        <StreetLabel edge={lot.street_edges[0]} />
      )}

      {/* North arrow */}
      <NorthArrow position={[lot.frontage_ft + 15, 0.5, lot.depth_ft / 2]} />

      {/* Scale bar */}
      <ScaleBar position={[-5, 0.2, -5]} />
    </Canvas>
  );
}


/** Street name label positioned along the street edge */
function StreetLabel({ edge }) {
  const name = edge.street_name || 'Street';
  const widthLabel = edge.width === 'wide' ? ' (Wide)' : ' (Narrow)';
  const midX = (edge.edge[0][0] + edge.edge[1][0]) / 2;
  const midZ = (edge.edge[0][1] + edge.edge[1][1]) / 2;

  return (
    <Text
      position={[midX, 0.5, midZ - 8]}
      rotation={[-Math.PI / 2, 0, 0]}
      fontSize={4}
      color="#333"
      anchorX="center"
      anchorY="middle"
    >
      {name}{widthLabel}
    </Text>
  );
}


/** North arrow indicator */
function NorthArrow({ position }) {
  const [x, y, z] = position;
  return (
    <group position={position}>
      {/* Arrow shaft */}
      <Line
        points={[[0, 0, 0], [0, 0, -12]]}
        color="#333"
        lineWidth={2}
      />
      {/* Arrow head */}
      <Line
        points={[[-2, 0, -9], [0, 0, -12], [2, 0, -9]]}
        color="#333"
        lineWidth={2}
      />
      {/* N label */}
      <Text
        position={[0, 0.5, -16]}
        rotation={[-Math.PI / 2, 0, 0]}
        fontSize={4}
        color="#333"
        anchorX="center"
      >
        N
      </Text>
    </group>
  );
}


/** Scale bar showing 10 ft and 50 ft */
function ScaleBar({ position }) {
  return (
    <group position={position}>
      <Line
        points={[[0, 0, 0], [50, 0, 0]]}
        color="#555"
        lineWidth={2}
      />
      {/* Ticks */}
      <Line points={[[0, 0, -1], [0, 0, 1]]} color="#555" lineWidth={2} />
      <Line points={[[10, 0, -1], [10, 0, 1]]} color="#555" lineWidth={1} />
      <Line points={[[50, 0, -1], [50, 0, 1]]} color="#555" lineWidth={2} />
      <Text
        position={[0, 0.5, 3]}
        rotation={[-Math.PI / 2, 0, 0]}
        fontSize={2.5}
        color="#555"
        anchorX="center"
      >
        0
      </Text>
      <Text
        position={[50, 0.5, 3]}
        rotation={[-Math.PI / 2, 0, 0]}
        fontSize={2.5}
        color="#555"
        anchorX="center"
      >
        50 ft
      </Text>
    </group>
  );
}
