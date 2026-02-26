import React, { useRef, useMemo, useState } from 'react';
import { Text } from '@react-three/drei';
import * as THREE from 'three';

/**
 * Color map for floor use types.
 * In Three.js coordinates: x = lot width, y = height, z = lot depth.
 */
const USE_COLORS = {
  commercial: '#4A90D9',
  residential: '#F5E6CC',
  community_facility: '#6BBF6B',
  parking: '#999999',
  mechanical: '#777777',
  cellar: '#777777',
  core: '#555555',
};

const FLOOR_GAP = 0.3; // Gap between floors for visual clarity

/**
 * Renders all floors of a single scenario as extruded polygons.
 */
export default function BuildingMesh({
  scenario,
  onFloorClick,
  onFloorHover,
  hoveredFloor,
  showFloorLabels,
}) {
  if (!scenario || !scenario.floors) return null;

  return (
    <group>
      {scenario.floors.map((floor, idx) => (
        <FloorMesh
          key={idx}
          floor={floor}
          isHovered={hoveredFloor && hoveredFloor.floor_num === floor.floor_num}
          onClick={() => onFloorClick && onFloorClick(floor)}
          onHover={(hovered) => {
            if (onFloorHover) {
              onFloorHover(hovered ? floor : null);
            }
          }}
          showLabel={showFloorLabels}
        />
      ))}

      {/* Bulkhead */}
      {scenario.bulkhead && (
        <BulkheadMesh bulkhead={scenario.bulkhead} />
      )}
    </group>
  );
}


/**
 * Single floor rendered as an extruded polygon.
 * Floor footprint is a 2D polygon [[x, z], ...] extruded vertically.
 */
function FloorMesh({ floor, isHovered, onClick, onHover, showLabel }) {
  const meshRef = useRef();
  const [localHover, setLocalHover] = useState(false);

  const { geometry, color, elevation } = useMemo(() => {
    const poly = floor.footprint;
    if (!poly || poly.length < 3) return { geometry: null, color: '#ccc', elevation: 0 };

    // Create a Shape from the floor polygon
    const shape = new THREE.Shape();
    shape.moveTo(poly[0][0], poly[0][1]);
    for (let i = 1; i < poly.length; i++) {
      shape.lineTo(poly[i][0], poly[i][1]);
    }
    shape.closePath();

    // Extrude settings — extrude along Y axis
    const extrudeSettings = {
      depth: floor.height_ft - FLOOR_GAP,
      bevelEnabled: false,
    };

    const geo = new THREE.ExtrudeGeometry(shape, extrudeSettings);

    // Rotate to make the extrusion go up (Y axis) instead of Z
    // ExtrudeGeometry extrudes along +Z, so we rotate -90 around X
    // Actually, we'll handle positioning differently:
    // The shape is in the XY plane, extrude goes in Z.
    // We want: X = lot width, Z = lot depth, Y = height.
    // So we need to re-orient: shape XY → XZ, extrude Z → Y.
    // Easier: just rotate the geometry.
    geo.rotateX(-Math.PI / 2);

    const baseColor = USE_COLORS[floor.use] || '#cccccc';

    return {
      geometry: geo,
      color: baseColor,
      elevation: floor.elevation_ft,
    };
  }, [floor]);

  if (!geometry) return null;

  const highlight = isHovered || localHover;

  return (
    <group position={[0, elevation + FLOOR_GAP / 2, 0]}>
      <mesh
        ref={meshRef}
        geometry={geometry}
        onClick={(e) => {
          e.stopPropagation();
          onClick();
        }}
        onPointerEnter={(e) => {
          e.stopPropagation();
          setLocalHover(true);
          onHover(true);
          document.body.style.cursor = 'pointer';
        }}
        onPointerLeave={(e) => {
          e.stopPropagation();
          setLocalHover(false);
          onHover(false);
          document.body.style.cursor = 'default';
        }}
        castShadow
        receiveShadow
      >
        <meshStandardMaterial
          color={color}
          transparent={highlight}
          opacity={highlight ? 0.85 : 1}
          emissive={highlight ? '#ffffff' : '#000000'}
          emissiveIntensity={highlight ? 0.15 : 0}
        />
      </mesh>

      {/* Wireframe edges */}
      <mesh geometry={geometry}>
        <meshBasicMaterial
          color="#333333"
          wireframe
          transparent
          opacity={0.08}
        />
      </mesh>

      {/* Floor label */}
      {showLabel && (
        <FloorLabel floor={floor} />
      )}
    </group>
  );
}


/** Floating text label for a floor */
function FloorLabel({ floor }) {
  const poly = floor.footprint;
  if (!poly || poly.length < 2) return null;

  // Position label at the front-center of the floor, slightly outside
  const minX = Math.min(...poly.map(p => p[0]));
  const y = floor.height_ft / 2;

  return (
    <Text
      position={[minX - 2, y, poly[0][1]]}
      fontSize={2}
      color="#333"
      anchorX="right"
      anchorY="middle"
    >
      {`F${floor.floor_num}`}
    </Text>
  );
}


/** Bulkhead mesh */
function BulkheadMesh({ bulkhead }) {
  const geometry = useMemo(() => {
    const poly = bulkhead.footprint;
    if (!poly || poly.length < 3) return null;

    const shape = new THREE.Shape();
    shape.moveTo(poly[0][0], poly[0][1]);
    for (let i = 1; i < poly.length; i++) {
      shape.lineTo(poly[i][0], poly[i][1]);
    }
    shape.closePath();

    const geo = new THREE.ExtrudeGeometry(shape, {
      depth: bulkhead.height_ft,
      bevelEnabled: false,
    });
    geo.rotateX(-Math.PI / 2);
    return geo;
  }, [bulkhead]);

  if (!geometry) return null;

  return (
    <group position={[0, bulkhead.elevation_ft, 0]}>
      <mesh geometry={geometry} castShadow>
        <meshStandardMaterial color="#888888" />
      </mesh>
      <mesh geometry={geometry}>
        <meshBasicMaterial color="#333" wireframe transparent opacity={0.1} />
      </mesh>
    </group>
  );
}
