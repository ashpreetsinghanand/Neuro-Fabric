import { useState, useEffect, useRef } from 'react';

const API = '';

/* ─── Tab Definitions ─────────────────────────────────────────────────────── */
const TABS = [
  { id: 'dashboard', label: 'Dashboard', icon: '◈' },
  { id: 'schema', label: 'Schema', icon: '⬡' },
  { id: 'query', label: 'SQL Query', icon: '⌘' },
  { id: 'quality', label: 'Quality', icon: '◉' },
  { id: 'chat', label: 'Chat', icon: '◬' },
  { id: 'artifacts', label: 'Artifacts', icon: '◇' },
];

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [connected, setConnected] = useState(false);
  const [engine, setEngine] = useState('');
  const [loading, setLoading] = useState(false);
  const [schema, setSchema] = useState({});
  const [quality, setQuality] = useState({});
  const [analytics, setAnalytics] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => { autoConnect(); }, []);

  async function autoConnect() {
    try {
      const r = await fetch(`${API}/api/connect`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) });
      const d = await r.json();
      setConnected(d.connected);
      setEngine(d.engine || '');
      if (d.connected) {
        loadAnalytics();
        loadSchema();
      }
    } catch (e) { console.error('Auto-connect failed:', e); }
  }

  async function loadSchema() {
    try {
      const r = await fetch(`${API}/api/schema`);
      const d = await r.json();
      setSchema(d);
    } catch (e) { console.error(e); }
  }

  async function loadQuality() {
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/quality`);
      const d = await r.json();
      setQuality(d);
    } catch (e) { console.error(e); }
    setLoading(false);
  }

  async function loadAnalytics() {
    try {
      const r = await fetch(`${API}/api/analytics/overview`);
      const d = await r.json();
      setAnalytics(d);
    } catch (e) { console.error(e); }
  }

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-primary)', color: 'var(--text-primary)', fontFamily: "'Inter', sans-serif" }}>
      {/* ── Header ── */}
      <header style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '16px 32px',
        background: 'linear-gradient(135deg, rgba(14,14,18,0.95), rgba(22,22,30,0.95))',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
        backdropFilter: 'blur(20px)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontSize: 28, filter: 'drop-shadow(0 0 8px rgba(138,92,246,0.5))' }}>🧠</span>
          <div>
            <h1 style={{ margin: 0, fontSize: 20, fontWeight: 700, background: 'linear-gradient(135deg, #a78bfa, #818cf8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              Neuro-Fabric
            </h1>
            <p style={{ margin: 0, fontSize: 11, color: 'var(--text-muted)', letterSpacing: 1 }}>DATA DICTIONARY · LOCAL-FIRST</p>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{
            display: 'inline-flex', alignItems: 'center', gap: 6,
            padding: '6px 14px', borderRadius: 20, fontSize: 12, fontWeight: 600,
            background: connected ? 'rgba(52,211,153,0.12)' : 'rgba(239,68,68,0.12)',
            color: connected ? '#34d399' : '#ef4444',
            border: `1px solid ${connected ? 'rgba(52,211,153,0.2)' : 'rgba(239,68,68,0.2)'}`,
          }}>
            <span style={{ width: 7, height: 7, borderRadius: '50%', background: connected ? '#34d399' : '#ef4444', boxShadow: connected ? '0 0 6px #34d399' : '0 0 6px #ef4444' }} />
            {connected ? `${engine.toUpperCase()} Connected` : 'Disconnected'}
          </span>
        </div>
      </header>

      {/* ── Tab Bar ── */}
      <nav style={{
        display: 'flex', gap: 2, padding: '0 32px',
        background: 'rgba(14,14,18,0.7)', borderBottom: '1px solid rgba(255,255,255,0.04)',
      }}>
        {TABS.map(tab => (
          <button key={tab.id} onClick={() => {
            setActiveTab(tab.id);
            if (tab.id === 'quality' && !Object.keys(quality).length) loadQuality();
            if (tab.id === 'schema' && !Object.keys(schema).length) loadSchema();
          }} style={{
            padding: '14px 20px', border: 'none', background: 'transparent', cursor: 'pointer',
            color: activeTab === tab.id ? '#a78bfa' : 'var(--text-muted)',
            fontSize: 13, fontWeight: activeTab === tab.id ? 600 : 400,
            borderBottom: activeTab === tab.id ? '2px solid #a78bfa' : '2px solid transparent',
            display: 'flex', alignItems: 'center', gap: 6, transition: 'all 0.2s',
            fontFamily: "'Inter', sans-serif",
          }}>
            <span style={{ fontSize: 15 }}>{tab.icon}</span> {tab.label}
          </button>
        ))}
      </nav>

      {/* ── Main Content ── */}
      <main style={{ padding: '24px 32px', maxWidth: 1400, margin: '0 auto' }}>
        {error && <div style={{ padding: '12px 16px', background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: 8, marginBottom: 16, color: '#ef4444', fontSize: 13 }}>{error}</div>}

        {activeTab === 'dashboard' && <Dashboard connected={connected} engine={engine} analytics={analytics} schema={schema} onReconnect={autoConnect} />}
        {activeTab === 'schema' && <SchemaBrowser schema={schema} />}
        {activeTab === 'query' && <SQLQuery />}
        {activeTab === 'quality' && <QualityDashboard quality={quality} loading={loading} onRefresh={loadQuality} />}
        {activeTab === 'chat' && <ChatPanel />}
        {activeTab === 'artifacts' && <ArtifactsPanel />}
      </main>
    </div>
  );
}


/* ═══════════════════════════════════════════════════════════════════════════ */
/*  DASHBOARD                                                                 */
/* ═══════════════════════════════════════════════════════════════════════════ */

function Dashboard({ connected, engine, analytics, schema, onReconnect }) {
  const tableCount = Object.keys(schema).length;
  const totalRows = Object.values(schema).reduce((s, t) => s + (t.row_count || 0), 0);

  const cards = [
    { label: 'Tables', value: analytics?.total_orders ? tableCount : tableCount, icon: '⬡', color: '#818cf8' },
    { label: 'Total Rows', value: totalRows.toLocaleString(), icon: '◈', color: '#34d399' },
    { label: 'Orders', value: analytics?.total_orders?.toLocaleString() || '—', icon: '📦', color: '#f472b6' },
    { label: 'Revenue', value: analytics?.total_revenue ? `R$ ${(analytics.total_revenue / 1000).toFixed(0)}K` : '—', icon: '💰', color: '#fbbf24' },
    { label: 'Customers', value: analytics?.unique_customers?.toLocaleString() || '—', icon: '👥', color: '#60a5fa' },
    { label: 'Avg Review', value: analytics?.avg_review_score ? `${analytics.avg_review_score.toFixed(1)} ⭐` : '—', icon: '⭐', color: '#a78bfa' },
  ];

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ margin: 0, fontSize: 22, fontWeight: 700, color: 'var(--text-primary)' }}>Dashboard</h2>
        <p style={{ margin: '4px 0 0', fontSize: 13, color: 'var(--text-muted)' }}>
          {connected ? `Connected to ${engine.toUpperCase()} engine with real-time analytics` : 'Not connected — click reconnect'}
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, marginBottom: 24 }}>
        {cards.map(c => (
          <div key={c.label} className="glass-card" style={{
            padding: '20px', borderRadius: 12,
            background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)',
            transition: 'all 0.3s',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <span style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1 }}>{c.label}</span>
              <span style={{ fontSize: 18 }}>{c.icon}</span>
            </div>
            <div style={{ fontSize: 28, fontWeight: 700, color: c.color }}>{c.value}</div>
          </div>
        ))}
      </div>

      {analytics?.order_status && (
        <div className="glass-card" style={{ padding: 24, borderRadius: 12, background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}>
          <h3 style={{ margin: '0 0 16px', fontSize: 15, fontWeight: 600, color: 'var(--text-secondary)' }}>Order Status Distribution</h3>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            {Object.entries(analytics.order_status).map(([status, count]) => {
              const colors = { delivered: '#34d399', shipped: '#60a5fa', approved: '#fbbf24', canceled: '#ef4444', returned: '#f97316', created: '#a78bfa' };
              return (
                <div key={status} style={{
                  padding: '10px 16px', borderRadius: 8,
                  background: `${colors[status] || '#666'}15`,
                  border: `1px solid ${colors[status] || '#666'}30`,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', minWidth: 100,
                }}>
                  <span style={{ fontSize: 20, fontWeight: 700, color: colors[status] || '#666' }}>{count.toLocaleString()}</span>
                  <span style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'capitalize' }}>{status}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}


/* ═══════════════════════════════════════════════════════════════════════════ */
/*  SCHEMA BROWSER                                                            */
/* ═══════════════════════════════════════════════════════════════════════════ */

function SchemaBrowser({ schema }) {
  const [selected, setSelected] = useState(null);
  const [sampleData, setSampleData] = useState(null);
  const tables = Object.entries(schema);

  async function loadSample(tableName) {
    try {
      const r = await fetch(`${API}/api/sample/${encodeURIComponent(tableName)}?limit=5`);
      const d = await r.json();
      setSampleData(d);
    } catch (e) { console.error(e); }
  }

  if (!tables.length) return <div style={{ color: 'var(--text-muted)', padding: 40, textAlign: 'center' }}>Loading schema... Connect to database first.</div>;

  // Group by schema
  const grouped = {};
  tables.forEach(([name, info]) => {
    const s = info.schema || 'main';
    if (!grouped[s]) grouped[s] = [];
    grouped[s].push([name, info]);
  });

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: 20, minHeight: 500 }}>
      {/* Sidebar */}
      <div style={{ background: 'rgba(255,255,255,0.02)', borderRadius: 12, border: '1px solid rgba(255,255,255,0.06)', padding: 16, overflowY: 'auto', maxHeight: 'calc(100vh - 200px)' }}>
        <h3 style={{ margin: '0 0 12px', fontSize: 13, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1 }}>Tables ({tables.length})</h3>
        {Object.entries(grouped).map(([schemaName, schemaTables]) => (
          <div key={schemaName} style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 10, color: '#a78bfa', fontWeight: 700, letterSpacing: 1.5, textTransform: 'uppercase', marginBottom: 6 }}>📁 {schemaName}</div>
            {schemaTables.map(([name, info]) => (
              <button key={name} onClick={() => { setSelected(name); loadSample(name); }} style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%',
                padding: '8px 10px', marginBottom: 2, border: 'none', borderRadius: 6, cursor: 'pointer',
                background: selected === name ? 'rgba(138,92,246,0.15)' : 'transparent',
                color: selected === name ? '#a78bfa' : 'var(--text-secondary)',
                fontSize: 12, fontFamily: "'Fira Code', monospace", textAlign: 'left', transition: 'all 0.15s',
              }}>
                <span>{info.table_name}</span>
                <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{(info.row_count || 0).toLocaleString()}</span>
              </button>
            ))}
          </div>
        ))}
      </div>

      {/* Detail */}
      <div>
        {selected && schema[selected] ? (
          <div style={{ background: 'rgba(255,255,255,0.02)', borderRadius: 12, border: '1px solid rgba(255,255,255,0.06)', padding: 24 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <div>
                <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', fontFamily: "'Fira Code', monospace" }}>{selected}</h3>
                <p style={{ margin: '4px 0 0', fontSize: 12, color: 'var(--text-muted)' }}>{schema[selected].columns.length} columns · {(schema[selected].row_count || 0).toLocaleString()} rows</p>
              </div>
            </div>

            {/* Columns */}
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
                  <th style={{ padding: '8px 12px', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 600, fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>Column</th>
                  <th style={{ padding: '8px 12px', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 600, fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>Type</th>
                  <th style={{ padding: '8px 12px', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 600, fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>Nullable</th>
                  <th style={{ padding: '8px 12px', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 600, fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>Key</th>
                </tr>
              </thead>
              <tbody>
                {schema[selected].columns.map(col => (
                  <tr key={col.name} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                    <td style={{ padding: '8px 12px', fontFamily: "'Fira Code', monospace", color: col.is_primary_key ? '#fbbf24' : 'var(--text-primary)' }}>
                      {col.is_primary_key && '🔑 '}{col.name}
                    </td>
                    <td style={{ padding: '8px 12px', color: '#818cf8', fontFamily: "'Fira Code', monospace" }}>{col.type}</td>
                    <td style={{ padding: '8px 12px', color: col.nullable ? '#34d399' : '#ef4444' }}>{col.nullable ? 'YES' : 'NO'}</td>
                    <td style={{ padding: '8px 12px' }}>
                      {col.is_primary_key && <span style={{ background: 'rgba(251,191,36,0.15)', color: '#fbbf24', padding: '2px 8px', borderRadius: 4, fontSize: 10, fontWeight: 600 }}>PK</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Foreign Keys */}
            {schema[selected].foreign_keys?.length > 0 && (
              <div style={{ marginTop: 16, padding: 12, background: 'rgba(96,165,250,0.05)', borderRadius: 8, border: '1px solid rgba(96,165,250,0.15)' }}>
                <h4 style={{ margin: '0 0 8px', fontSize: 12, color: '#60a5fa', fontWeight: 600 }}>🔗 Foreign Keys</h4>
                {schema[selected].foreign_keys.map((fk, i) => (
                  <div key={i} style={{ fontSize: 11, color: 'var(--text-secondary)', fontFamily: "'Fira Code', monospace", marginBottom: 4 }}>
                    {fk.from_column} → {fk.to_table}.{fk.to_column}
                  </div>
                ))}
              </div>
            )}

            {/* Sample Data */}
            {sampleData?.rows?.length > 0 && (
              <div style={{ marginTop: 16 }}>
                <h4 style={{ margin: '0 0 8px', fontSize: 13, color: 'var(--text-secondary)', fontWeight: 600 }}>📋 Sample Data</h4>
                <div style={{ overflowX: 'auto', borderRadius: 8, border: '1px solid rgba(255,255,255,0.06)' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
                    <thead>
                      <tr style={{ background: 'rgba(255,255,255,0.03)' }}>
                        {sampleData.columns.map(c => (
                          <th key={c} style={{ padding: '6px 10px', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 600, fontSize: 10, whiteSpace: 'nowrap', fontFamily: "'Fira Code', monospace" }}>{c}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {sampleData.rows.map((row, i) => (
                        <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                          {sampleData.columns.map(c => (
                            <td key={c} style={{ padding: '6px 10px', color: 'var(--text-secondary)', fontFamily: "'Fira Code', monospace", maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                              {row[c] === null ? <span style={{ color: '#666', fontStyle: 'italic' }}>null</span> : String(row[c]).substring(0, 50)}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 400, color: 'var(--text-muted)', fontSize: 14 }}>
            ← Select a table to view its schema
          </div>
        )}
      </div>
    </div>
  );
}


/* ═══════════════════════════════════════════════════════════════════════════ */
/*  SQL QUERY                                                                 */
/* ═══════════════════════════════════════════════════════════════════════════ */

function SQLQuery() {
  const [query, setQuery] = useState('SELECT o.order_status, COUNT(*) AS cnt,\n  ROUND(AVG(oi.price)::NUMERIC, 2) AS avg_price\nFROM orders o\nJOIN order_items oi ON o.order_id = oi.order_id\nGROUP BY o.order_status\nORDER BY cnt DESC');
  const [result, setResult] = useState(null);
  const [running, setRunning] = useState(false);
  const [history, setHistory] = useState([]);

  async function runQuery() {
    setRunning(true);
    setResult(null);
    const start = Date.now();
    try {
      const r = await fetch(`${API}/api/query`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query.trim(), limit: 200 }),
      });
      const d = await r.json();
      d.duration_ms = Date.now() - start;
      setResult(d);
      setHistory(h => [{ query: query.trim(), time: new Date().toLocaleTimeString(), rows: d.row_count || 0 }, ...h.slice(0, 9)]);
    } catch (e) {
      setResult({ error: e.message });
    }
    setRunning(false);
  }

  const quickQueries = [
    { label: 'Top Products', sql: "SELECT p.product_name, pc.category_name_english, COUNT(*) AS orders\nFROM order_items oi\nJOIN products p ON p.product_id = oi.product_id\nJOIN product_categories pc ON pc.category_id = p.category_id\nGROUP BY p.product_name, pc.category_name_english\nORDER BY orders DESC LIMIT 10" },
    { label: 'Revenue by State', sql: "SELECT c.state, COUNT(DISTINCT o.order_id) AS orders,\n  ROUND(SUM(oi.price)::NUMERIC, 2) AS revenue\nFROM orders o\nJOIN customers c ON c.customer_id = o.customer_id\nJOIN order_items oi ON oi.order_id = o.order_id\nGROUP BY c.state ORDER BY revenue DESC LIMIT 10" },
    { label: 'Daily Revenue', sql: "SELECT date, total_orders, ROUND(total_revenue::NUMERIC, 2) AS revenue\nFROM analytics.daily_revenue\nORDER BY date DESC LIMIT 15" },
    { label: 'Seller Leaderboard', sql: "SELECT s.business_name, sp.total_orders,\n  ROUND(sp.total_revenue::NUMERIC, 2) AS revenue,\n  ROUND(sp.avg_review_score::NUMERIC, 1) AS rating\nFROM analytics.seller_performance sp\nJOIN sellers s ON s.seller_id = sp.seller_id\nORDER BY sp.total_revenue DESC LIMIT 10" },
    { label: 'Data Quality', sql: "SELECT table_name, check_type, check_result\nFROM staging.data_quality_log\nORDER BY checked_at DESC LIMIT 20" },
    { label: 'Math: Stats', sql: "SELECT\n  COUNT(*) AS total_items,\n  ROUND(AVG(price)::NUMERIC, 2) AS mean_price,\n  ROUND(STDDEV(price)::NUMERIC, 2) AS stddev_price,\n  ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price)::NUMERIC, 2) AS median,\n  MIN(price) AS min_price,\n  MAX(price) AS max_price\nFROM order_items" },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h2 style={{ margin: 0, fontSize: 22, fontWeight: 700 }}>SQL Query Engine</h2>
        <span style={{ fontSize: 12, color: 'var(--text-muted)', background: 'rgba(138,92,246,0.1)', padding: '4px 10px', borderRadius: 6 }}>⌘ DuckDB Powered</span>
      </div>

      {/* Quick Queries */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
        {quickQueries.map(qq => (
          <button key={qq.label} onClick={() => setQuery(qq.sql)} style={{
            padding: '6px 14px', borderRadius: 6, border: '1px solid rgba(255,255,255,0.08)',
            background: 'rgba(255,255,255,0.03)', color: 'var(--text-secondary)',
            fontSize: 11, cursor: 'pointer', transition: 'all 0.15s', fontFamily: "'Inter', sans-serif",
          }}>{qq.label}</button>
        ))}
      </div>

      {/* Editor */}
      <div style={{ background: 'rgba(255,255,255,0.02)', borderRadius: 12, border: '1px solid rgba(255,255,255,0.06)', overflow: 'hidden', marginBottom: 16 }}>
        <textarea value={query} onChange={e => setQuery(e.target.value)}
          onKeyDown={e => { if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') { e.preventDefault(); runQuery(); } }}
          style={{
            width: '100%', minHeight: 140, padding: 16, border: 'none', outline: 'none', resize: 'vertical',
            background: 'transparent', color: '#e2e8f0', fontSize: 13,
            fontFamily: "'Fira Code', monospace", lineHeight: 1.6,
          }}
          placeholder="Write SQL... Press Cmd+Enter to run"
        />
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 16px', borderTop: '1px solid rgba(255,255,255,0.04)' }}>
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>⌘+Enter to execute</span>
          <button onClick={runQuery} disabled={running} style={{
            padding: '8px 24px', borderRadius: 8, border: 'none', cursor: 'pointer',
            background: running ? 'rgba(138,92,246,0.3)' : 'linear-gradient(135deg, #7c3aed, #6366f1)',
            color: '#fff', fontSize: 13, fontWeight: 600, fontFamily: "'Inter', sans-serif",
            transition: 'all 0.2s',
          }}>{running ? '⏳ Running...' : '▶ Execute'}</button>
        </div>
      </div>

      {/* Results */}
      {result && (
        <div style={{ background: 'rgba(255,255,255,0.02)', borderRadius: 12, border: '1px solid rgba(255,255,255,0.06)' }}>
          {result.error ? (
            <div style={{ padding: 16, color: '#ef4444', fontSize: 13, fontFamily: "'Fira Code', monospace" }}>❌ {result.error}</div>
          ) : (
            <>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 16px', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                  {result.row_count} row{result.row_count !== 1 ? 's' : ''} returned
                  {result.truncated && ' (truncated)'}
                </span>
                <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>⏱ {result.duration_ms}ms · {result.engine}</span>
              </div>
              <div style={{ overflowX: 'auto', maxHeight: 400 }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                  <thead>
                    <tr style={{ background: 'rgba(255,255,255,0.03)', position: 'sticky', top: 0 }}>
                      {result.columns?.map(c => (
                        <th key={c} style={{ padding: '8px 12px', textAlign: 'left', color: '#a78bfa', fontWeight: 600, fontSize: 11, whiteSpace: 'nowrap', fontFamily: "'Fira Code', monospace" }}>{c}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.rows?.map((row, i) => (
                      <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                        {result.columns?.map(c => (
                          <td key={c} style={{ padding: '6px 12px', color: 'var(--text-secondary)', fontFamily: "'Fira Code', monospace", whiteSpace: 'nowrap' }}>
                            {row[c] === null ? <span style={{ color: '#555', fontStyle: 'italic' }}>null</span> : String(row[c])}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}


/* ═══════════════════════════════════════════════════════════════════════════ */
/*  QUALITY DASHBOARD                                                         */
/* ═══════════════════════════════════════════════════════════════════════════ */

function QualityDashboard({ quality, loading, onRefresh }) {
  const tables = Object.entries(quality);

  if (loading) return <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>⏳ Analyzing data quality...</div>;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h2 style={{ margin: 0, fontSize: 22, fontWeight: 700 }}>Data Quality</h2>
        <button onClick={onRefresh} style={{
          padding: '8px 20px', borderRadius: 8, border: '1px solid rgba(255,255,255,0.1)',
          background: 'rgba(255,255,255,0.03)', color: 'var(--text-secondary)',
          fontSize: 12, cursor: 'pointer', fontFamily: "'Inter', sans-serif",
        }}>🔄 Refresh</button>
      </div>

      {!tables.length && <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>Click Refresh to analyze quality metrics</div>}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: 16 }}>
        {tables.map(([name, info]) => {
          const comp = info.completeness || 0;
          const barColor = comp >= 95 ? '#34d399' : comp >= 80 ? '#fbbf24' : '#ef4444';
          return (
            <div key={name} style={{
              background: 'rgba(255,255,255,0.02)', borderRadius: 12,
              border: '1px solid rgba(255,255,255,0.06)', padding: 20,
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                <span style={{ fontFamily: "'Fira Code', monospace", fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{name}</span>
                <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{(info.row_count || 0).toLocaleString()} rows</span>
              </div>

              {/* Completeness bar */}
              <div style={{ marginBottom: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                  <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Completeness</span>
                  <span style={{ fontSize: 11, fontWeight: 600, color: barColor }}>{comp.toFixed(1)}%</span>
                </div>
                <div style={{ height: 4, borderRadius: 2, background: 'rgba(255,255,255,0.06)' }}>
                  <div style={{ height: '100%', borderRadius: 2, width: `${comp}%`, background: barColor, transition: 'width 0.5s' }} />
                </div>
              </div>

              {/* Column null rates */}
              {info.columns && (
                <div style={{ maxHeight: 150, overflowY: 'auto' }}>
                  {Object.entries(info.columns).slice(0, 8).map(([col, metrics]) => (
                    <div key={col} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '3px 0', fontSize: 11 }}>
                      <span style={{ color: 'var(--text-secondary)', fontFamily: "'Fira Code', monospace" }}>{col}</span>
                      <span style={{ color: metrics.null_rate > 10 ? '#ef4444' : metrics.null_rate > 0 ? '#fbbf24' : '#34d399', fontWeight: 500 }}>
                        {metrics.null_rate === 0 ? '✓' : `${metrics.null_rate}% null`}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}


/* ═══════════════════════════════════════════════════════════════════════════ */
/*  CHAT                                                                      */
/* ═══════════════════════════════════════════════════════════════════════════ */

function ChatPanel() {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: '🧠 **Neuro-Fabric Data Assistant**\n\nAsk me anything about your database! I can answer questions using SQL.\n\nTry: *"How many customers?"* or *"Show me revenue stats"*' },
  ]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const endRef = useRef(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  async function send() {
    if (!input.trim() || sending) return;
    const msg = input.trim();
    setInput('');
    setMessages(m => [...m, { role: 'user', content: msg }]);
    setSending(true);

    try {
      const r = await fetch(`${API}/api/chat`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg }),
      });
      const d = await r.json();
      setMessages(m => [...m, { role: 'assistant', content: d.response }]);
    } catch (e) {
      setMessages(m => [...m, { role: 'assistant', content: `Error: ${e.message}` }]);
    }
    setSending(false);
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 200px)' }}>
      {/* Messages */}
      <div style={{
        flex: 1, overflowY: 'auto', padding: 16, display: 'flex', flexDirection: 'column', gap: 12,
        background: 'rgba(255,255,255,0.01)', borderRadius: 12, border: '1px solid rgba(255,255,255,0.06)',
        marginBottom: 12,
      }}>
        {messages.map((m, i) => (
          <div key={i} style={{
            alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
            maxWidth: '75%', padding: '12px 16px', borderRadius: 12,
            background: m.role === 'user'
              ? 'linear-gradient(135deg, rgba(124,58,237,0.25), rgba(99,102,241,0.25))'
              : 'rgba(255,255,255,0.03)',
            border: `1px solid ${m.role === 'user' ? 'rgba(124,58,237,0.3)' : 'rgba(255,255,255,0.06)'}`,
            fontSize: 13, lineHeight: 1.6, color: 'var(--text-secondary)',
            whiteSpace: 'pre-wrap',
          }}>
            {m.content.split('**').map((part, j) =>
              j % 2 === 1 ? <strong key={j} style={{ color: 'var(--text-primary)' }}>{part}</strong> : part
            )}
          </div>
        ))}
        {sending && <div style={{ alignSelf: 'flex-start', padding: '12px 16px', color: 'var(--text-muted)', fontSize: 13 }}>⏳ Thinking...</div>}
        <div ref={endRef} />
      </div>

      {/* Input */}
      <div style={{
        display: 'flex', gap: 8, padding: '0',
      }}>
        <input value={input} onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }}
          placeholder="Ask about your data..."
          style={{
            flex: 1, padding: '14px 18px', borderRadius: 12,
            border: '1px solid rgba(255,255,255,0.08)', background: 'rgba(255,255,255,0.03)',
            color: 'var(--text-primary)', fontSize: 14, outline: 'none',
            fontFamily: "'Inter', sans-serif",
          }}
        />
        <button onClick={send} disabled={sending} style={{
          padding: '14px 24px', borderRadius: 12, border: 'none', cursor: 'pointer',
          background: 'linear-gradient(135deg, #7c3aed, #6366f1)',
          color: '#fff', fontSize: 14, fontWeight: 600, fontFamily: "'Inter', sans-serif",
        }}>Send</button>
      </div>
    </div>
  );
}


/* ═══════════════════════════════════════════════════════════════════════════ */
/*  ARTIFACTS                                                                 */
/* ═══════════════════════════════════════════════════════════════════════════ */

function ArtifactsPanel() {
  const [artifacts, setArtifacts] = useState([]);

  useEffect(() => {
    fetch(`${API}/api/artifacts`).then(r => r.json()).then(setArtifacts).catch(console.error);
  }, []);

  return (
    <div>
      <h2 style={{ margin: '0 0 16px', fontSize: 22, fontWeight: 700 }}>Artifacts</h2>

      {!artifacts.length && (
        <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
          No artifacts yet. Run the AI pipeline to generate documentation artifacts.
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 12 }}>
        {artifacts.map((art, i) => (
          <div key={i} style={{
            background: 'rgba(255,255,255,0.02)', borderRadius: 12,
            border: '1px solid rgba(255,255,255,0.06)', padding: 16,
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          }}>
            <div>
              <div style={{ fontFamily: "'Fira Code', monospace", fontSize: 13, color: 'var(--text-primary)', marginBottom: 4 }}>{art.name}</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{art.size_kb} KB · {art.type.toUpperCase()}</div>
            </div>
            <a href={`${API}/api/artifacts/download/${art.name}`} style={{
              padding: '6px 14px', borderRadius: 6, border: '1px solid rgba(138,92,246,0.3)',
              background: 'rgba(138,92,246,0.1)', color: '#a78bfa',
              fontSize: 11, fontWeight: 600, textDecoration: 'none',
            }}>Download</a>
          </div>
        ))}
      </div>
    </div>
  );
}
