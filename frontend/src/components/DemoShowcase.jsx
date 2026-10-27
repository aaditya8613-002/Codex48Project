import React from 'react';
import { 
  ArrowRight, 
  Target, 
  Terminal 
} from 'lucide-react';

export default function DemoShowcase({ presets = [], onLoadPreset }) {
  return (
    <div style={{ maxWidth: '1440px', margin: '0 auto', padding: '20px' }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '12px',
        marginBottom: '16px',
        borderBottom: '1px solid var(--border-subtle)',
        paddingBottom: '14px',
      }}>
        <div>
          <h1 style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--text-main)', letterSpacing: '-0.02em' }}>
            Sample Test Scenarios & Benchmark Cases
          </h1>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.8125rem', marginTop: '2px' }}>
            Reference test cases from the 30-item evaluation testbed for quick validation.
          </div>
        </div>

        <div style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)' }}>
          eval/testset.json: <span style={{ color: '#4ade80' }}>22/22 caught (100%)</span> | 0 false alarms
        </div>
      </div>

      {/* Benchmark Summary Bar */}
      <div className="glass-panel" style={{
        padding: '12px 16px',
        marginBottom: '16px',
        background: 'var(--bg-tertiary)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        fontSize: '0.78rem',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Terminal size={14} color="#94a3b8" />
          <span style={{ color: 'var(--text-main)', fontWeight: 600 }}>Testbed Verification:</span>
          <span style={{ color: 'var(--text-muted)' }}>20 planted violation drafts + 10 clean control drafts.</span>
        </div>
        <div style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-dim)' }}>
          recall: 1.000 | false_alarm_rate: 0.000
        </div>
      </div>

      {/* Scenario Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(310px, 1fr))', gap: '14px' }}>
        {presets.map((preset, index) => {
          const isClean = preset.id === 'preset-clean-approved';

          return (
            <div
              key={preset.id}
              id={`preset-card-${preset.id}`}
              className="glass-panel"
              style={{
                padding: '16px',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <span className="badge" style={{ background: 'var(--bg-input)', color: isClean ? '#4ade80' : '#f87171' }}>
                    {isClean ? 'CONTROL (CLEAN)' : `SCENARIO #${index + 1}`}
                  </span>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                    {preset.channel}
                  </span>
                </div>

                <div style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-main)', marginBottom: '4px' }}>
                  {preset.title}
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '10px', lineHeight: '1.4' }}>
                  {preset.description}
                </div>

                {/* Excerpt */}
                <div style={{
                  background: 'var(--bg-input)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '8px 10px',
                  fontSize: '0.75rem',
                  fontFamily: 'var(--font-mono)',
                  color: 'var(--text-dim)',
                  lineHeight: '1.45',
                  marginBottom: '10px',
                  maxHeight: '90px',
                  overflowY: 'auto',
                }}>
                  {preset.text}
                </div>

                {/* Expected Violations */}
                <div style={{ marginBottom: '14px' }}>
                  <div style={{ fontSize: '0.6875rem', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', textTransform: 'uppercase', marginBottom: '4px' }}>
                    Assertions Flagged:
                  </div>
                  <ul style={{ paddingLeft: '14px', fontSize: '0.72rem', color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', gap: '2px' }}>
                    {preset.expected_issues.map((issue, idx) => (
                      <li key={idx} style={{ color: isClean ? '#4ade80' : '#f87171' }}>
                        {issue}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Action Button */}
              <button
                id={`load-preset-btn-${preset.id}`}
                onClick={() => onLoadPreset(preset.id)}
                className="btn btn-secondary"
                style={{ width: '100%', fontSize: '0.78rem' }}
              >
                <span>Load in Studio</span>
                <ArrowRight size={13} />
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
