import type { DevelopmentScenario } from '../types';

interface ScenarioPanelProps {
  scenarios: DevelopmentScenario[];
  activeScenario: number;
  onSelectScenario: (index: number) => void;
}

export default function ScenarioPanel({ scenarios, activeScenario, onSelectScenario }: ScenarioPanelProps) {
  const scenario = scenarios[activeScenario];

  return (
    <div style={{ padding: 16 }}>
      {/* Scenario tabs */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 16 }}>
        {scenarios.map((s, i) => (
          <button
            key={i}
            onClick={() => onSelectScenario(i)}
            style={{
              padding: '6px 12px', fontSize: 12, fontWeight: 600,
              backgroundColor: i === activeScenario ? '#4A90D9' : '#f0f0f0',
              color: i === activeScenario ? '#fff' : '#333',
              border: 'none', borderRadius: 6, cursor: 'pointer',
              transition: 'all 0.2s',
            }}
          >
            {s.name}
          </button>
        ))}
      </div>

      {scenario && (
        <>
          <div style={{ fontSize: 12, color: '#666', marginBottom: 16, lineHeight: 1.4 }}>
            {scenario.description}
          </div>

          {/* Key Metrics */}
          <div style={{
            display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 16,
          }}>
            <MetricCard label="Gross SF" value={Math.round(scenario.total_gross_sf).toLocaleString()} />
            <MetricCard label="Net SF" value={Math.round(scenario.total_net_sf).toLocaleString()} />
            <MetricCard label="Floors" value={String(scenario.num_floors)} />
            <MetricCard label="Height" value={`${Math.round(scenario.max_height_ft)} ft`} />
            <MetricCard label="FAR Used" value={scenario.far_used.toFixed(2)} />
            {scenario.total_units > 0 && (
              <MetricCard label="Units" value={String(scenario.total_units)} />
            )}
          </div>

          {/* Floor-by-floor breakdown */}
          {scenario.floors.length > 0 && (
            <Section title="Floor Breakdown">
              <div style={{
                maxHeight: 200, overflowY: 'auto', fontSize: 12,
                border: '1px solid #eee', borderRadius: 6,
              }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid #ddd', position: 'sticky', top: 0, background: '#fff' }}>
                      <th style={{ padding: '6px 8px', textAlign: 'left' }}>Floor</th>
                      <th style={{ padding: '6px 8px', textAlign: 'left' }}>Use</th>
                      <th style={{ padding: '6px 8px', textAlign: 'right' }}>Gross SF</th>
                      <th style={{ padding: '6px 8px', textAlign: 'right' }}>Net SF</th>
                    </tr>
                  </thead>
                  <tbody>
                    {scenario.floors.map((f, i) => (
                      <tr key={i} style={{ borderBottom: '1px solid #f5f5f5' }}>
                        <td style={{ padding: '4px 8px' }}>{f.floor}</td>
                        <td style={{ padding: '4px 8px' }}>
                          <UseTag use={f.use} />
                        </td>
                        <td style={{ padding: '4px 8px', textAlign: 'right' }}>
                          {Math.round(f.gross_sf).toLocaleString()}
                        </td>
                        <td style={{ padding: '4px 8px', textAlign: 'right' }}>
                          {Math.round(f.net_sf).toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Section>
          )}

          {/* Unit Mix */}
          {scenario.unit_mix && scenario.unit_mix.total_units > 0 && (
            <Section title="Unit Mix">
              {scenario.unit_mix.units.map((u, i) => (
                <div key={i} style={{
                  display: 'flex', justifyContent: 'space-between',
                  padding: '4px 0', fontSize: 13,
                }}>
                  <span style={{ textTransform: 'capitalize' }}>
                    {u.type.replace('br', ' BR')}
                  </span>
                  <span style={{ fontWeight: 600 }}>
                    {u.count} units ({u.avg_sf} SF avg)
                  </span>
                </div>
              ))}
              <div style={{
                display: 'flex', justifyContent: 'space-between',
                padding: '6px 0', fontSize: 13, fontWeight: 700,
                borderTop: '1px solid #ddd', marginTop: 4,
              }}>
                <span>Total</span>
                <span>{scenario.unit_mix.total_units} units</span>
              </div>
            </Section>
          )}

          {/* Loss Factor */}
          {scenario.loss_factor && (
            <Section title="Efficiency">
              <Row label="Gross Area" value={`${Math.round(scenario.loss_factor.gross_building_area).toLocaleString()} SF`} />
              <Row label="Common Area" value={`${Math.round(scenario.loss_factor.total_common_area).toLocaleString()} SF`} />
              <Row label="Net Rentable" value={`${Math.round(scenario.loss_factor.net_rentable_area).toLocaleString()} SF`} />
              <Row
                label="Efficiency"
                value={`${(scenario.loss_factor.efficiency_ratio * 100).toFixed(1)}%`}
                highlight={scenario.loss_factor.efficiency_ratio > 0.80}
              />
            </Section>
          )}

          {/* Parking */}
          {scenario.parking && scenario.parking.total_spaces_required > 0 && (
            <Section title="Parking Requirements">
              <Row label="Residential Spaces" value={String(scenario.parking.residential_spaces_required)} />
              {scenario.parking.commercial_spaces_required > 0 && (
                <Row label="Commercial Spaces" value={String(scenario.parking.commercial_spaces_required)} />
              )}
              <Row label="Total Required" value={String(scenario.parking.total_spaces_required)} />
              {scenario.parking.waiver_eligible && (
                <div style={{
                  padding: '6px 10px', backgroundColor: '#2ECC71', color: '#fff',
                  borderRadius: 4, fontSize: 12, marginTop: 6,
                }}>
                  Eligible for small-lot parking waiver
                </div>
              )}
              {scenario.parking.parking_options.length > 0 && (
                <div style={{ marginTop: 8, fontSize: 12 }}>
                  <div style={{ fontWeight: 600, marginBottom: 4, color: '#666' }}>Parking Options:</div>
                  {scenario.parking.parking_options.map((opt, i) => (
                    <div key={i} style={{
                      padding: '6px 8px', backgroundColor: '#f9f9f9',
                      borderRadius: 4, marginBottom: 4,
                    }}>
                      <div style={{ fontWeight: 600, textTransform: 'capitalize' }}>
                        {opt.type.replace(/_/g, ' ')}
                      </div>
                      <div style={{ color: '#666' }}>
                        {opt.total_sf.toLocaleString()} SF
                        {opt.estimated_cost && ` | Est. $${(opt.estimated_cost / 1000).toFixed(0)}K`}
                        {opt.floors_consumed && ` | ${opt.floors_consumed} floors`}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Section>
          )}

          {/* Core */}
          {scenario.core && (
            <Section title="Building Core">
              <Row label="Elevators" value={String(scenario.core.elevators)} />
              <Row label="Stairs" value={String(scenario.core.stairs)} />
              <Row label="Core/Floor" value={`${Math.round(scenario.core.total_core_sf_per_floor).toLocaleString()} SF`} />
              <Row label="Core %" value={`${scenario.core.core_percentage}%`} />
            </Section>
          )}
        </>
      )}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{
        fontSize: 13, fontWeight: 700, color: '#333',
        borderBottom: '2px solid #4A90D9', paddingBottom: 3, marginBottom: 8,
      }}>
        {title}
      </div>
      {children}
    </div>
  );
}

function Row({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div style={{
      display: 'flex', justifyContent: 'space-between',
      padding: '3px 0', fontSize: 13,
    }}>
      <span style={{ color: '#666' }}>{label}</span>
      <span style={{
        fontWeight: 600,
        color: highlight ? '#2ECC71' : '#333',
      }}>{value}</span>
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div style={{
      padding: '10px 12px', backgroundColor: '#f8f9fa',
      borderRadius: 8, textAlign: 'center',
    }}>
      <div style={{ fontSize: 18, fontWeight: 700, color: '#333' }}>{value}</div>
      <div style={{ fontSize: 11, color: '#888', marginTop: 2 }}>{label}</div>
    </div>
  );
}

function UseTag({ use }: { use: string }) {
  const colors: Record<string, string> = {
    residential: '#4A90D9',
    commercial: '#D94A4A',
    community_facility: '#4AD97A',
    parking: '#888',
  };
  return (
    <span style={{
      padding: '2px 6px', borderRadius: 3, fontSize: 11,
      backgroundColor: colors[use] || '#ccc', color: '#fff',
      textTransform: 'capitalize',
    }}>
      {use.replace(/_/g, ' ')}
    </span>
  );
}
