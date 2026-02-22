import {
  useState, useEffect, useRef, useCallback
} from 'react'; import {
  LayoutDashboard, Settings, Database, BookOpen, GitMerge, TerminalSquare, ShieldCheck, MessageSquare, Github, Package, List, ShoppingCart, DollarSign, Users, Star, TrendingUp, Truck, CreditCard, BarChart2, Folder, Key, Link, Table2, ArrowLeft, Hourglass, RefreshCw, Bot, Lightbulb, AlertTriangle, Search, FileText, Command, Play, XCircle, Clock, Check, Brain, MessageCircle, Trash2, User, Info, ArrowRight, CheckCircle2
} from 'lucide-react';
import mermaid from 'mermaid';

mermaid.initialize({
  startOnLoad: false,
  theme: 'dark',
  themeVariables: {
    primaryColor: '#6366f1',
    primaryTextColor: '#f1f5f9',
    primaryBorderColor: '#818cf8',
    lineColor: '#94a3b8',
    secondaryColor: '#1e293b',
    tertiaryColor: '#0f172a',
    background: '#0f172a',
    mainBkg: '#1e293b',
    nodeBorder: '#818cf8',
    clusterBkg: '#1e293b',
    titleColor: '#f1f5f9',
    edgeLabelBackground: '#1e293b',
  },
  er: { useMaxWidth: true, layoutDirection: 'TB' },
  securityLevel: 'loose',
});

const API = 'http://localhost:8000';

const TABS = [
  { id: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard size={16} /> },
  { id: 'settings', label: 'Settings', icon: <Settings size={16} /> },
  { id: 'schema', label: 'Schema', icon: <Database size={16} /> },
  { id: 'docs', label: 'Docs', icon: <BookOpen size={16} /> },
  { id: 'lineage', label: 'Lineage', icon: <GitMerge size={16} /> },
  { id: 'query', label: 'SQL Query', icon: <TerminalSquare size={16} /> },
  { id: 'quality', label: 'Quality', icon: <ShieldCheck size={16} /> },
  { id: 'chat', label: 'Chat', icon: <MessageSquare size={16} /> },
  { id: 'github', label: 'GitHub', icon: <Github size={16} /> },
  { id: 'artifacts', label: 'Artifacts', icon: <Package size={16} /> },
];

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [connected, setConnected] = useState(false);
  const [engine, setEngine] = useState('');
  const [loading, setLoading] = useState(false);
  const [schema, setSchema] = useState({});
  const [quality, setQuality] = useState({});
  const [analytics, setAnalytics] = useState(null);

  useEffect(() => { autoConnect(); }, []);

  async function autoConnect() {
    try {
      const r = await fetch(`${API}/api/health`);
      const d = await r.json();
      setConnected(d.connected);
      setEngine(d.engine || '');
      if (d.connected) {
        loadAnalytics(); loadSchema();
      } else {
        setActiveTab('settings');
      }
    } catch (e) {
      console.error('Auto-connect / Health check failed:', e);
      setActiveTab('settings');
    }
  }

  async function loadSchema() {
    try {
      const r = await fetch(`${API}/api/schema`);
      setSchema(await r.json());
    } catch (e) { console.error(e); }
  }

  async function loadQuality() {
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/quality`);
      setQuality(await r.json());
    } catch (e) { console.error(e); }
    setLoading(false);
  }

  async function loadAnalytics() {
    try {
      const r = await fetch(`${API}/api/analytics/overview`);
      setAnalytics(await r.json());
    } catch (e) { console.error(e); }
  }

  return (
    <div className="app-root">
      {/* Header */}
      <header className="app-header">
        <div className="header-left">
          <span className="logo-icon w-10 h-10"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="100%" height="100%">
            <defs>
              <linearGradient id="neuroGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#8B5CF6" /> <stop offset="100%" stop-color="#3B82F6" /> </linearGradient>
            </defs>

            <path d="M128 32 L212 80 L212 176 L128 224 L44 176 L44 80 Z" fill="none" stroke="#334155" stroke-width="8" stroke-linejoin="round" />
            <path d="M128 32 L128 128 L212 176 M128 128 L44 176 M44 80 L128 128 L212 80" fill="none" stroke="#334155" stroke-width="4" stroke-opacity="0.5" />

            <path d="M128 32 L212 80 L128 128 L44 176 L128 224" fill="none" stroke="url(#neuroGrad)" stroke-width="16" stroke-linecap="round" stroke-linejoin="round" />

            <circle cx="128" cy="32" r="12" fill="#8B5CF6" />
            <circle cx="212" cy="80" r="12" fill="#6D28D9" />
            <circle cx="128" cy="128" r="16" fill="#3B82F6" />
            <circle cx="44" cy="176" r="12" fill="#2563EB" />
            <circle cx="128" cy="224" r="12" fill="#1D4ED8" />
          </svg></span>
          <div>
            <h1 className="logo-text">Neuro-Fabric</h1>
            <p className="logo-sub">DATA DICTIONARY · LOCAL-FIRST</p>
          </div>
        </div>
        <div className="header-right">
          <span className={`status-badge ${connected ? 'connected' : 'disconnected'}`}>
            <span className="status-dot" />
            {connected ? `${engine.toUpperCase()} Connected` : 'Disconnected'}
          </span>
        </div>
      </header>

      {/* Tab Bar */}
      <nav className="tab-bar">
        {TABS.map(tab => (
          <button key={tab.id}
            className={`tab-btn ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => {
              setActiveTab(tab.id);
              if (tab.id === 'quality' && !Object.keys(quality).length) loadQuality();
              if (tab.id === 'schema' && !Object.keys(schema).length) loadSchema();
            }}>
            <span className="tab-icon">{tab.icon}</span> {tab.label}
          </button>
        ))}
      </nav>

      {/* Content */}
      <main className="main-content">
        {activeTab === 'dashboard' && <Dashboard connected={connected} engine={engine} analytics={analytics} schema={schema} />}
        {activeTab === 'settings' && <SettingsPanel onConnect={(status, dbEngine) => {
          setConnected(status); setEngine(dbEngine);
          if (status) { loadSchema(); loadAnalytics(); setActiveTab('dashboard'); }
        }} connected={connected} currentEngine={engine} />}

        {/* Protected Tabs */}
        {connected ? (
          <>
            {activeTab === 'schema' && <SchemaBrowser schema={schema} />}
            {activeTab === 'docs' && <DocsPanel schema={schema} />}
            {activeTab === 'lineage' && <LineagePanel />}
            {activeTab === 'query' && <SQLQuery />}
            {activeTab === 'quality' && <QualityDashboard quality={quality} loading={loading} onRefresh={loadQuality} />}
            {activeTab === 'chat' && <ChatPanel />}
            {activeTab === 'github' && <GitHubPanel />}
            {activeTab === 'artifacts' && <ArtifactsPanel />}
          </>
        ) : (
          activeTab !== 'dashboard' && activeTab !== 'settings' && (
            <div className="empty-state">
              <h2>Connection Required</h2>
              <p>Please connect your database in the Settings tab to access this feature.</p>
              <button className="primary-btn" onClick={() => setActiveTab('settings')} style={{ marginTop: '16px' }}>Go to Settings</button>
            </div>
          )
        )}
      </main>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════ */
/*  DASHBOARD                                                                */
/* ═══════════════════════════════════════════════════════════════════════════ */
function Dashboard({ connected, engine, analytics, schema }) {
  const tableCount = Object.keys(schema).length;
  const totalRows = Object.values(schema).reduce((s, t) => s + (t.row_count || 0), 0);
  const cards = [
    { label: 'Tables', value: tableCount, icon: <Database size={20} />, color: '#6366f1' },
    { label: 'Total Rows', value: totalRows.toLocaleString(), icon: <List size={20} />, color: '#10b981' },
    { label: 'Orders', value: analytics?.total_orders !== undefined ? analytics.total_orders.toLocaleString() : '—', icon: <ShoppingCart size={20} />, color: '#ec4899' },
    { label: 'Revenue', value: analytics?.total_revenue !== undefined ? `R$ ${(analytics.total_revenue / 1000).toFixed(0)}K` : '—', icon: <DollarSign size={20} />, color: '#f59e0b' },
    { label: 'Customers', value: analytics?.unique_customers !== undefined ? analytics.unique_customers.toLocaleString() : '—', icon: <Users size={20} />, color: '#3b82f6' },
    { label: 'Avg Review', value: analytics?.avg_review_score !== undefined ? `${analytics.avg_review_score.toFixed(1)} ⭐` : '—', icon: <Star size={20} />, color: '#8b5cf6' },
  ];

  // Calculate table row distribution for chart
  const tableDistribution = Object.entries(schema)
    .map(([name, info]) => ({ name, rows: info.row_count || 0 }))
    .sort((a, b) => b.rows - a.rows)
    .slice(0, 8);
  const maxRows = Math.max(...tableDistribution.map(t => t.rows), 1);

  // Review score distribution
  const reviewDistribution = analytics?.review_distribution || [];
  const maxReviews = reviewDistribution.length > 0 ? Math.max(...reviewDistribution.map(r => r.count), 1) : 1;

  // Payment type distribution
  const paymentDistribution = analytics?.payment_types || [];
  const maxPayments = paymentDistribution.length > 0 ? Math.max(...paymentDistribution.map(p => p.count), 1) : 1;

  return (
    <div>
      <div className="section-header">
        <h2>Dashboard</h2>
        <p>{connected ? `Connected to ${engine.toUpperCase()} with real-time analytics` : 'Not connected'}</p>
      </div>

      {/* Metric Cards */}
      <div className="card-grid">
        {cards.map(c => (
          <div key={c.label} className="metric-card">
            <div className="metric-top">
              <span className="metric-label">{c.label}</span>
              <span className="metric-icon">{c.icon}</span>
            </div>
            <div className="metric-value" style={{ color: c.color }}>{c.value}</div>
          </div>
        ))}
      </div>

      {/* Charts Row */}
      <div className="charts-row">
        {/* Order Status Distribution */}
        {analytics?.order_status && (
          <div className="chart-card">
            <h3 className="chart-title"><Package size={14} className="inline-icon" /> Order Status</h3>
            <div className="bar-chart">
              {Object.entries(analytics.order_status).map(([status, count]) => {
                const colors = {
                  delivered: '#10b981',
                  shipped: '#3b82f6',
                  approved: '#f59e0b',
                  canceled: '#ef4444',
                  returned: '#f97316',
                  created: '#8b5cf6',
                  processing: '#6366f1',
                  invoiced: '#14b8a6',
                  unavailable: '#94a3b8'
                };
                const total = Object.values(analytics.order_status).reduce((a, b) => a + b, 0);
                const pct = ((count / total) * 100).toFixed(1);
                return (
                  <div key={status} className="bar-row">
                    <div className="bar-label">
                      <span className="bar-name">{status}</span>
                      <span className="bar-value">{count.toLocaleString()}</span>
                    </div>
                    <div className="bar-track">
                      <div
                        className="bar-fill"
                        style={{
                          width: `${pct}%`,
                          background: colors[status] || '#94a3b8'
                        }}
                      />
                    </div>
                    <span className="bar-pct">{pct}%</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Review Score Distribution */}
        {reviewDistribution.length > 0 && (
          <div className="chart-card">
            <h3 className="chart-title">⭐ Review Scores</h3>
            <div className="bar-chart">
              {reviewDistribution.map(r => {
                const pct = ((r.count / maxReviews) * 100).toFixed(1);
                const colors = { 5: '#10b981', 4: '#22c55e', 3: '#f59e0b', 2: '#f97316', 1: '#ef4444' };
                return (
                  <div key={r.score} className="bar-row">
                    <div className="bar-label">
                      <span className="bar-name">{r.score} Stars</span>
                      <span className="bar-value">{r.count.toLocaleString()}</span>
                    </div>
                    <div className="bar-track">
                      <div className="bar-fill" style={{
                        width: `${pct}%`,
                        background: colors[r.score] || '#ceb4ff'
                      }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Second Row */}
      <div className="charts-row 
      ">
        {/* Table Row Distribution */}
        <div className="chart-card">
          <h3 className="chart-title"><BarChart2 size={14} className="inline-icon" /> Table Sizes</h3>
          <div className="bar-chart horizontal">
            {tableDistribution.map(t => {
              const pct = ((t.rows / maxRows) * 100);
              return (
                <div key={t.name} className="bar-row">
                  <span className="bar-name mono">{t.name}</span>
                  <div className="bar-track">
                    <div className="bar-fill" style={{ width: `${pct}%`, background: '#6366f1' }} />
                  </div>
                  <span className="bar-value">{t.rows.toLocaleString()}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Payment Types */}
        {paymentDistribution.length > 0 && (
          <div className="chart-card">
            <h3 className="chart-title">💳 Payment Methods</h3>
            <div className="bar-chart">
              {paymentDistribution.map((p, i) => {
                const total = paymentDistribution.reduce((a, x) => a + x.count, 0);
                const pct = ((p.count / total) * 100).toFixed(1);
                const colors = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];
                return (
                  <div key={p.type} className="bar-row">
                    <div className="bar-label">
                      <span className="bar-name">{p.type.replace('_', ' ')}</span>
                      <span className="bar-value">{p.count.toLocaleString()}</span>
                    </div>
                    <div className="bar-track">
                      <div className="bar-fill" style={{ width: `${pct}%`, background: colors[i] || '#94a3b8' }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Quick Stats Conditional Render Block */}
      {(analytics?.avg_order_value || analytics?.items_per_order || analytics?.delivery_days || analytics?.total_freight) ? (
        <div className="card-grid" style={{ marginTop: '24px' }}>
          {analytics?.avg_order_value && (
            <div className="metric-card">
              <div className="metric-top">
                <span className="metric-label">Avg Order Value</span>
                <span className="metric-icon"><TrendingUp size={20} /></span>
              </div>
              <div className="metric-value">R$ {analytics.avg_order_value.toFixed(2)}</div>
            </div>
          )}
          {analytics?.items_per_order && (
            <div className="metric-card">
              <div className="metric-top">
                <span className="metric-label">Items per Order</span>
                <span className="metric-icon"><ShoppingCart size={20} /></span>
              </div>
              <div className="metric-value">{analytics.items_per_order.toFixed(1)}</div>
            </div>
          )}
          {analytics?.delivery_days && (
            <div className="metric-card">
              <div className="metric-top">
                <span className="metric-label">Avg Delivery Days</span>
                <span className="metric-icon"><Truck size={20} /></span>
              </div>
              <div className="metric-value">{analytics.delivery_days.toFixed(0)}</div>
            </div>
          )}
          {analytics?.total_freight && (
            <div className="metric-card">
              <div className="metric-top">
                <span className="metric-label">Total Freight</span>
                <span className="metric-icon"><DollarSign size={20} /></span>
              </div>
              <div className="metric-value">R$ {(analytics.total_freight / 1000).toFixed(0)}K</div>
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════ */
/*  SCHEMA BROWSER                                                           */
/* ═══════════════════════════════════════════════════════════════════════════ */
function SchemaBrowser({ schema }) {
  const [selected, setSelected] = useState(null);
  const [sampleData, setSampleData] = useState(null);
  const tables = Object.entries(schema);

  async function loadSample(name) {
    try { const r = await fetch(`${API}/api/sample/${encodeURIComponent(name)}?limit=5`); setSampleData(await r.json()); } catch (e) { console.error(e); }
  }

  if (!tables.length) return <div className="empty-state">Loading schema... Connect to database first.</div>;

  const grouped = {};
  tables.forEach(([name, info]) => { const s = info.schema || 'main'; if (!grouped[s]) grouped[s] = []; grouped[s].push([name, info]); });

  return (
    <div className="schema-layout">
      <div className="schema-sidebar">
        <h3 className="sidebar-title">Tables ({tables.length})</h3>
        {Object.entries(grouped).map(([s, tbls]) => (
          <div key={s} className="schema-group">
            <div className="schema-name"><Folder size={16} className="inline-icon" /> {s}</div>
            {tbls.map(([name, info]) => (
              <button key={name} className={`table-btn ${selected === name ? 'active' : ''}`}
                onClick={() => { setSelected(name); loadSample(name); }}>
                <span>{info.table_name}</span>
                <span className="row-count">{(info.row_count || 0).toLocaleString()}</span>
              </button>
            ))}
          </div>
        ))}
      </div>
      <div className="schema-detail">
        {selected && schema[selected] ? (
          <div className="card">
            <div className="detail-header">
              <div>
                <h3 className="detail-title">{selected}</h3>
                <p className="detail-sub">{schema[selected].columns.length} columns · {(schema[selected].row_count || 0).toLocaleString()} rows</p>
              </div>
            </div>
            <table className="data-table">
              <thead><tr>
                <th>Column</th><th>Type</th><th>Nullable</th><th>Key</th>
              </tr></thead>
              <tbody>
                {schema[selected].columns.map(col => (
                  <tr key={col.name}>
                    <td className={`mono ${col.is_primary_key ? 'pk-col' : ''}`}>{col.is_primary_key && <Key size={12} className="inline-icon" style={{ marginRight: '4px', color: 'var(--primary)' }} />}{col.name}</td>
                    <td className="mono type-col">{col.type}</td>
                    <td className={col.nullable ? 'yes-col' : 'no-col'}>{col.nullable ? 'YES' : 'NO'}</td>
                    <td>{col.is_primary_key && <span className="pk-badge">PK</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {schema[selected].foreign_keys?.length > 0 && (
              <div className="fk-section">
                <h4 className="fk-title"><Link size={14} className="inline-icon" /> Foreign Keys</h4>
                {schema[selected].foreign_keys.map((fk, i) => (
                  <div key={i} className="fk-item">{fk.from_column} → {fk.to_table}.{fk.to_column}</div>
                ))}
              </div>
            )}
            {sampleData?.rows?.length > 0 && (
              <div className="sample-section">
                <h4 className="sample-title"><Table2 size={14} className="inline-icon" /> Sample Data</h4>
                <div className="table-scroll">
                  <table className="data-table compact">
                    <thead><tr>{sampleData.columns.map(c => <th key={c} className="mono">{c}</th>)}</tr></thead>
                    <tbody>{sampleData.rows.map((row, i) => (
                      <tr key={i}>{sampleData.columns.map(c => (
                        <td key={c} className="mono">{row[c] === null ? <span className="null-val">null</span> : String(row[c]).substring(0, 50)}</td>
                      ))}</tr>
                    ))}</tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        ) : <div className="empty-state"><ArrowLeft size={16} className="inline-icon" /> Select a table to view its schema</div>}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════ */
/*  DOCUMENTATION PANEL                                                       */
/* ═══════════════════════════════════════════════════════════════════════════ */
function DocsPanel({ schema }) {
  const [selectedTable, setSelectedTable] = useState(null);
  const [docs, setDocs] = useState({});
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    const tables = Object.keys(schema);
    if (tables.length > 0 && !selectedTable) {
      setSelectedTable(tables[0]);
    }
  }, [schema]);

  async function generateDocs(tableName) {
    setGenerating(true);
    try {
      const tableInfo = schema[tableName];
      const r = await fetch(`${API}/api/docs/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          table_name: tableName,
          columns: tableInfo?.columns || [],
          row_count: tableInfo?.row_count || 0,
          foreign_keys: tableInfo?.foreign_keys || []
        })
      });
      const d = await r.json();
      setDocs(prev => ({ ...prev, [tableName]: d }));
    } catch (e) {
      console.error('Failed to generate docs:', e);
      // Fallback to local generation
      const tableInfo = schema[tableName];
      setDocs(prev => ({
        ...prev,
        [tableName]: generateLocalDocs(tableName, tableInfo)
      }));
    }
    setGenerating(false);
  }

  function generateLocalDocs(tableName, tableInfo) {
    const columns = tableInfo?.columns || [];
    const rowCount = tableInfo?.row_count || 0;
    const fks = tableInfo?.foreign_keys || [];

    // Generate business-friendly descriptions
    const tableDescriptions = {
      customers: 'Stores customer information including unique identifiers, contact details, and location data. Each customer can have multiple orders.',
      orders: 'Contains order transactions with status tracking, timestamps for purchase, approval, and delivery. Links to customers and order items.',
      order_items: 'Individual items within each order, tracking product, seller, price, and shipping costs.',
      products: 'Product catalog with category classifications and physical dimensions for shipping calculations.',
      sellers: 'Seller profiles with location information for marketplace vendors.',
      payments: 'Payment transactions linked to orders, tracking payment type, installments, and amounts.',
      reviews: 'Customer reviews and satisfaction scores for completed orders.',
      geolocation: 'Geographic coordinate mapping for Brazilian zip codes, enabling location-based analytics.',
      product_categories: 'Product taxonomy with English translations of category names.'
    };

    const columnDescriptions = {
      customer_id: 'Unique identifier for each customer',
      customer_unique_id: 'Internal identifier to track repeat customers',
      order_id: 'Unique transaction identifier',
      order_status: 'Current state: pending, processing, shipped, delivered, cancelled',
      order_purchase_timestamp: 'When the order was placed',
      order_delivered_customer_date: 'Actual delivery completion date',
      order_estimated_delivery_date: 'Promised delivery date for SLA tracking',
      payment_type: 'Method: credit_card, boleto, voucher, debit_card',
      payment_value: 'Total payment amount in Brazilian Reais',
      review_score: 'Customer satisfaction rating (1-5 scale)',
      price: 'Item price excluding shipping',
      freight_value: 'Shipping cost for this item',
      product_category_name: 'Category in Portuguese',
      product_category_name_english: 'Translated category name for international use',
      seller_id: 'Unique marketplace vendor identifier',
      product_photos_qty: 'Number of product images available',
      product_weight_g: 'Weight in grams for shipping calculations',
      product_length_cm: 'Package length in centimeters',
      product_height_cm: 'Package height in centimeters',
      product_width_cm: 'Package width in centimeters'
    };

    const businessInsights = [];

    // Generate insights based on table structure
    if (fks.length > 0) {
      businessInsights.push(`**Relationships:** Connects to ${fks.map(fk => fk.to_table).join(', ')}`);
    }
    if (columns.some(c => c.name.includes('timestamp') || c.name.includes('date'))) {
      businessInsights.push('**Time-series:** Contains temporal data suitable for trend analysis and forecasting');
    }
    if (columns.some(c => c.name.includes('price') || c.name.includes('value') || c.name.includes('amount'))) {
      businessInsights.push('**Financial:** Contains monetary values - ensure proper decimal handling');
    }
    if (rowCount > 10000) {
      businessInsights.push(`**Scale:** Large dataset (${rowCount.toLocaleString()} rows) - consider partitioning for performance`);
    }

    return {
      table_name: tableName,
      business_description: tableDescriptions[tableName] || `Data table with ${columns.length} columns and ${rowCount.toLocaleString()} records.`,
      column_descriptions: columns.map(col => ({
        name: col.name,
        type: col.type,
        nullable: col.nullable,
        is_pk: col.is_primary_key,
        description: columnDescriptions[col.name] || inferColumnDescription(col),
        business_use: inferBusinessUse(col)
      })),
      data_quality_notes: generateQualityNotes(columns, rowCount),
      business_insights: businessInsights,
      suggested_queries: generateSuggestedQueries(tableName, columns),
      generated_at: new Date().toISOString()
    };
  }

  function inferColumnDescription(col) {
    const name = col.name.toLowerCase();
    if (name.includes('_id')) return 'Unique identifier field';
    if (name.includes('_date') || name.includes('timestamp')) return 'Temporal tracking field';
    if (name.includes('name')) return 'Descriptive name field';
    if (name.includes('count') || name.includes('qty')) return 'Quantity counter';
    if (name.includes('value') || name.includes('price') || name.includes('amount')) return 'Monetary value field';
    if (name.includes('zip') || name.includes('postal')) return 'Location identifier';
    if (name.includes('city') || name.includes('state')) return 'Geographic location field';
    if (name.includes('status')) return 'Status indicator field';
    if (name.includes('lat') || name.includes('lng')) return 'Geographic coordinate';
    if (col.is_primary_key) return 'Primary key - unique row identifier';
    return `${col.type} data field`;
  }

  function inferBusinessUse(col) {
    const name = col.name.toLowerCase();
    if (col.is_primary_key) return 'Record identification';
    if (name.includes('price') || name.includes('value')) return 'Revenue analytics';
    if (name.includes('date') || name.includes('timestamp')) return 'Trend analysis, SLA monitoring';
    if (name.includes('status')) return 'Operational dashboards';
    if (name.includes('customer')) return 'Customer analytics, segmentation';
    if (name.includes('product')) return 'Inventory management, catalog';
    if (name.includes('seller')) return 'Vendor performance analysis';
    if (name.includes('review') || name.includes('score')) return 'Customer satisfaction metrics';
    return 'General data field';
  }

  function generateQualityNotes(columns, rowCount) {
    const notes = [];
    const nullableCols = columns.filter(c => c.nullable);
    if (nullableCols.length > 0) {
      notes.push(`${nullableCols.length} columns allow NULL values - check for missing data`);
    }
    const pkCols = columns.filter(c => c.is_primary_key);
    if (pkCols.length === 0) {
      notes.push('No primary key defined - verify data uniqueness');
    }
    if (rowCount === 0) {
      notes.push('Empty table - verify data load completed');
    }
    return notes;
  }

  function generateSuggestedQueries(tableName, columns) {
    const queries = {
      customers: [
        'SELECT city, COUNT(*) as customer_count FROM customers GROUP BY city ORDER BY customer_count DESC LIMIT 10',
        'SELECT state, COUNT(*) as customers_by_state FROM customers GROUP BY state'
      ],
      orders: [
        'SELECT order_status, COUNT(*) FROM orders GROUP BY order_status',
        'SELECT DATE_TRUNC(\'month\', order_purchase_timestamp) as month, COUNT(*) FROM orders GROUP BY month ORDER BY month'
      ],
      order_items: [
        'SELECT product_id, COUNT(*) as times_ordered, SUM(price) as total_revenue FROM order_items GROUP BY product_id ORDER BY total_revenue DESC LIMIT 10'
      ],
      payments: [
        'SELECT payment_type, COUNT(*), AVG(payment_value) FROM payments GROUP BY payment_type'
      ],
      reviews: [
        'SELECT review_score, COUNT(*) FROM reviews GROUP BY review_score ORDER BY review_score'
      ]
    };
    return queries[tableName] || [
      `SELECT * FROM ${tableName} LIMIT 10`,
      `SELECT COUNT(*) FROM ${tableName}`
    ];
  }

  const tableNames = Object.keys(schema);
  const currentDoc = docs[selectedTable] || (selectedTable && schema[selectedTable] ? generateLocalDocs(selectedTable, schema[selectedTable]) : null);

  return (
    <div className="docs-layout">
      <div className="docs-sidebar">
        <div className="docs-sidebar-header">
          <h3 className="docs-sidebar-title">Tables</h3>
          <button
            className="generate-all-btn"
            onClick={() => tableNames.forEach(t => generateDocs(t))}
            disabled={generating}>
            {generating ? <Hourglass size={16} className="animate-spin inline-icon" /> : <RefreshCw size={16} className="inline-icon" />} Refresh All
          </button>
        </div>
        <div className="docs-table-list">
          {tableNames.map(name => (
            <div
              key={name}
              className={`docs-table-item ${selectedTable === name ? 'active' : ''}`}
              onClick={() => setSelectedTable(name)}>
              <span className="docs-table-icon"><BarChart2 size={16} /></span>
              <span className="docs-table-name">{name}</span>
              <span className="docs-table-rows">{(schema[name]?.row_count || 0).toLocaleString()}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="docs-content">
        {currentDoc ? (
          <div className="docs-detail">
            <div className="docs-header">
              <div>
                <h2 className="docs-title">{currentDoc.table_name}</h2>
                <p className="docs-subtitle">{currentDoc.business_description}</p>
              </div>
              <button
                className="generate-btn"
                onClick={() => generateDocs(selectedTable)}
                disabled={generating}>
                {generating ? <><Hourglass size={16} className="animate-spin inline-icon" /> Generating...</> : <><Bot size={16} className="inline-icon" /> AI Enhance</>}
              </button>
            </div>

            {/* Business Insights */}
            {currentDoc.business_insights?.length > 0 && (
              <div className="docs-section">
                <h3 className="docs-section-title"><Lightbulb size={16} className="inline-icon" /> Business Insights</h3>
                <div className="insights-grid">
                  {currentDoc.business_insights.map((insight, i) => (
                    <div key={i} className="insight-card">
                      <MarkdownRenderer content={insight} />
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Column Documentation */}
            <div className="docs-section">
              <h3 className="docs-section-title"><FileText size={16} className="inline-icon" /> Column Documentation</h3>
              <div className="table-scroll">
                <table className="data-table docs-table">
                  <thead>
                    <tr>
                      <th>Column</th>
                      <th>Type</th>
                      <th>Description</th>
                      <th>Business Use</th>
                      <th>Nullable</th>
                    </tr>
                  </thead>
                  <tbody>
                    {currentDoc.column_descriptions?.map(col => (
                      <tr key={col.name}>
                        <td className={`mono ${col.is_pk ? 'pk-col' : ''}`}>
                          {col.is_pk && <Key size={14} className="inline-icon pk-icon" />}{col.name}
                        </td>
                        <td className="mono type-col">{col.type}</td>
                        <td>{col.description}</td>
                        <td className="business-use">{col.business_use}</td>
                        <td className={col.nullable ? 'yes-col' : 'no-col'}>
                          {col.nullable ? 'YES' : 'NO'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Data Quality Notes */}
            {currentDoc.data_quality_notes?.length > 0 && (
              <div className="docs-section">
                <h3 className="docs-section-title"><AlertTriangle size={16} className="inline-icon" /> Data Quality Notes</h3>
                <ul className="quality-notes-list">
                  {currentDoc.data_quality_notes.map((note, i) => (
                    <li key={i}>{note}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Suggested Queries */}
            {currentDoc.suggested_queries?.length > 0 && (
              <div className="docs-section">
                <h3 className="docs-section-title"><Search size={16} className="inline-icon" /> Suggested Queries</h3>
                <div className="suggested-queries">
                  {currentDoc.suggested_queries.map((query, i) => (
                    <div key={i} className="query-suggestion">
                      {typeof query === 'object' ? (
                        <>
                          <div className="query-header">
                            <span className="query-name">{query.name}</span>
                            <span className="query-description">{query.description}</span>
                          </div>
                          <code className="mono">{query.sql}</code>
                        </>
                      ) : (
                        <code className="mono">{query}</code>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="empty-state">
            <div className="empty-icon"><FileText size={48} /></div>
            <div>Select a table to view documentation</div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════ */
/*  SQL QUERY                                                                */
/* ═══════════════════════════════════════════════════════════════════════════ */
function SQLQuery() {
  const [query, setQuery] = useState('-- Connect a database and click a suggestion below to get started');
  const [result, setResult] = useState(null);
  const [running, setRunning] = useState(false);
  const [quickQueries, setQuickQueries] = useState([]);
  const [loadingQueries, setLoadingQueries] = useState(true);

  useEffect(() => { loadSuggestions(); }, []);

  async function loadSuggestions() {
    setLoadingQueries(true);
    try {
      const r = await fetch(`${API}/api/query/suggestions`);
      const d = await r.json();
      setQuickQueries(d.suggestions || []);
      if (d.suggestions?.length) {
        setQuery(d.suggestions[0].sql);
      }
    } catch (e) { console.error('Failed to load query suggestions', e); }
    setLoadingQueries(false);
  }

  async function runQuery() {
    setRunning(true); setResult(null);
    const start = Date.now();
    try {
      const r = await fetch(`${API}/api/query`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query: query.trim(), limit: 200 }) });
      const d = await r.json();
      d.duration_ms = Date.now() - start;
      setResult(d);
    } catch (e) { setResult({ error: e.message }); }
    setRunning(false);
  }

  return (
    <div>
      <div className="section-header">
        <h2>SQL Query Engine</h2>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <span className="engine-badge"><Command size={14} className="inline-icon" /> Live Database</span>
          <button className="secondary-btn" onClick={loadSuggestions} style={{ padding: '4px 10px', fontSize: '0.8rem' }}>
            <RefreshCw size={12} /> Refresh Queries
          </button>
        </div>
      </div>
      <div className="quick-queries">
        {loadingQueries ? <span style={{ fontSize: '0.85em', color: 'var(--muted-foreground)' }}>Loading dynamic queries...</span> :
          quickQueries.length ? quickQueries.map(qq => (
            <button key={qq.label} className="quick-btn" onClick={() => setQuery(qq.sql)}>{qq.label}</button>
          )) : <span style={{ fontSize: '0.85em', color: 'var(--muted-foreground)' }}>Connect a database to get query suggestions</span>
        }
      </div>
      <div className="query-editor">
        <textarea value={query} onChange={e => setQuery(e.target.value)}
          onKeyDown={e => { if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') { e.preventDefault(); runQuery(); } }}
          className="query-textarea" placeholder="Write SQL... Press Cmd+Enter to run" />
        <div className="query-footer">
          <span className="shortcut-hint flex items-center"><Command size={12} className="inline-icon" />+Enter to execute</span>
          <button onClick={runQuery} disabled={running} className="run-btn">
            {running ? <><Hourglass size={16} className="animate-spin inline-icon" /> Running...</> : <><Play size={16} className="inline-icon" /> Execute</>}
          </button>
        </div>
      </div>
      {result && (
        <div className="result-card">
          {result.error ? (
            <div className="error-msg"><XCircle size={16} className="inline-icon text-red-500" /> {result.error}</div>
          ) : (<>
            <div className="result-meta">
              <span>{result.row_count} row{result.row_count !== 1 ? 's' : ''} returned{result.truncated && ' (truncated)'}</span>
              <span><Clock size={14} className="inline-icon" /> {result.duration_ms}ms · {result.engine}</span>
            </div>
            <div className="table-scroll">
              <table className="data-table">
                <thead><tr>{result.columns?.map(c => <th key={c} className="mono result-th">{c}</th>)}</tr></thead>
                <tbody>{result.rows?.map((row, i) => (
                  <tr key={i}>{result.columns?.map(c => (
                    <td key={c} className="mono">{row[c] === null ? <span className="null-val">null</span> : String(row[c])}</td>
                  ))}</tr>
                ))}</tbody>
              </table>
            </div>
          </>)}
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════ */
/*  QUALITY                                                                  */
/* ═══════════════════════════════════════════════════════════════════════════ */
function QualityDashboard({ quality, loading, onRefresh }) {
  // Extract the array of table quality metrics from the backend response
  const tables = Array.isArray(quality) ? quality : (quality?.quality || []);

  if (loading) return <div className="empty-state"><Hourglass size={24} className="animate-spin inline-icon" /> Analyzing data quality...</div>;

  return (
    <div>
      <div className="section-header">
        <h2>Data Quality</h2>
        <button className="refresh-btn" onClick={onRefresh}><RefreshCw size={16} className="inline-icon" /> Refresh</button>
      </div>
      {!tables.length && <div className="empty-state">Click Refresh to analyze quality metrics</div>}
      <div className="quality-grid">
        {tables.map((info) => {
          const name = info.table_name;
          const comp = (info.overall_completeness || 0) * 100;
          const barColor = comp >= 95 ? '#10b981' : comp >= 80 ? '#f59e0b' : '#ef4444';
          return (
            <div key={name} className="card quality-card">
              <div className="quality-header">
                <span className="mono quality-name">{name}</span>
                <span className="row-count">{(info.row_count || 0).toLocaleString()} rows</span>
              </div>
              <div className="bar-section">
                <div className="bar-label"><span>Completeness</span><span style={{ color: barColor, fontWeight: 600 }}>{comp.toFixed(1)}%</span></div>
                <div className="bar-track"><div className="bar-fill" style={{ width: `${comp}%`, background: barColor }} /></div>
              </div>
              {info.column_quality && (
                <div className="col-metrics">
                  {info.column_quality.slice(0, 8).map((col) => {
                    const nullPct = (col.null_rate * 100).toFixed(1);
                    return (
                      <div key={col.column_name} className="col-row">
                        <span className="mono">{col.column_name}</span>
                        <span className={nullPct > 10 ? 'bad' : nullPct > 0 ? 'warn' : 'good'}>
                          {nullPct === '0.0' ? <Check size={14} className="inline-icon text-green-500" /> : `${nullPct}% null`}
                        </span>
                      </div>
                    );
                  })}
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
/*  CHAT - ChatGPT Style Interface                                           */
/* ═══════════════════════════════════════════════════════════════════════════ */
function ChatPanel() {
  const [threads, setThreads] = useState([
    { id: 'default', title: 'New Chat', messages: [{ role: 'assistant', content: '**Neuro-Fabric Data Assistant**\n\nAsk me anything about your database. I can answer questions using SQL, analyze your schema, and reference your codebase if GitHub is connected.\n\nTry: *"How many customers?"* or *"Which tables are unused in the code?"*' }], createdAt: new Date() }
  ]);
  const [activeThread, setActiveThread] = useState('default');
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [thinkingPhase, setThinkingPhase] = useState(0);
  const [phaseLabel, setPhaseLabel] = useState('');
  const wsRef = useRef(null);
  const endRef = useRef(null);
  const activeThreadRef = useRef(activeThread);

  // Keep a ref in sync so WS callbacks access the latest thread
  useEffect(() => { activeThreadRef.current = activeThread; }, [activeThread]);

  const messages = threads.find(t => t.id === activeThread)?.messages || [];

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, thinkingPhase]);

  // WebSocket connection management
  useEffect(() => {
    function connect() {
      const wsUrl = API.replace('http', 'ws') + '/ws/chat';
      const socket = new WebSocket(wsUrl);

      socket.onopen = () => { console.log('WS Chat connected'); };

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'phase') {
            setThinkingPhase(data.phase);
            setPhaseLabel(data.label || '');
          } else if (data.type === 'response') {
            setThreads(prev => prev.map(t =>
              t.id === activeThreadRef.current
                ? { ...t, messages: [...t.messages, { role: 'assistant', content: data.content }] }
                : t
            ));
            setSending(false);
          } else if (data.type === 'error') {
            setThreads(prev => prev.map(t =>
              t.id === activeThreadRef.current
                ? { ...t, messages: [...t.messages, { role: 'assistant', content: `Error: ${data.content}` }] }
                : t
            ));
            setSending(false);
          }
        } catch (e) { console.error('WS parse error', e); }
      };

      socket.onclose = () => {
        console.log('WS Chat disconnected, reconnecting...');
        setTimeout(connect, 2000);
      };

      socket.onerror = (e) => { console.error('WS error', e); };

      wsRef.current = socket;
    }

    connect();
    return () => { wsRef.current?.close(); };
  }, []);

  function send() {
    if (!input.trim() || sending) return;
    const msg = input.trim();
    setInput('');
    setThreads(prev => prev.map(t =>
      t.id === activeThread
        ? { ...t, messages: [...t.messages, { role: 'user', content: msg }] }
        : t
    ));
    setSending(true);
    setThinkingPhase(0);
    setPhaseLabel('Connecting...');

    // Send via WebSocket, fallback to HTTP if WS not ready
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ message: msg }));
    } else {
      // HTTP fallback
      (async () => {
        try {
          const r = await fetch(`${API}/api/chat`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: msg }) });
          const d = await r.json();
          setThreads(prev => prev.map(t =>
            t.id === activeThread
              ? { ...t, messages: [...t.messages, { role: 'assistant', content: d.response }] }
              : t
          ));
        } catch (e) {
          setThreads(prev => prev.map(t =>
            t.id === activeThread
              ? { ...t, messages: [...t.messages, { role: 'assistant', content: `Error: ${e.message}` }] }
              : t
          ));
        }
        setSending(false);
      })();
    }
  }

  function newChat() {
    const id = `chat_${Date.now()}`;
    setThreads(prev => [{ id, title: 'New Chat', messages: [{ role: 'assistant', content: '**Neuro-Fabric Data Assistant**\n\nHow can I help you analyze your data today?' }], createdAt: new Date() }, ...prev]);
    setActiveThread(id);
  }

  function deleteThread(id) {
    if (threads.length === 1) return;
    setThreads(prev => prev.filter(t => t.id !== id));
    if (activeThread === id) {
      setActiveThread(threads.find(t => t.id !== id)?.id || 'default');
    }
  }

  return (
    <div className="chat-layout">
      {/* Sidebar */}
      <div className="chat-sidebar">
        <div className="chat-sidebar-header">
          <h3 className="chat-sidebar-title">Chats</h3>
          <button className="new-chat-btn" onClick={newChat}>
            <span>+</span> New
          </button>
        </div>
        <div className="chat-history-list">
          {threads.map(thread => (
            <div key={thread.id}
              className={`chat-history-item ${activeThread === thread.id ? 'active' : ''}`}
              onClick={() => setActiveThread(thread.id)}>
              <span className="chat-history-icon"><MessageCircle size={14} /></span>
              <span className="chat-history-title">{thread.title}</span>
              <div className="chat-history-actions">
                <button className="chat-action-btn" onClick={(e) => { e.stopPropagation(); deleteThread(thread.id); }}><Trash2 size={16} /></button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="chat-main">
        <div className="chat-header">
          <span className="chat-header-title">Neuro-Fabric Assistant</span>
          <span className="chat-header-model">Gemini Pro</span>
        </div>

        <div className="chat-messages">
          {messages.length === 0 ? (
            <div className="chat-empty">
              <div className="chat-empty-icon"><Brain size={48} /></div>
              <div className="chat-empty-title">Start a conversation</div>
              <div className="chat-empty-desc">Ask questions about your database, analyze data quality, or generate documentation.</div>
              <div className="chat-suggestions">
                {['How many orders?', 'Show revenue stats', 'Analyze data quality', 'Top products'].map(q => (
                  <button key={q} className="chat-suggestion" onClick={() => { setInput(q); }}>{q}</button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((m, i) => (
              <div key={i} className={`chat-message ${m.role}`}>
                <div className={`chat-avatar ${m.role}`}>
                  {m.role === 'assistant' ? <Brain size={16} /> : <User size={16} />}
                </div>
                <div className="chat-content">
                  <div className="chat-content-header">
                    <span className="chat-role">{m.role === 'assistant' ? 'Assistant' : 'You'}</span>
                  </div>
                  <div className="chat-content-body">
                    <MarkdownRenderer content={m.content} />
                  </div>
                </div>
              </div>
            ))
          )}
          {sending && (
            <div className="chat-message assistant">
              <div className="chat-avatar assistant"><Brain size={16} /></div>
              <div className="chat-content">
                <div className="thinking-steps">
                  {[
                    { icon: <Database size={14} />, label: 'Checking database schema...' },
                    { icon: <Search size={14} />, label: 'Analyzing your query...' },
                    { icon: <FileText size={14} />, label: 'Reviewing code context...' },
                    { icon: <Brain size={14} />, label: 'Generating response...' },
                  ].map((step, i) => (
                    <div key={i} className={`thinking-step ${i <= thinkingPhase ? 'active' : ''} ${i === thinkingPhase ? 'current' : ''}`}>
                      <span className="thinking-step-icon">{step.icon}</span>
                      <span className="thinking-step-label">{step.label}</span>
                      {i < thinkingPhase && <Check size={12} style={{ color: '#10b981', marginLeft: '4px' }} />}
                      {i === thinkingPhase && <span className="thinking-pulse"></span>}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
          <div ref={endRef} />
        </div>

        <div className="chat-input-area">
          <div className="chat-input-container">
            <textarea
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }}
              placeholder="Ask about your data... (Shift+Enter for new line)"
              className="chat-input"
              rows={1}
            />
            <button className="chat-send-btn" onClick={send} disabled={sending || !input.trim()}>
              <ArrowRight size={16} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

/* Simple Markdown Renderer */
function MarkdownRenderer({ content }) {
  const parts = [];
  let key = 0;
  let remaining = content;

  // Process code blocks
  const codeBlockRegex = /```(\w*)\n([\s\S]*?)```/g;
  let match;
  let lastIndex = 0;

  while ((match = codeBlockRegex.exec(remaining)) !== null) {
    if (match.index > lastIndex) {
      parts.push(renderInline(remaining.slice(lastIndex, match.index), key++));
    }
    parts.push(
      <div key={key++} className="chat-code-block">
        <div className="chat-code-header">
          <span className="chat-code-lang">{match[1] || 'code'}</span>
        </div>
        <pre className="chat-code-content">
          <code>{match[2].trim()}</code>
        </pre>
      </div>
    );
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < remaining.length) {
    parts.push(renderInline(remaining.slice(lastIndex), key++));
  }

  return <>{parts}</>;
}

function renderInline(text, key) {
  // Split by lines for block-level processing
  const lines = text.split('\n');
  const elements = [];
  let listBuffer = [];
  let inList = false;
  let listKey = 0;

  function flushList() {
    if (listBuffer.length > 0) {
      elements.push(
        <ul key={`list-${listKey++}`} style={{ margin: '8px 0', paddingLeft: '20px', listStyle: 'disc' }}>
          {listBuffer.map((item, i) => <li key={i} dangerouslySetInnerHTML={{ __html: formatLine(item) }} style={{ marginBottom: '4px', lineHeight: 1.6 }} />)}
        </ul>
      );
      listBuffer = [];
      inList = false;
    }
  }

  function formatLine(line) {
    // Bold
    line = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Italic
    line = line.replace(/(?<![*])\*([^*]+)\*(?![*])/g, '<em>$1</em>');
    // Inline code
    line = line.replace(/`([^`]+)`/g, '<code style="background:rgba(99,102,241,0.15);padding:2px 6px;border-radius:4px;font-size:0.9em">$1</code>');
    return line;
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    // Headings
    if (trimmed.startsWith('### ')) {
      flushList();
      elements.push(<h4 key={`h-${i}`} style={{ margin: '16px 0 8px', fontSize: '1em', fontWeight: 700, color: 'var(--foreground)' }} dangerouslySetInnerHTML={{ __html: formatLine(trimmed.slice(4)) }} />);
    } else if (trimmed.startsWith('## ')) {
      flushList();
      elements.push(<h3 key={`h-${i}`} style={{ margin: '20px 0 10px', fontSize: '1.1em', fontWeight: 700, color: 'var(--foreground)' }} dangerouslySetInnerHTML={{ __html: formatLine(trimmed.slice(3)) }} />);
    } else if (trimmed.startsWith('# ')) {
      flushList();
      elements.push(<h2 key={`h-${i}`} style={{ margin: '24px 0 12px', fontSize: '1.2em', fontWeight: 700, color: 'var(--foreground)' }} dangerouslySetInnerHTML={{ __html: formatLine(trimmed.slice(2)) }} />);
    }
    // Horizontal rule
    else if (trimmed === '---' || trimmed === '***') {
      flushList();
      elements.push(<hr key={`hr-${i}`} style={{ border: 'none', borderTop: '1px solid var(--border)', margin: '16px 0' }} />);
    }
    // Bullet lists
    else if (/^[\*\-•]\s/.test(trimmed)) {
      inList = true;
      listBuffer.push(trimmed.replace(/^[\*\-•]\s/, ''));
    }
    // Numbered lists
    else if (/^\d+\.\s/.test(trimmed)) {
      flushList();
      // Collect sequential numbered items
      const numItems = [trimmed.replace(/^\d+\.\s/, '')];
      while (i + 1 < lines.length && /^\d+\.\s/.test(lines[i + 1].trim())) {
        i++;
        numItems.push(lines[i].trim().replace(/^\d+\.\s/, ''));
      }
      elements.push(
        <ol key={`ol-${i}`} style={{ margin: '8px 0', paddingLeft: '20px' }}>
          {numItems.map((item, j) => <li key={j} dangerouslySetInnerHTML={{ __html: formatLine(item) }} style={{ marginBottom: '4px', lineHeight: 1.6 }} />)}
        </ol>
      );
    }
    // Empty line
    else if (trimmed === '') {
      flushList();
      elements.push(<div key={`br-${i}`} style={{ height: '8px' }} />);
    }
    // Normal text
    else {
      flushList();
      elements.push(<p key={`p-${i}`} style={{ margin: '4px 0', lineHeight: 1.7 }} dangerouslySetInnerHTML={{ __html: formatLine(trimmed) }} />);
    }
  }
  flushList();

  return <div key={key}>{elements}</div>;
}

/* ═══════════════════════════════════════════════════════════════════════════ */
/*  ARTIFACTS                                                                */
/* ═══════════════════════════════════════════════════════════════════════════ */
function ArtifactsPanel() {
  const [artifacts, setArtifacts] = useState([]);
  useEffect(() => { fetch(`${API}/api/artifacts`).then(r => r.json()).then(setArtifacts).catch(console.error); }, []);

  return (
    <div>
      <h2 className="section-title">Artifacts</h2>
      {!artifacts.length && <div className="empty-state">No artifacts yet. Run the AI pipeline to generate documentation.</div>}
      <div className="artifact-grid">
        {artifacts.map((art, i) => (
          <div key={i} className="card artifact-row">
            <div>
              <div className="mono artifact-name">{art.name}</div>
              <div className="artifact-meta">{art.size_kb} KB · {art.type.toUpperCase()}</div>
            </div>
            <a href={`${API}/api/artifacts/download/${art.name}`} className="download-btn">Download</a>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════ */
/*  LINEAGE PANEL (In-Memory FK Graph + ER Diagram)                            */
/* ═══════════════════════════════════════════════════════════════════════════ */
function LineagePanel() {
  const [graph, setGraph] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [view, setView] = useState('graph'); // 'graph' or 'er'
  const [erDiagram, setErDiagram] = useState(null);
  const [erLoading, setErLoading] = useState(false);
  const [showCode, setShowCode] = useState(false);
  const mermaidRef = useRef(null);

  useEffect(() => { loadGraph(); }, []);

  // Render mermaid diagram whenever erDiagram changes and view is 'er'
  useEffect(() => {
    if (view === 'er' && erDiagram?.mermaid && mermaidRef.current && !showCode) {
      const renderDiagram = async () => {
        try {
          const id = 'er-diagram-' + Date.now();
          const { svg } = await mermaid.render(id, erDiagram.mermaid);
          if (mermaidRef.current) {
            mermaidRef.current.innerHTML = svg;
            // Make the SVG responsive
            const svgEl = mermaidRef.current.querySelector('svg');
            if (svgEl) {
              svgEl.style.maxWidth = '100%';
              svgEl.style.height = 'auto';
              svgEl.style.minHeight = '400px';
            }
          }
        } catch (e) {
          console.error('Mermaid render error:', e);
          if (mermaidRef.current) {
            mermaidRef.current.innerHTML = '<p style="color:#ef4444;padding:16px">Failed to render diagram. Try "Show Code" to see the raw Mermaid syntax.</p>';
          }
        }
      };
      renderDiagram();
    }
  }, [erDiagram, view, showCode]);

  async function loadGraph() {
    setLoading(true);
    setError('');
    try {
      const r = await fetch(`${API}/api/lineage/graph`);
      const data = await r.json();
      if (data.error) setError(data.error);
      else setGraph(data);
    } catch (e) {
      setError(e.message);
    }
    setLoading(false);
  }

  async function loadER() {
    setErLoading(true);
    try {
      const r = await fetch(`${API}/api/lineage/er-diagram`);
      const data = await r.json();
      setErDiagram(data);
    } catch (e) {
      console.error('Failed to load ER diagram', e);
    }
    setErLoading(false);
  }

  function handleViewToggle(v) {
    setView(v);
    if (v === 'er' && !erDiagram) loadER();
  }

  if (loading) return <div className="loading-state">Building lineage graph from schema...</div>;

  return (
    <div className="card">
      <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 className="card-title">Data Lineage</h2>
          <p className="card-subtitle">{graph ? `${graph.table_count || graph.nodes?.length || 0} tables · ${graph.relationship_count || graph.edges?.length || 0} FK relationships` : 'No data'}</p>
        </div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <div style={{ display: 'flex', background: 'var(--muted)', borderRadius: '6px', overflow: 'hidden', border: '1px solid var(--border)' }}>
            <button onClick={() => handleViewToggle('graph')} style={{ padding: '6px 14px', fontSize: '0.8rem', fontWeight: 600, border: 'none', cursor: 'pointer', background: view === 'graph' ? 'var(--primary)' : 'transparent', color: view === 'graph' ? 'white' : 'var(--muted-foreground)' }}>Graph</button>
            <button onClick={() => handleViewToggle('er')} style={{ padding: '6px 14px', fontSize: '0.8rem', fontWeight: 600, border: 'none', cursor: 'pointer', background: view === 'er' ? 'var(--primary)' : 'transparent', color: view === 'er' ? 'white' : 'var(--muted-foreground)' }}>ER Diagram</button>
          </div>
          <button className="primary-btn" onClick={() => { loadGraph(); if (view === 'er') loadER(); }} style={{ marginLeft: '4px' }}>
            <RefreshCw size={14} /> Refresh
          </button>
        </div>
      </div>

      {error ? (
        <div className="empty-state" style={{ color: '#ef4444' }}>
          <p>Failed to build lineage graph: {error}</p>
          <p>Ensure a database is connected and schema is loaded.</p>
        </div>
      ) : view === 'er' ? (
        /* ── ER Diagram View ── */
        erLoading ? <div className="loading-state">Generating ER diagram...</div> : erDiagram ? (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <span style={{ fontSize: '0.85em', color: 'var(--muted-foreground)' }}>{erDiagram.table_count} tables · {erDiagram.relationship_count} relationships</span>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button className="secondary-btn" onClick={() => setShowCode(!showCode)} style={{ fontSize: '0.8rem', padding: '4px 12px' }}>
                  {showCode ? <><BarChart2 size={12} className="inline-icon" /> Show Diagram</> : <><FileText size={12} className="inline-icon" /> Show Code</>}
                </button>
                <button className="secondary-btn" onClick={() => { navigator.clipboard.writeText(erDiagram.mermaid); }} style={{ fontSize: '0.8rem', padding: '4px 12px' }}>
                  <FileText size={12} className="inline-icon" /> Copy Mermaid
                </button>
              </div>
            </div>
            {showCode ? (
              <div style={{ background: '#0f172a', color: '#e2e8f0', padding: '20px', borderRadius: '8px', fontFamily: 'monospace', fontSize: '0.8rem', lineHeight: 1.6, overflowX: 'auto', whiteSpace: 'pre', maxHeight: '600px', overflow: 'auto' }}>
                {erDiagram.mermaid}
              </div>
            ) : (
              <div ref={mermaidRef} style={{ background: '#0f172a', padding: '24px', borderRadius: '8px', overflow: 'auto', minHeight: '300px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <div className="loading-state" style={{ color: '#94a3b8' }}>Rendering diagram...</div>
              </div>
            )}
          </div>
        ) : <div className="empty-state">Failed to load ER diagram.</div>
      ) : (
        /* ── Graph View ── */
        !graph?.nodes?.length ? (
          <div className="empty-state">
            No tables found. Connect a database and load the schema first.
          </div>
        ) : (
          <div className="lineage-graph-container" style={{ background: 'var(--muted)', padding: '24px', borderRadius: '8px', border: '1px solid var(--border)', display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '16px' }}>
            {graph.nodes.map(node => (
              <div key={node.id} style={{ background: 'var(--card)', padding: '16px', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', border: '1px solid var(--border)' }}>
                <div style={{ fontWeight: 600, color: 'var(--primary)', marginBottom: '4px', fontSize: '1em' }}>{node.label}</div>
                <div className="artifact-meta">Schema: {node.schema} · Rows: {typeof node.row_count === 'number' ? node.row_count.toLocaleString() : node.row_count} · Cols: {node.column_count || '?'}</div>
                <div style={{ marginTop: '12px' }}>
                  <div style={{ fontSize: '0.8em', color: 'var(--muted-foreground)', fontWeight: 600, marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>References →</div>
                  {graph.edges.filter(e => e.source === node.id).map((e, i) => (
                    <div key={i} style={{ fontSize: '0.875em', color: 'var(--foreground)', padding: '4px 0', borderBottom: '1px solid var(--border)' }}>
                      → {e.target} <span style={{ color: 'var(--muted-foreground)', fontSize: '0.85em' }}>({e.label})</span>
                    </div>
                  ))}
                  {graph.edges.filter(e => e.target === node.id).map((e, i) => (
                    <div key={`in-${i}`} style={{ fontSize: '0.875em', color: 'var(--foreground)', padding: '4px 0', borderBottom: '1px solid var(--border)' }}>
                      ← {e.source} <span style={{ color: 'var(--muted-foreground)', fontSize: '0.85em' }}>({e.label})</span>
                    </div>
                  ))}
                  {graph.edges.filter(e => e.source === node.id || e.target === node.id).length === 0 && (
                    <div style={{ fontSize: '0.875em', color: 'var(--muted-foreground)', fontStyle: 'italic' }}>No references</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════ */
/*  GITHUB PANEL (localStorage-based)                                          */
/* ═══════════════════════════════════════════════════════════════════════════ */
function GitHubPanel() {
  const [prs, setPrs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [scanResult, setScanResult] = useState(null);

  const token = localStorage.getItem('nf_github_token') || '';
  const repo = localStorage.getItem('nf_github_repo') || '';
  const configured = Boolean(token && repo);

  useEffect(() => {
    if (configured) {
      loadPrs();
      scanRepo();
    } else {
      setLoading(false);
    }
  }, []);

  async function loadPrs() {
    setLoading(true);
    setError('');
    try {
      const params = new URLSearchParams({ token, repo, state: 'all', per_page: '15' });
      const r = await fetch(`${API}/api/github/prs?${params}`);
      const d = await r.json();
      if (d.error) setError(d.error);
      setPrs(d.prs || []);
    } catch (e) { setError(e.message); }
    setLoading(false);
  }

  async function scanRepo() {
    try {
      const params = new URLSearchParams({ token, repo });
      const r = await fetch(`${API}/api/github/scan?${params}`);
      const d = await r.json();
      if (!d.error) setScanResult(d);
    } catch (e) { console.error('Failed to scan repo', e); }
  }

  if (loading) return <div className="loading-state">Loading GitHub integration...</div>;

  return (
    <div className="card">
      <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 className="card-title">GitHub Integration</h2>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          {configured ? (
            <span className="status-badge connected"><span className="status-dot"></span> {repo}</span>
          ) : (
            <span className="status-badge disconnected"><span className="status-dot"></span> Not Configured</span>
          )}
          {scanResult && (
            <span className="status-badge connected" style={{ background: 'rgba(16, 185, 129, 0.1)', color: '#10b981', border: '1px solid rgba(16, 185, 129, 0.3)' }}>
              <FileText size={12} style={{ marginRight: '4px' }} /> {scanResult.file_count} files indexed
            </span>
          )}
          {configured && (
            <button className="primary-btn" onClick={() => { loadPrs(); scanRepo(); }} style={{ marginLeft: '8px' }}>
              <RefreshCw size={14} /> Refresh
            </button>
          )}
        </div>
      </div>

      {!configured ? (
        <div className="empty-state">
          <p>GitHub Integration not configured.</p>
          <p>Go to <strong>Settings</strong> and enter your GitHub <strong>Repository</strong> (owner/repo) and <strong>Personal Access Token</strong> to enable PR monitoring and code-aware AI chat.</p>
        </div>
      ) : error ? (
        <div className="empty-state" style={{ color: '#ef4444' }}>
          <p>Error loading PRs: {error}</p>
        </div>
      ) : (
        <div>
          {scanResult && (
            <div style={{ marginBottom: '16px', padding: '16px', background: 'rgba(16, 185, 129, 0.05)', borderRadius: '8px', border: '1px solid rgba(16, 185, 129, 0.2)' }}>
              <h3 style={{ margin: '0 0 8px 0', color: '#10b981', fontSize: '1em', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <CheckCircle2 size={16} /> Code Context Active
              </h3>
              <p style={{ margin: 0, color: 'var(--muted-foreground)', fontSize: '0.9em', lineHeight: 1.5 }}>
                {scanResult.file_count} code files from <strong>{repo}</strong> have been indexed. The AI Chat can now reference your codebase to answer questions like <em>"which tables are used in the code"</em> or <em>"which tables are not needed"</em>.
              </p>
            </div>
          )}

          <div style={{ marginBottom: '24px', padding: '16px', background: 'var(--muted)', borderRadius: '8px', border: '1px solid var(--border)' }}>
            <h3 style={{ margin: '0 0 8px 0', color: 'var(--primary)', fontSize: '1em', display: 'flex', alignItems: 'center', gap: '8px' }}><Info size={16} /> Webhook Auto-Generation</h3>
            <p style={{ margin: 0, color: 'var(--muted-foreground)', fontSize: '0.95em', lineHeight: 1.5 }}>
              Neuro-Fabric listens for merged Pull Requests onto the <strong>dev</strong> branch. When a PR is merged, we scan for modified `.sql` and `.py` files and automatically regenerate AI documentation for affected tables.
            </p>
          </div>

          <h3 className="section-title">Recent Pull Requests</h3>
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>PR #</th>
                  <th>Title</th>
                  <th>Status</th>
                  <th>Author</th>
                  <th>Updated</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {prs.map(pr => (
                  <tr key={pr.number}>
                    <td className="mono">#{pr.number}</td>
                    <td style={{ fontWeight: 500 }}>{pr.title}</td>
                    <td>
                      <span style={{
                        padding: '4px 8px', borderRadius: '4px', fontSize: '0.85em', fontWeight: 500,
                        backgroundColor: pr.merged ? '#dcfce7' : pr.state === 'closed' ? '#fee2e2' : '#dbeafe',
                        color: pr.merged ? '#166534' : pr.state === 'closed' ? '#991b1b' : '#1e40af'
                      }}>
                        {pr.merged ? 'Merged' : pr.state}
                      </span>
                    </td>
                    <td>{pr.author}</td>
                    <td>{new Date(pr.updated_at).toLocaleDateString()}</td>
                    <td>
                      <a href={pr.url} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--primary)', textDecoration: 'none', fontWeight: 500 }}>View on GitHub</a>
                    </td>
                  </tr>
                ))}
                {!prs.length && (
                  <tr><td colSpan="6" style={{ textAlign: 'center', padding: '32px', color: 'var(--muted-foreground)' }}>No recent PRs found for {repo}</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════ */
/*  SETTINGS PANEL (SaaS Config)                                             */
/* ═══════════════════════════════════════════════════════════════════════════ */
function SettingsPanel({ onConnect, connected, currentEngine }) {
  const [dbUrl, setDbUrl] = useState('');
  const [gitToken, setGitToken] = useState(localStorage.getItem('nf_github_token') || '');
  const [gitRepo, setGitRepo] = useState(localStorage.getItem('nf_github_repo') || '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Example connections
  const examples = {
    duckdb: 'duckdb:///data/neuro_fabric.duckdb',
    supabase: 'postgresql://postgres:password@db.id.supabase.co:5432/postgres',
  };

  async function handleSave(e) {
    e.preventDefault();
    setSaving(true);
    setError('');
    setSuccess('');

    // Persist GitHub settings to localStorage
    localStorage.setItem('nf_github_token', gitToken);
    localStorage.setItem('nf_github_repo', gitRepo);

    try {
      const payload = {
        db_url: dbUrl,
      };

      const r = await fetch(`${API}/api/settings/connect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const d = await r.json();

      if (d.connected) {
        setSuccess(d.message + (gitRepo ? ` · GitHub: ${gitRepo}` : ''));
        onConnect(true, d.engine);
      } else if (!dbUrl) {
        setSuccess('Settings saved.' + (gitRepo ? ` GitHub: ${gitRepo}` : ''));
        onConnect(false, '');
      } else {
        setError(d.message);
      }
    } catch (err) {
      setError(err.message);
    }
    setSaving(false);
  }

  async function handleDisconnect() {
    setDbUrl('');
    // Trigger empty save to clear DB but keep other settings
    setSaving(true);
    try {
      await fetch(`${API}/api/settings/connect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ db_url: '' })
      });
      onConnect(false, '');
    } catch (e) { console.error(e); }
    setSaving(false);
  }

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto' }}>
      <div className="section-header">
        <h2>Workspace Settings</h2>
        <p>Configure your databases, graph services, and source control integrations.</p>
      </div>

      <form onSubmit={handleSave}>

        {/* Database Connection */}
        <div className="card">
          <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between' }}>
            <div>
              <h3 className="card-title">Database Connection</h3>
              <p className="card-subtitle">Connect your PostgreSQL or Snowflake instance.</p>
            </div>
            {connected && (
              <span className="status-badge connected"><span className="status-dot"></span> {currentEngine.toUpperCase()} CONNECTED</span>
            )}
          </div>

          <div className="input-group">
            <label className="input-label">Connection String (URI)</label>
            <input
              type="text"
              className="text-input"
              placeholder="e.g. postgresql://user:pass@host:5432/db"
              value={dbUrl}
              onChange={e => setDbUrl(e.target.value)}
            />
            <div style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '6px', display: 'flex', gap: '8px' }}>
              <span>Examples: </span>
              <button type="button" style={{ background: 'none', border: 'none', color: '#6366f1', cursor: 'pointer', textDecoration: 'underline' }} onClick={() => setDbUrl(examples.supabase)}>Supabase</button>
            </div>
          </div>

          {connected && (
            <button type="button" className="secondary-btn" onClick={handleDisconnect} style={{ color: '#ef4444', borderColor: '#fca5a5' }}>
              Disconnect Database
            </button>
          )}
        </div>



        {/* GitHub Webhook */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">GitHub Integration</h3>
            <p className="card-subtitle">Connect repository to auto-sync AI docs on PR merges.</p>
          </div>
          <div className="grid-2">
            <div className="input-group">
              <label className="input-label">Repository Name</label>
              <input type="text" className="text-input" placeholder="owner/repo" value={gitRepo} onChange={e => setGitRepo(e.target.value)} />
            </div>
            <div className="input-group">
              <label className="input-label">Personal Access Token</label>
              <input type="password" className="text-input" placeholder="ghp_••••••••" value={gitToken} onChange={e => setGitToken(e.target.value)} />
            </div>
          </div>
        </div>

        {/* Actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '40px' }}>
          <button type="submit" className="primary-btn" disabled={saving}>
            {saving ? 'Testing & Saving...' : 'Save & Connect'}
          </button>

          {error && <span style={{ color: '#ef4444', fontSize: '0.875rem', fontWeight: 500 }}><XCircle size={16} className="inline-icon" /> {error}</span>}
          {success && <span style={{ color: '#10b981', fontSize: '0.875rem', fontWeight: 500 }}><CheckCircle2 size={16} className="inline-icon" /> {success}</span>}
        </div>
      </form>
    </div>
  );
}
