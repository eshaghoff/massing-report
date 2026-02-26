import React, { useMemo } from 'react';
import { Line } from '@react-three/drei';
import * as THREE from 'three';

/**
 * Renders a transparent wireframe showing the maximum zoning envelope:
 * - Max height horizontal plane
 * - Base height horizontal line
 * - Setback lines on the ground plane
 * - Sky exposure plane (if Height Factor scenario)
 */
export default function ZoningEnvelope({ envelope, lot }) {
  const w = lot.frontage_ft || 50;
  const d = lot.depth_ft || 100;
  const maxH = envelope.max_height_ft || 100;
  const baseH = envelope.base_height_max_ft || 60;

  // Max height plane (top of envelope)
  const topPlane = useMemo(() => {
    const geo = new THREE.PlaneGeometry(w + 4, d + 4);
    geo.rotateX(-Math.PI / 2);
    return geo;
  }, [w, d]);

  // Base height plane
  const basePlane = useMemo(() => {
    const geo = new THREE.PlaneGeometry(w + 4, d + 4);
    geo.rotateX(-Math.PI / 2);
    return geo;
  }, [w, d]);

  // Vertical edges of the envelope box
  const corners = [
    [0, 0], [w, 0], [w, d], [0, d],
  ];

  // Setback line (if present)
  const setbackLine = envelope.setback_line;

  // Sky exposure plane
  const sep = envelope.sky_exposure_plane;

  return (
    <group>
      {/* Max height plane — transparent blue */}
      <mesh geometry={topPlane} position={[w / 2, maxH, d / 2]}>
        <meshBasicMaterial
          color="#4A90D9"
          transparent
          opacity={0.08}
          side={THREE.DoubleSide}
        />
      </mesh>

      {/* Max height border lines */}
      <Line
        points={[
          [0, maxH, 0], [w, maxH, 0], [w, maxH, d], [0, maxH, d], [0, maxH, 0],
        ]}
        color="#4A90D9"
        lineWidth={1.5}
        dashed
        dashSize={3}
        gapSize={2}
      />

      {/* Base height plane — transparent green */}
      {baseH > 0 && baseH < maxH && (
        <>
          <mesh geometry={basePlane} position={[w / 2, baseH, d / 2]}>
            <meshBasicMaterial
              color="#6BBF6B"
              transparent
              opacity={0.06}
              side={THREE.DoubleSide}
            />
          </mesh>
          <Line
            points={[
              [0, baseH, 0], [w, baseH, 0], [w, baseH, d], [0, baseH, d], [0, baseH, 0],
            ]}
            color="#6BBF6B"
            lineWidth={1}
            dashed
            dashSize={2}
            gapSize={2}
          />
        </>
      )}

      {/* Vertical edges */}
      {corners.map(([cx, cz], i) => (
        <Line
          key={`vert-${i}`}
          points={[[cx, 0, cz], [cx, maxH, cz]]}
          color="#4A90D9"
          lineWidth={0.5}
          transparent
          opacity={0.3}
        />
      ))}

      {/* Setback line on the ground and at base height */}
      {setbackLine && setbackLine.length >= 2 && (
        <>
          {/* Setback at grade */}
          <Line
            points={setbackLine.map(([x, z]) => [x, 0.2, z])}
            color="#e74c3c"
            lineWidth={1.5}
            dashed
            dashSize={2}
            gapSize={1}
          />
          {/* Setback at base height */}
          <Line
            points={setbackLine.map(([x, z]) => [x, baseH, z])}
            color="#e74c3c"
            lineWidth={1.5}
            dashed
            dashSize={2}
            gapSize={1}
          />
          {/* Vertical line connecting setback at grade to base */}
          <Line
            points={[
              [setbackLine[0][0], 0.2, setbackLine[0][1]],
              [setbackLine[0][0], baseH, setbackLine[0][1]],
            ]}
            color="#e74c3c"
            lineWidth={0.5}
            transparent
            opacity={0.4}
          />
        </>
      )}

      {/* Sky exposure plane */}
      {sep && <SkyExposurePlane sep={sep} lot={lot} />}
    </group>
  );
}


/**
 * Renders the sky exposure plane as angled triangular planes.
 */
function SkyExposurePlane({ sep, lot }) {
  const w = lot.frontage_ft || 50;
  const d = lot.depth_ft || 100;
  const startH = sep.start_height || 60;
  const slope = sep.slope || 2.7; // rise per ft of setback
  const maxH = (lot.depth_ft || 100) * slope + startH;

  // SEP slopes inward from the street (front edge z=0 going to rear z=d)
  // At the street line (z=0): height = startH
  // Going back: height = startH + z * slope
  // But SEP usually slopes inward, so: height = startH + distance * slope_ratio
  // For simplicity, show a single sloped plane from the front

  const geometry = useMemo(() => {
    const vertices = new Float32Array([
      // Front edge at start height
      0, startH, 0,
      w, startH, 0,
      // Back edge (capped at max allowable or lot depth * slope)
      w, Math.min(startH + d * slope, 300), d,
      0, Math.min(startH + d * slope, 300), d,
    ]);

    const indices = new Uint16Array([0, 1, 2, 0, 2, 3]);

    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(vertices, 3));
    geo.setIndex(new THREE.BufferAttribute(indices, 1));
    geo.computeVertexNormals();
    return geo;
  }, [w, d, startH, slope]);

  return (
    <mesh geometry={geometry}>
      <meshBasicMaterial
        color="#f39c12"
        transparent
        opacity={0.1}
        side={THREE.DoubleSide}
      />
    </mesh>
  );
}
