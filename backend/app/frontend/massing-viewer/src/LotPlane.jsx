import React, { useMemo } from 'react';
import { Line } from '@react-three/drei';
import * as THREE from 'three';

/**
 * Ground-level lot boundary and setback/yard indicators.
 */
export default function LotPlane({ lot, showSetbacks }) {
  const polygon = lot.polygon || [];
  const w = lot.frontage_ft || 50;
  const d = lot.depth_ft || 100;

  // Lot boundary polygon (or rectangle fallback)
  const lotBoundary = useMemo(() => {
    if (polygon.length >= 3) {
      return [...polygon.map(([x, z]) => [x, 0.15, z]), [polygon[0][0], 0.15, polygon[0][1]]];
    }
    return [
      [0, 0.15, 0], [w, 0.15, 0], [w, 0.15, d], [0, 0.15, d], [0, 0.15, 0],
    ];
  }, [polygon, w, d]);

  // Lot fill
  const lotFillGeo = useMemo(() => {
    const shape = new THREE.Shape();
    if (polygon.length >= 3) {
      shape.moveTo(polygon[0][0], polygon[0][1]);
      for (let i = 1; i < polygon.length; i++) {
        shape.lineTo(polygon[i][0], polygon[i][1]);
      }
    } else {
      shape.moveTo(0, 0);
      shape.lineTo(w, 0);
      shape.lineTo(w, d);
      shape.lineTo(0, d);
    }
    shape.closePath();
    const geo = new THREE.ShapeGeometry(shape);
    geo.rotateX(-Math.PI / 2);
    return geo;
  }, [polygon, w, d]);

  // Street edges (thicker line)
  const streetEdges = (lot.street_edges || []).map((se) => {
    if (!se.edge || se.edge.length < 2) return null;
    return se.edge.map(([x, z]) => [x, 0.2, z]);
  }).filter(Boolean);

  return (
    <group>
      {/* Lot fill — subtle green-ish tint */}
      <mesh geometry={lotFillGeo} position={[0, 0.05, 0]}>
        <meshBasicMaterial
          color="#b8d4b8"
          transparent
          opacity={0.25}
          side={THREE.DoubleSide}
        />
      </mesh>

      {/* Lot boundary line */}
      <Line
        points={lotBoundary}
        color="#333"
        lineWidth={2}
      />

      {/* Street edges (bold) */}
      {streetEdges.map((pts, i) => (
        <Line
          key={`street-${i}`}
          points={pts}
          color="#e74c3c"
          lineWidth={3}
        />
      ))}

      {/* Setback / yard indicators */}
      {showSetbacks && <SetbackIndicators lot={lot} />}
    </group>
  );
}


/**
 * Dashed lines showing required yard setbacks.
 * Assumes rectangular lot: front at z=0, rear at z=depth.
 */
function SetbackIndicators({ lot }) {
  const w = lot.frontage_ft || 50;
  const d = lot.depth_ft || 100;

  // Extract yard info from the first scenario or lot data
  // We'll render rear yard (most common) as a dashed line
  const rearYard = 30; // Default NYC rear yard
  const rearZ = d - rearYard;

  const lines = [];

  // Rear yard setback
  if (rearYard > 0 && rearZ > 0) {
    lines.push({
      key: 'rear',
      points: [[0, 0.2, rearZ], [w, 0.2, rearZ]],
      color: '#f39c12',
      label: `Rear Yard (${rearYard} ft)`,
    });

    // Rear yard fill
    lines.push({
      key: 'rear-fill',
      fill: true,
      polygon: [[0, rearZ], [w, rearZ], [w, d], [0, d]],
      color: '#f39c12',
    });
  }

  return (
    <group>
      {lines.map((line) => {
        if (line.fill) {
          return <YardFill key={line.key} polygon={line.polygon} color={line.color} />;
        }
        return (
          <Line
            key={line.key}
            points={line.points}
            color={line.color}
            lineWidth={1.5}
            dashed
            dashSize={2}
            gapSize={1.5}
          />
        );
      })}
    </group>
  );
}


/** Transparent fill for a yard area */
function YardFill({ polygon, color }) {
  const geometry = useMemo(() => {
    const shape = new THREE.Shape();
    shape.moveTo(polygon[0][0], polygon[0][1]);
    for (let i = 1; i < polygon.length; i++) {
      shape.lineTo(polygon[i][0], polygon[i][1]);
    }
    shape.closePath();
    const geo = new THREE.ShapeGeometry(shape);
    geo.rotateX(-Math.PI / 2);
    return geo;
  }, [polygon]);

  return (
    <mesh geometry={geometry} position={[0, 0.08, 0]}>
      <meshBasicMaterial
        color={color}
        transparent
        opacity={0.12}
        side={THREE.DoubleSide}
      />
    </mesh>
  );
}
