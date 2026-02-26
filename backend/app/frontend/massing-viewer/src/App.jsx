import React, { useState, useEffect, useCallback } from 'react';
import MassingScene from './MassingScene';
import InfoPanel from './InfoPanel';
import ComparisonView from './ComparisonView';
import './App.css';

/**
 * Main App — loads massing data and manages state for the 3D viewer.
 *
 * URL params:
 *   ?bbl=1234567890           — single lot
 *   ?bbl=1234567890,1234567891 — assemblage
 *   ?scenario=Max+Residential  — pre-select scenario
 *   ?data=...                  — inline JSON (from parent window postMessage)
 */
export default function App() {
  const [massingData, setMassingData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // UI state
  const [activeScenario, setActiveScenario] = useState(0);
  const [selectedFloor, setSelectedFloor] = useState(null);
  const [hoveredFloor, setHoveredFloor] = useState(null);
  const [showEnvelope, setShowEnvelope] = useState(false);
  const [showLotBoundary, setShowLotBoundary] = useState(true);
  const [showSetbacks, setShowSetbacks] = useState(true);
  const [showFloorLabels, setShowFloorLabels] = useState(false);
  const [comparisonMode, setComparisonMode] = useState(false);
  const [comparisonScenario, setComparisonScenario] = useState(1);

  // Load massing data
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const bbl = params.get('bbl');
    const scenarioName = params.get('scenario');

    // Check for data passed via postMessage from parent window
    const handleMessage = (event) => {
      if (event.data && event.data.type === 'MASSING_DATA') {
        setMassingData(event.data.payload);
        setLoading(false);
      }
    };
    window.addEventListener('message', handleMessage);

    // Check for inline data in URL hash
    if (window.location.hash && window.location.hash.length > 1) {
      try {
        const decoded = decodeURIComponent(window.location.hash.substring(1));
        const data = JSON.parse(decoded);
        setMassingData(data);
        setLoading(false);
        return () => window.removeEventListener('message', handleMessage);
      } catch (e) {
        // not inline data, continue to API fetch
      }
    }

    if (!bbl) {
      // Show demo data if no BBL provided
      setMassingData(getDemoData());
      setLoading(false);
      return () => window.removeEventListener('message', handleMessage);
    }

    // Fetch from API
    const fetchData = async () => {
      try {
        setLoading(true);
        const url = `/api/v1/massing/${bbl}${scenarioName ? `?scenario=${encodeURIComponent(scenarioName)}` : ''}`;
        const resp = await fetch(url);
        if (!resp.ok) {
          const err = await resp.json();
          throw new Error(err.detail || `HTTP ${resp.status}`);
        }
        const data = await resp.json();
        setMassingData(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchData();

    return () => window.removeEventListener('message', handleMessage);
  }, []);

  // Preselect scenario from URL
  useEffect(() => {
    if (!massingData) return;
    const params = new URLSearchParams(window.location.search);
    const scenarioName = params.get('scenario');
    if (scenarioName && massingData.scenarios) {
      const idx = massingData.scenarios.findIndex(
        (s) => s.name.toLowerCase().includes(scenarioName.toLowerCase())
      );
      if (idx >= 0) setActiveScenario(idx);
    }
  }, [massingData]);

  const handleScreenshot = useCallback(() => {
    const canvas = document.querySelector('canvas');
    if (!canvas) return;
    const link = document.createElement('a');
    link.download = `massing-${Date.now()}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
  }, []);

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="spinner" />
        <p>Loading massing data...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-screen">
        <h2>Error Loading Massing</h2>
        <p>{error}</p>
        <button onClick={() => window.location.reload()}>Retry</button>
      </div>
    );
  }

  if (!massingData || !massingData.scenarios || massingData.scenarios.length === 0) {
    return (
      <div className="error-screen">
        <h2>No Massing Data</h2>
        <p>No development scenarios found for this lot.</p>
      </div>
    );
  }

  const scenarios = massingData.scenarios;
  const currentScenario = scenarios[activeScenario] || scenarios[0];

  return (
    <div className="app">
      {/* Top toolbar */}
      <div className="toolbar">
        <div className="toolbar-left">
          <h1>NYC Zoning — 3D Massing</h1>
          <select
            value={activeScenario}
            onChange={(e) => {
              setActiveScenario(Number(e.target.value));
              setSelectedFloor(null);
              setHoveredFloor(null);
            }}
          >
            {scenarios.map((s, i) => (
              <option key={i} value={i}>{s.name}</option>
            ))}
          </select>
        </div>
        <div className="toolbar-right">
          <label>
            <input type="checkbox" checked={showEnvelope} onChange={(e) => setShowEnvelope(e.target.checked)} />
            Envelope
          </label>
          <label>
            <input type="checkbox" checked={showLotBoundary} onChange={(e) => setShowLotBoundary(e.target.checked)} />
            Lot
          </label>
          <label>
            <input type="checkbox" checked={showSetbacks} onChange={(e) => setShowSetbacks(e.target.checked)} />
            Setbacks
          </label>
          <label>
            <input type="checkbox" checked={showFloorLabels} onChange={(e) => setShowFloorLabels(e.target.checked)} />
            Labels
          </label>
          <button
            className={`btn-toggle ${comparisonMode ? 'active' : ''}`}
            onClick={() => setComparisonMode(!comparisonMode)}
          >
            Compare
          </button>
          <button className="btn-icon" onClick={handleScreenshot} title="Screenshot">
            📷
          </button>
        </div>
      </div>

      <div className="main-content">
        {/* 3D Scene */}
        <div className="scene-container">
          {comparisonMode ? (
            <ComparisonView
              massingData={massingData}
              scenarioA={activeScenario}
              scenarioB={comparisonScenario}
              showEnvelope={showEnvelope}
              showLotBoundary={showLotBoundary}
              showSetbacks={showSetbacks}
              showFloorLabels={showFloorLabels}
            />
          ) : (
            <MassingScene
              massingData={massingData}
              scenario={currentScenario}
              showEnvelope={showEnvelope}
              showLotBoundary={showLotBoundary}
              showSetbacks={showSetbacks}
              showFloorLabels={showFloorLabels}
              onFloorClick={setSelectedFloor}
              onFloorHover={setHoveredFloor}
              hoveredFloor={hoveredFloor}
            />
          )}
        </div>

        {/* Side Panel */}
        <InfoPanel
          scenario={currentScenario}
          lot={massingData.lot}
          selectedFloor={selectedFloor}
          hoveredFloor={hoveredFloor}
          warnings={massingData.warnings}
          comparisonMode={comparisonMode}
          comparisonScenario={comparisonScenario}
          setComparisonScenario={setComparisonScenario}
          scenarios={scenarios}
          activeScenario={activeScenario}
        />
      </div>

      {/* Floor tooltip on hover */}
      {hoveredFloor && !selectedFloor && (
        <div className="floor-tooltip" style={{ pointerEvents: 'none' }}>
          <strong>Floor {hoveredFloor.floor_num}</strong>
          <span>{hoveredFloor.use}</span>
          <span>{(hoveredFloor.gross_area_sf || 0).toLocaleString()} SF</span>
        </div>
      )}
    </div>
  );
}


/** Demo data for when no BBL is provided */
function getDemoData() {
  const lotW = 50, lotD = 100, rearYard = 30;
  const bldgW = lotW, bldgD = lotD - rearYard;
  const lotPoly = [[0,0],[lotW,0],[lotW,lotD],[0,lotD]];
  const basePoly = [[0,0],[bldgW,0],[bldgW,bldgD],[0,bldgD]];
  const setbackPoly = [[10,0],[bldgW,0],[bldgW,bldgD],[10,bldgD]];

  const floors = [];
  // Ground floor commercial
  floors.push({
    floor_num: 1, use: 'commercial', elevation_ft: 0, height_ft: 15,
    footprint: basePoly, gross_area_sf: bldgW * bldgD, net_area_sf: bldgW * bldgD * 0.82,
    setback_from_street_ft: 0, setback_from_rear_ft: rearYard,
  });
  // Floors 2-6 residential at base
  for (let i = 2; i <= 6; i++) {
    floors.push({
      floor_num: i, use: 'residential',
      elevation_ft: 15 + (i - 2) * 10, height_ft: 10,
      footprint: basePoly, gross_area_sf: bldgW * bldgD, net_area_sf: bldgW * bldgD * 0.82,
      setback_from_street_ft: 0, setback_from_rear_ft: rearYard,
    });
  }
  // Floors 7-8 residential with setback
  for (let i = 7; i <= 8; i++) {
    floors.push({
      floor_num: i, use: 'residential',
      elevation_ft: 15 + (i - 2) * 10, height_ft: 10,
      footprint: setbackPoly, gross_area_sf: (bldgW - 10) * bldgD,
      net_area_sf: (bldgW - 10) * bldgD * 0.82,
      setback_from_street_ft: 10, setback_from_rear_ft: rearYard,
    });
  }

  return {
    lot: {
      polygon: lotPoly,
      area_sf: lotW * lotD,
      frontage_ft: lotW,
      depth_ft: lotD,
      street_edges: [{ edge: [[0,0],[lotW,0]], street_name: 'Main St', width: 'narrow' }],
    },
    scenarios: [{
      name: 'Demo — Max Residential (Quality Housing)',
      floors,
      bulkhead: {
        footprint: [[15,20],[35,20],[35,50],[15,50]],
        height_ft: 15, elevation_ft: 85,
      },
      zoning_envelope: {
        max_height_ft: 95, base_height_max_ft: 65,
        sky_exposure_plane: null,
        setback_line: [[10,0],[10,bldgD]],
      },
      summary: {
        total_zfa: 22000, max_height: 95, floors: 8,
        units: 24, loss_factor: 0.18, parking_spaces: 6,
      },
    }],
    origin: { lat: 40.7128, lng: -74.006 },
    warnings: ['Demo data — not a real zoning analysis'],
  };
}
