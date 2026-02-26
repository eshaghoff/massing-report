import { useRef, useMemo } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Text, Line, PerspectiveCamera } from '@react-three/drei';
import * as THREE from 'three';
import type { MassingGeometry, DevelopmentScenario } from '../types';

interface MassingViewerProps {
  scenarios: DevelopmentScenario[];
  activeScenario: number;
}

function BuildingMesh({ geometry }: { geometry: MassingGeometry }) {
  const meshRef = useRef<THREE.Group>(null);

  const { positions, colorArray } = useMemo(() => {
    if (!geometry?.vertices?.length || !geometry?.faces?.length) {
      return { positions: new Float32Array(0), colorArray: new Float32Array(0) };
    }

    const verts = geometry.vertices;
    const faces = geometry.faces;
    const colors = geometry.colors || [];

    // Expand faces into non-indexed triangles with per-face colors
    const triPositions: number[] = [];
    const triColors: number[] = [];

    for (let i = 0; i < faces.length; i++) {
      const [a, b, c] = faces[i];
      if (a >= verts.length || b >= verts.length || c >= verts.length) continue;

      const va = verts[a];
      const vb = verts[b];
      const vc = verts[c];

      triPositions.push(va[0], va[2], -va[1]); // swap Y/Z for Three.js
      triPositions.push(vb[0], vb[2], -vb[1]);
      triPositions.push(vc[0], vc[2], -vc[1]);

      const color = new THREE.Color(colors[i] || '#CCCCCC');
      triColors.push(color.r, color.g, color.b);
      triColors.push(color.r, color.g, color.b);
      triColors.push(color.r, color.g, color.b);
    }

    return {
      positions: new Float32Array(triPositions),
      colorArray: new Float32Array(triColors),
    };
  }, [geometry]);

  const positionAttr = useMemo(() => {
    if (positions.length === 0) return null;
    return new THREE.BufferAttribute(positions, 3);
  }, [positions]);

  const colorAttr = useMemo(() => {
    if (colorArray.length === 0) return null;
    return new THREE.BufferAttribute(colorArray, 3);
  }, [colorArray]);

  if (!positionAttr) return null;

  return (
    <group ref={meshRef}>
      <mesh>
        <bufferGeometry>
          <primitive attach="attributes-position" object={positionAttr} />
          {colorAttr && <primitive attach="attributes-color" object={colorAttr} />}
        </bufferGeometry>
        <meshStandardMaterial
          vertexColors
          side={THREE.DoubleSide}
          transparent
          opacity={0.85}
        />
      </mesh>
      {/* Wireframe overlay */}
      <mesh>
        <bufferGeometry>
          <primitive attach="attributes-position" object={positionAttr} />
        </bufferGeometry>
        <meshBasicMaterial wireframe color="#333" transparent opacity={0.15} />
      </mesh>
    </group>
  );
}

function EnvelopeWireframe({ wireframe }: { wireframe: MassingGeometry['envelope_wireframe'] }) {
  if (!wireframe?.length) return null;

  return (
    <group>
      {wireframe.map((edge, i) => (
        <Line
          key={i}
          points={[
            [edge.start[0], edge.start[2], -edge.start[1]],
            [edge.end[0], edge.end[2], -edge.end[1]],
          ]}
          color="#FFD700"
          lineWidth={1}
          transparent
          opacity={0.4}
          dashed
          dashSize={3}
          gapSize={2}
        />
      ))}
    </group>
  );
}

function Ground() {
  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.1, 0]} receiveShadow>
      <planeGeometry args={[500, 500]} />
      <meshStandardMaterial color="#e8e8e0" transparent opacity={0.6} />
    </mesh>
  );
}

function GridHelper() {
  return <gridHelper args={[500, 50, '#ccc', '#eee']} position={[0, 0, 0]} />;
}

function NorthArrow() {
  return (
    <group position={[100, 0, -100]}>
      <Line
        points={[[0, 0, 0], [0, 20, 0]]}
        color="red"
        lineWidth={2}
      />
      <Text
        position={[0, 25, 0]}
        fontSize={8}
        color="red"
        anchorX="center"
        anchorY="bottom"
      >
        N
      </Text>
    </group>
  );
}

function ScaleBar() {
  return (
    <group position={[-100, 0, 100]}>
      <Line
        points={[[-25, 0.5, 0], [25, 0.5, 0]]}
        color="#333"
        lineWidth={2}
      />
      <Text position={[0, 5, 0]} fontSize={5} color="#333" anchorX="center">
        50 ft
      </Text>
    </group>
  );
}

function Scene({ scenario }: { scenario: DevelopmentScenario }) {
  const massing = scenario.massing_geometry;

  // Calculate camera distance based on building height
  const maxH = scenario.max_height_ft || 100;
  const camDist = Math.max(maxH * 2, 200);

  return (
    <>
      <PerspectiveCamera
        makeDefault
        position={[camDist * 0.7, camDist * 0.5, camDist * 0.7]}
        fov={45}
        near={1}
        far={5000}
      />
      <ambientLight intensity={0.5} />
      <directionalLight position={[100, 200, 100]} intensity={0.8} castShadow />
      <directionalLight position={[-50, 100, -50]} intensity={0.3} />

      {massing && <BuildingMesh geometry={massing} />}
      {massing?.envelope_wireframe && (
        <EnvelopeWireframe wireframe={massing.envelope_wireframe} />
      )}

      <Ground />
      <GridHelper />
      <NorthArrow />
      <ScaleBar />

      <OrbitControls
        enablePan
        enableZoom
        enableRotate
        minDistance={50}
        maxDistance={2000}
        maxPolarAngle={Math.PI / 2 - 0.05}
      />
    </>
  );
}

export default function MassingViewer({ scenarios, activeScenario }: MassingViewerProps) {
  const scenario = scenarios[activeScenario];

  if (!scenario) {
    return (
      <div style={{
        height: '100%', display: 'flex', alignItems: 'center',
        justifyContent: 'center', color: '#888', fontSize: 14
      }}>
        No scenario data available
      </div>
    );
  }

  return (
    <div style={{ height: '100%', position: 'relative' }}>
      <Canvas shadows>
        <Scene scenario={scenario} />
      </Canvas>

      {/* Legend */}
      <div style={{
        position: 'absolute', bottom: 16, left: 16,
        background: 'rgba(255,255,255,0.92)', borderRadius: 8,
        padding: '10px 14px', fontSize: 12, boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
      }}>
        <div style={{ fontWeight: 600, marginBottom: 6 }}>Legend</div>
        {[
          { color: '#4A90D9', label: 'Residential' },
          { color: '#D94A4A', label: 'Commercial' },
          { color: '#4AD97A', label: 'Community Facility' },
          { color: '#888888', label: 'Parking' },
          { color: '#FFD700', label: 'Zoning Envelope' },
        ].map(({ color, label }) => (
          <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3 }}>
            <div style={{ width: 12, height: 12, borderRadius: 2, backgroundColor: color }} />
            <span>{label}</span>
          </div>
        ))}
      </div>

      {/* Building info overlay */}
      <div style={{
        position: 'absolute', top: 16, right: 16,
        background: 'rgba(255,255,255,0.92)', borderRadius: 8,
        padding: '10px 14px', fontSize: 12, boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
        maxWidth: 220,
      }}>
        <div style={{ fontWeight: 600, marginBottom: 6 }}>{scenario.name}</div>
        <div>Height: {Math.round(scenario.max_height_ft)} ft</div>
        <div>Floors: {scenario.num_floors}</div>
        <div>Gross SF: {Math.round(scenario.total_gross_sf).toLocaleString()}</div>
        <div>FAR Used: {scenario.far_used}</div>
      </div>
    </div>
  );
}
