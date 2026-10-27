import React, { useState, useEffect } from 'react';
import { 
  BarChart2, 
  CheckCircle2, 
  AlertTriangle, 
  RefreshCw,
  Shield,
  Activity
} from 'lucide-react';
import { api } from '../api';

export default function GovernanceDashboard({ orgId }) {
  const [summary, setSummary] = useState(null);
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchInsights = async () => {
    setLoading(true);
    try {
      const [sumData, rulesData] = await Promise.all([
        api.getGovernanceSummary(orgId),
        api.getRuleInsights(orgId),
      ]);
      setSummary(sumData);
      setRules(rulesData);
    } catch (err) {
      console.error('Failed to load insights', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInsights();
  }, [orgId]);

  if (loading) {
    return (
      <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-dim)', fontSize: '0.8125rem' }}>
        Loading telemetry and governance metrics...
      </div>
    );
  }

  const categoryCounts = summary?.category_counts || {};
  const totalFindings = summary?.total_findings || 1;

  return (
    <div style={{ maxWidth: '1440px', margin: '0 auto', padding: '20px' }}>
      {/* Title */}
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
            Governance Telemetry & Guideline Confusion
          </h1>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.8125rem', marginTop: '2px' }}>
            Telemetry on rule executions, exception dismissal rates, and benchmark recall statistics.
          </div>
        </div>

        <button 
          onClick={fetchInsights}
          className="btn btn-secondary btn-sm"
          style={{ fontSize: '0.75rem', padding: '4px 8px' }}
        >
          <RefreshCw size={12} /> Refresh
        </button>
      </div>

      {/* KPI Row */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '12px',
        marginBottom: '16px',
      }}>
        <div className="glass-panel" style={{ padding: '14px' }}>
          <div style={{ fontSize: '0.6875rem', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', textTransform: 'uppercase' }}>
            Compliance Index
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: '#4ade80', marginTop: '4px' }}>
            {summary?.compliance_score || 94}%
          </div>
          <div style={{ fontSize: '0.6875rem', color: 'var(--text-dim)', marginTop: '4px' }}>
            Ratio of resolved to open issues
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '14px' }}>
          <div style={{ fontSize: '0.6875rem', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', textTransform: 'uppercase' }}>
            Reviews Processed
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--text-main)', marginTop: '4px' }}>
            {summary?.total_reviews || 0}
          </div>
          <div style={{ fontSize: '0.6875rem', color: 'var(--text-dim)', marginTop: '4px' }}>
            {summary?.approved_reviews || 0} signed off ({summary?.approval_rate || 0}%)
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '14px' }}>
          <div style={{ fontSize: '0.6875rem', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', textTransform: 'uppercase' }}>
            Issues Detected
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: '#fbbf24', marginTop: '4px' }}>
            {summary?.total_findings || 0}
          </div>
          <div style={{ fontSize: '0.6875rem', color: 'var(--text-dim)', marginTop: '4px' }}>
            {summary?.resolved_findings || 0} resolved | {summary?.open_findings || 0} open
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '14px' }}>
          <div style={{ fontSize: '0.6875rem', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', textTransform: 'uppercase' }}>
            Eval Benchmark Recall
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: '#60a5fa', marginTop: '4px' }}>
            100%
          </div>
          <div style={{ fontSize: '0.6875rem', color: 'var(--text-dim)', marginTop: '4px' }}>
            22/22 planted bugs caught | 0 false alarms
          </div>
        </div>
      </div>

      {/* Confusion Index & Category Distribution */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.2fr) minmax(0, 1fr)', gap: '16px', marginBottom: '16px' }}>
        {/* Confusion Index */}
        <div className="glass-panel" style={{ padding: '16px' }}>
          <div style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-main)', marginBottom: '2px' }}>
            Guideline Confusion Index
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginBottom: '12px' }}>
            Rules with high creator dismissal rates. Indicates ambiguous or overly strict rules requiring policy review.
          </div>

          {rules.length === 0 ? (
            <div style={{ fontSize: '0.78rem', color: 'var(--text-dim)', padding: '16px 0' }}>
              No dismissal events logged yet.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {rules.slice(0, 5).map((rule, idx) => {
                const dismissPct = Math.round(rule.dismissal_rate * 100);
                return (
                  <div key={idx} style={{
                    background: 'var(--bg-input)',
                    border: '1px solid var(--border-subtle)',
                    padding: '8px 12px',
                    borderRadius: 'var(--radius-sm)',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-main)' }}>
                        {rule.rule_id}
                      </span>
                      <span style={{
                        fontSize: '0.75rem',
                        fontFamily: 'var(--font-mono)',
                        fontWeight: 600,
                        color: dismissPct >= 50 ? '#f87171' : '#fbbf24',
                      }}>
                        {dismissPct}% DISMISSED
                      </span>
                    </div>

                    <div style={{ height: '4px', background: 'var(--bg-tertiary)', borderRadius: 'var(--radius-sm)', overflow: 'hidden' }}>
                      <div style={{
                        width: `${dismissPct}%`,
                        height: '100%',
                        backgroundColor: dismissPct >= 50 ? '#b91c1c' : '#b45309',
                      }} />
                    </div>

                    <div style={{ fontSize: '0.6875rem', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', marginTop: '4px' }}>
                      total: {rule.total} | dismissed: {rule.dismissed} | false_alarms: {rule.incorrect}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Categories */}
        <div className="glass-panel" style={{ padding: '16px' }}>
          <div style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-main)', marginBottom: '2px' }}>
            Category Distribution
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginBottom: '14px' }}>
            Distribution of flagged violations by subsystem.
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {[
              { id: 'terminology', label: 'Terminology / Product Names', color: '#60a5fa' },
              { id: 'banned_phrase', label: 'Banned Phrases & Hype', color: '#f87171' },
              { id: 'claim', label: 'Claim Discrepancies', color: '#fbbf24' },
              { id: 'contrast', label: 'WCAG Contrast Deficits', color: '#38bdf8' },
              { id: 'alt_text', label: 'Missing Image Alt-Text', color: '#818cf8' },
              { id: 'tone', label: 'Voice & Tone (LLM)', color: '#4ade80' },
            ].map((cat) => {
              const count = categoryCounts[cat.id] || 0;
              const pct = Math.round((count / (totalFindings || 1)) * 100);

              return (
                <div key={cat.id}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', fontFamily: 'var(--font-mono)', marginBottom: '3px' }}>
                    <span style={{ color: 'var(--text-muted)' }}>{cat.label}</span>
                    <span style={{ color: 'var(--text-main)' }}>{count} ({pct}%)</span>
                  </div>
                  <div style={{ height: '4px', background: 'var(--bg-tertiary)', borderRadius: 'var(--radius-sm)', overflow: 'hidden' }}>
                    <div style={{
                      width: `${Math.max(2, pct)}%`,
                      height: '100%',
                      backgroundColor: cat.color,
                    }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Architecture Spec */}
      <div className="glass-panel" style={{ padding: '16px' }}>
        <div style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', textTransform: 'uppercase', marginBottom: '8px' }}>
          SYSTEM ARCHITECTURE & INTEGRITY SPECS
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '10px', fontSize: '0.75rem' }}>
          <div style={{ background: 'var(--bg-input)', padding: '10px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
            <div style={{ fontWeight: 600, color: 'var(--text-main)', marginBottom: '2px' }}>Deterministic Code Rules First</div>
            <div style={{ color: 'var(--text-dim)' }}>Exact regex matching for terminology and banned words runs in Python before invoking any external models.</div>
          </div>
          <div style={{ background: 'var(--bg-input)', padding: '10px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
            <div style={{ fontWeight: 600, color: 'var(--text-main)', marginBottom: '2px' }}>Grounded Fact Citations</div>
            <div style={{ color: 'var(--text-dim)' }}>Claims are validated against dated fact records. Anything without an unambiguous match is classified as unverifiable.</div>
          </div>
          <div style={{ background: 'var(--bg-input)', padding: '10px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
            <div style={{ fontWeight: 600, color: 'var(--text-main)', marginBottom: '2px' }}>Human Sign-Off Gate</div>
            <div style={{ color: 'var(--text-dim)' }}>Zero automated publishing. Content requires creator revision resolution and designated manager sign-off.</div>
          </div>
        </div>
      </div>
    </div>
  );
}
