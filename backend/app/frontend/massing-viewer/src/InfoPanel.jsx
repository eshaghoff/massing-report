import React from 'react';

/**
 * Right-hand side info panel showing scenario metrics,
 * floor details (on click), and comparison controls.
 */
export default function InfoPanel({
  scenario,
  lot,
  selectedFloor,
  hoveredFloor,
  warnings,
  comparisonMode,
  comparisonScenario,
  setComparisonScenario,
  scenarios,
  activeScenario,
}) {
  const summary = scenario?.summary || {};

  return (
    <div className="info-panel">
      {/* Scenario summary */}
      <h2>{scenario?.name || 'Scenario'}</h2>

      <h3>Building Summary</h3>
      <MetricRow label="Total ZFA" value={fmt(summary.total_zfa, ' SF')} />
      <MetricRow label="Max Height" value={fmt(summary.max_height, ' ft')} />
      <MetricRow label="Floors" value={summary.floors} />
      <MetricRow label="Units" value={summary.units} />
      <MetricRow
        label="Loss Factor"
        value={summary.loss_factor != null ? `${(summary.loss_factor * 100).toFixed(0)}%` : 'N/A'}
      />
      <MetricRow label="Parking" value={summary.parking_spaces} />

      {/* Lot info */}
      <h3>Lot</h3>
      <MetricRow label="Area" value={fmt(lot?.area_sf, ' SF')} />
      <MetricRow label="Frontage" value={fmt(lot?.frontage_ft, ' ft')} />
      <MetricRow label="Depth" value={fmt(lot?.depth_ft, ' ft')} />

      {/* Selected floor detail */}
      {(selectedFloor || hoveredFloor) && (
        <>
          <h3>Floor Detail</h3>
          <FloorCard floor={selectedFloor || hoveredFloor} />
        </>
      )}

      {/* Comparison mode controls */}
      {comparisonMode && (
        <div className="comparison-select">
          <label>Compare with:</label>
          <select
            value={comparisonScenario}
            onChange={(e) => setComparisonScenario(Number(e.target.value))}
          >
            {scenarios.map((s, i) => (
              i !== activeScenario && (
                <option key={i} value={i}>{s.name}</option>
              )
            ))}
          </select>
        </div>
      )}

      {/* Color legend */}
      <h3>Legend</h3>
      <div className="legend">
        <LegendItem color="#4A90D9" label="Commercial" />
        <LegendItem color="#F5E6CC" label="Residential" />
        <LegendItem color="#6BBF6B" label="Comm. Fac." />
        <LegendItem color="#999" label="Parking" />
        <LegendItem color="#888" label="Bulkhead" />
      </div>

      {/* Warnings */}
      {warnings && warnings.length > 0 && (
        <div className="warnings">
          <h3 style={{ margin: '0 0 4px', color: '#856404' }}>Warnings</h3>
          {warnings.map((w, i) => (
            <p key={i}>{w}</p>
          ))}
        </div>
      )}

      {/* Download / export buttons */}
      <div style={{ marginTop: 16, display: 'flex', gap: 8, flexDirection: 'column' }}>
        <button
          className="panel-btn"
          onClick={() => {
            const canvas = document.querySelector('canvas');
            if (!canvas) return;
            const link = document.createElement('a');
            link.download = `massing-screenshot-${Date.now()}.png`;
            link.href = canvas.toDataURL('image/png');
            link.click();
          }}
        >
          Download Screenshot (PNG)
        </button>
      </div>
    </div>
  );
}


function MetricRow({ label, value }) {
  return (
    <div className="metric-row">
      <span className="label">{label}</span>
      <span className="value">{value ?? 'N/A'}</span>
    </div>
  );
}


function FloorCard({ floor }) {
  if (!floor) return null;
  const useClass = (floor.use || '').replace(/ /g, '_').toLowerCase();

  return (
    <div className="floor-card">
      <div className="floor-header">
        <strong>Floor {floor.floor_num}</strong>
        <span className={`use-badge ${useClass}`}>{floor.use || 'Unknown'}</span>
      </div>
      <MetricRow label="Elevation" value={`${floor.elevation_ft} ft`} />
      <MetricRow label="Floor Height" value={`${floor.height_ft} ft`} />
      <MetricRow label="Gross Area" value={fmt(floor.gross_area_sf, ' SF')} />
      <MetricRow label="Net Area" value={fmt(floor.net_area_sf, ' SF')} />
      {floor.setback_from_street_ft > 0 && (
        <MetricRow label="Street Setback" value={`${floor.setback_from_street_ft} ft`} />
      )}
    </div>
  );
}


function LegendItem({ color, label }) {
  return (
    <div className="legend-item">
      <div className="legend-swatch" style={{ background: color }} />
      {label}
    </div>
  );
}


function fmt(val, suffix = '') {
  if (val == null || val === undefined) return 'N/A';
  if (typeof val === 'number') {
    return val.toLocaleString() + suffix;
  }
  return String(val) + suffix;
}
