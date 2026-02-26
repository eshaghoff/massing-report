import type { ZoningEnvelope, LotProfile } from '../types';

interface ZoningPanelProps {
  lot: LotProfile;
  envelope: ZoningEnvelope;
}

export default function ZoningPanel({ lot, envelope }: ZoningPanelProps) {
  return (
    <div style={{ padding: 16 }}>
      {/* Site Info */}
      <Section title="Site Information">
        <Row label="Address" value={lot.address || '—'} />
        <Row label="BBL" value={lot.bbl} />
        <Row label="Lot Area" value={`${lot.lot_area?.toLocaleString() || '—'} SF`} />
        <Row label="Lot Frontage" value={`${lot.lot_frontage || '—'} ft`} />
        <Row label="Lot Depth" value={`${lot.lot_depth || '—'} ft`} />
        <Row label="Lot Type" value={lot.lot_type} />
        <Row label="Street Width" value={lot.street_width} />
        {lot.pluto?.yearbuilt && <Row label="Year Built" value={String(lot.pluto.yearbuilt)} />}
        {lot.pluto?.builtfar && <Row label="Existing FAR" value={lot.pluto.builtfar.toFixed(2)} />}
      </Section>

      {/* Zoning */}
      <Section title="Zoning Districts">
        {lot.zoning_districts.map((d, i) => (
          <div key={i} style={{
            display: 'inline-block', padding: '4px 10px', margin: '2px 4px 2px 0',
            backgroundColor: '#4A90D9', color: '#fff', borderRadius: 4, fontSize: 13, fontWeight: 600,
          }}>
            {d}
          </div>
        ))}
        {lot.overlays.length > 0 && (
          <div style={{ marginTop: 8 }}>
            <span style={{ fontSize: 12, color: '#666', fontWeight: 600 }}>Overlays: </span>
            {lot.overlays.map((o, i) => (
              <span key={i} style={{
                padding: '3px 8px', margin: '2px 4px 2px 0',
                backgroundColor: '#D9A84A', color: '#fff', borderRadius: 4, fontSize: 12,
                display: 'inline-block',
              }}>
                {o}
              </span>
            ))}
          </div>
        )}
        {lot.special_districts.length > 0 && (
          <div style={{ marginTop: 8 }}>
            <span style={{ fontSize: 12, color: '#666', fontWeight: 600 }}>Special Districts: </span>
            {lot.special_districts.map((s, i) => (
              <span key={i} style={{
                padding: '3px 8px', margin: '2px 4px 2px 0',
                backgroundColor: '#8E44AD', color: '#fff', borderRadius: 4, fontSize: 12,
                display: 'inline-block',
              }}>
                {s}
              </span>
            ))}
          </div>
        )}
        {lot.split_zone && (
          <div style={{ marginTop: 6, color: '#D94A4A', fontSize: 12, fontWeight: 600 }}>
            Split-zoned lot
          </div>
        )}
      </Section>

      {/* FAR */}
      <Section title="Floor Area Ratio (FAR)">
        <FARTable envelope={envelope} />
      </Section>

      {/* Height & Setback */}
      <Section title="Height & Setback">
        {envelope.quality_housing && (
          <div style={{
            padding: '4px 10px', backgroundColor: '#2ECC71', color: '#fff',
            borderRadius: 4, fontSize: 12, fontWeight: 600, display: 'inline-block', marginBottom: 8,
          }}>
            Quality Housing Program
          </div>
        )}
        {envelope.height_factor && (
          <div style={{
            padding: '4px 10px', backgroundColor: '#E67E22', color: '#fff',
            borderRadius: 4, fontSize: 12, fontWeight: 600, display: 'inline-block', marginBottom: 8,
          }}>
            Height Factor
          </div>
        )}
        {envelope.base_height_min != null && (
          <Row label="Base Height (min)" value={`${envelope.base_height_min} ft`} />
        )}
        {envelope.base_height_max != null && (
          <Row label="Base Height (max)" value={`${envelope.base_height_max} ft`} />
        )}
        {envelope.max_building_height != null && (
          <Row label="Max Building Height" value={`${envelope.max_building_height} ft`} />
        )}
        {!envelope.max_building_height && envelope.height_factor && (
          <Row label="Max Building Height" value="No cap (Sky Exposure Plane applies)" />
        )}
        {envelope.sky_exposure_plane && (
          <>
            <Row label="SEP Start Height" value={`${envelope.sky_exposure_plane.start_height} ft`} />
            <Row label="SEP Slope" value={`${envelope.sky_exposure_plane.ratio}:1`} />
          </>
        )}
      </Section>

      {/* Yards */}
      <Section title="Yard Requirements">
        <Row label="Front Yard" value={`${envelope.front_yard} ft`} />
        <Row label="Rear Yard" value={`${envelope.rear_yard} ft`} />
        <Row label="Side Yards" value={envelope.side_yards_required ? `${envelope.side_yard_width} ft each` : 'Not required'} />
        {envelope.lot_coverage_max != null && (
          <Row label="Max Lot Coverage" value={`${envelope.lot_coverage_max}%`} />
        )}
      </Section>

      {/* IH Bonus */}
      {envelope.ih_bonus_far != null && envelope.ih_bonus_far > 0 && (
        <Section title="Inclusionary Housing Bonus">
          <Row label="Bonus FAR" value={`+${envelope.ih_bonus_far.toFixed(2)}`} />
          <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>
            Available through Mandatory Inclusionary Housing program.
            Requires 25-30% affordable units.
          </div>
        </Section>
      )}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 20 }}>
      <div style={{
        fontSize: 14, fontWeight: 700, color: '#333',
        borderBottom: '2px solid #4A90D9', paddingBottom: 4, marginBottom: 10,
      }}>
        {title}
      </div>
      {children}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div style={{
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      padding: '4px 0', fontSize: 13,
    }}>
      <span style={{ color: '#666' }}>{label}</span>
      <span style={{ fontWeight: 600, color: '#333' }}>{value}</span>
    </div>
  );
}

function FARTable({ envelope }: { envelope: ZoningEnvelope }) {
  const rows = [
    { label: 'Residential', far: envelope.residential_far, zfa: envelope.max_residential_zfa },
    { label: 'Commercial', far: envelope.commercial_far, zfa: envelope.max_commercial_zfa },
    { label: 'Community Facility', far: envelope.cf_far, zfa: envelope.max_cf_zfa },
  ].filter(r => r.far != null && r.far > 0);

  if (rows.length === 0) {
    return <div style={{ fontSize: 13, color: '#999' }}>No FAR data available.</div>;
  }

  return (
    <table style={{ width: '100%', fontSize: 13, borderCollapse: 'collapse' }}>
      <thead>
        <tr style={{ borderBottom: '1px solid #ddd' }}>
          <th style={{ textAlign: 'left', padding: '4px 0', color: '#666', fontWeight: 600 }}>Use</th>
          <th style={{ textAlign: 'right', padding: '4px 0', color: '#666', fontWeight: 600 }}>FAR</th>
          <th style={{ textAlign: 'right', padding: '4px 0', color: '#666', fontWeight: 600 }}>Max ZFA</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i} style={{ borderBottom: '1px solid #f0f0f0' }}>
            <td style={{ padding: '4px 0' }}>{r.label}</td>
            <td style={{ padding: '4px 0', textAlign: 'right', fontWeight: 600 }}>{r.far?.toFixed(2)}</td>
            <td style={{ padding: '4px 0', textAlign: 'right', fontWeight: 600 }}>
              {r.zfa ? `${Math.round(r.zfa).toLocaleString()} SF` : '—'}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
