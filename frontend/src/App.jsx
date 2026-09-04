import { useState } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const demos = [
  ['TXN-DEMO-001', 'Normal Settlement'], ['TXN-DEMO-002', 'Bank Delay'],
  ['TXN-DEMO-003', 'Missing Bank Record'], ['TXN-DEMO-004', 'Amount Mismatch'],
  ['TXN-DEMO-005', 'Missing Ledger'], ['TXN-DEMO-006', 'Settlement Not Initiated'],
  ['TXN-DEMO-007', 'Duplicate Settlement'],
];

const statusTone = (value = '') => {
  const text = value.toLowerCase();
  if (text.includes('complete') || text === 'captured' || text === 'settled' || text === 'posted') return 'success';
  if (text.includes('missing') || text.includes('mismatch') || text.includes('duplicate') || text.includes('conflict')) return 'danger';
  if (text.includes('delay') || text.includes('pending') || text.includes('accrued') || text.includes('initiated')) return 'warning';
  return 'neutral';
};
const humanize = (value = '') => value.replaceAll('_', ' ').replace(/\b\w/g, char => char.toUpperCase());

function App() {
  const [view, setView] = useState('investigate');
  const [transactionId, setTransactionId] = useState('');
  const [result, setResult] = useState(null);
  const [explanation, setExplanation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [explanationLoading, setExplanationLoading] = useState(false);
  const [error, setError] = useState('');

  async function investigate(id = transactionId) {
    const normalizedId = id.trim();
    if (!normalizedId) return setError('Enter a transaction ID to begin an investigation.');
    setTransactionId(normalizedId); setLoading(true); setError(''); setResult(null); setExplanation(null); setView('investigate');
    try {
      const response = await fetch(`${API_BASE}/investigations/${encodeURIComponent(normalizedId)}`);
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || 'Investigation could not be completed.');
      setResult(body);
    } catch (requestError) { setError(requestError.message || 'Unable to reach the investigation service.'); }
    finally { setLoading(false); }
  }

  async function generateExplanation() {
    if (!result) return;
    setExplanationLoading(true); setError('');
    try {
      const response = await fetch(`${API_BASE}/investigations/${encodeURIComponent(result.transaction_id)}/explanation`, { method: 'POST' });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || 'Explanation could not be generated.');
      setExplanation(body.explanation);
    } catch (requestError) { setError(requestError.message || 'Unable to reach the AI explanation service.'); }
    finally { setExplanationLoading(false); }
  }

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><span className="brand-mark">S</span><span>SettleTrace</span></div>
      <p className="sidebar-kicker">Settlement operations</p>
      <nav className="navigation" aria-label="Primary navigation">
        <button className={view === 'investigate' ? 'nav-item active' : 'nav-item'} onClick={() => setView('investigate')}><i>⌕</i> Investigate</button>
        <button className={view === 'how' ? 'nav-item active' : 'nav-item'} onClick={() => setView('how')}><i>◈</i> How It Works</button>
        <button className={view === 'demos' ? 'nav-item active' : 'nav-item'} onClick={() => setView('demos')}><i>▤</i> Demo Cases</button>
      </nav>
      <div className="sources"><p className="eyebrow">Data sources</p><p className="source"><b className="dot" />Gateway <span>Ready</span></p><p className="source"><b className="dot" />Bank <span>Ready</span></p><p className="source"><b className="dot" />Ledger <span>Ready</span></p></div>
      <p className="sidebar-footer">Verified reconciliation workspace</p>
    </aside>
    <main className="main"><header className="topbar"><div><p className="eyebrow">Operations / Settlement investigation</p><h1>{view === 'how' ? 'How the system works' : view === 'demos' ? 'Demo cases' : 'Investigation workspace'}</h1></div><div className="verified"><span>✓</span> Deterministic first</div></header>
      {view === 'investigate' && <InvestigationView {...{transactionId, setTransactionId, investigate, result, explanation, loading, explanationLoading, generateExplanation, error}} />}
      {view === 'how' && <HowItWorks />}
      {view === 'demos' && <DemoCases onSelect={investigate} />}
    </main>
  </div>;
}

function InvestigationView({ transactionId, setTransactionId, investigate, result, explanation, loading, explanationLoading, generateExplanation, error }) {
  return <>
    <section className={result ? 'search-panel compact' : 'search-panel'}><div><p className="eyebrow">Transaction lookup</p><h2>{result ? result.transaction_id : 'Investigate a Transaction'}</h2>{!result && <p>Trace settlement evidence across Gateway, Bank and Ledger.</p>}</div><form onSubmit={event => { event.preventDefault(); investigate(); }}><label htmlFor="transaction-id">Transaction ID</label><div className="input-row"><input id="transaction-id" value={transactionId} onChange={event => setTransactionId(event.target.value)} placeholder="e.g. TXN-DEMO-004" /><button className="primary" disabled={loading}>{loading ? 'Investigating…' : 'Investigate'}</button></div></form></section>
    {error && <div className="alert" role="alert">{error}</div>}
    {!result && !loading && <section className="empty-state"><div className="empty-icon">⌕</div><h2>Start with a transaction ID</h2><p>Enter a transaction ID to reconcile its Gateway, Bank and Ledger records.</p><div className="source-flow"><span>Gateway</span><b>+</b><span>Bank</span><b>+</b><span>Ledger</span><b>→</b><strong>Verified result</strong></div></section>}
    {result && <Workspace {...{result, explanation, explanationLoading, generateExplanation}} />}
  </>;
}

function Workspace({ result, explanation, explanationLoading, generateExplanation }) {
  const tone = statusTone(result.settlement_status);
  return <div className="workspace">
    <section className="result-banner"><div><p className="eyebrow">Investigation result <span className="verified-note">Determined from Gateway, Bank and Ledger records</span></p><h2>{humanize(result.settlement_status)}</h2><p className="cause">Root cause: <strong>{humanize(result.root_cause)}</strong></p></div><Confidence value={result.confidence} tone={tone} /></section>
    <section><div className="section-heading"><div><p className="eyebrow">Record trace</p><h2>Source status</h2></div><span className="legend">Text labels accompany every status</span></div><div className="status-grid"><StatusCard name="Gateway" values={result.gateway_status} /><StatusCard name="Bank" values={result.bank_status} /><StatusCard name="Ledger" values={result.ledger_status} /></div></section>
    <div className="detail-grid"><section className="panel"><p className="eyebrow">Detected issues</p><h2>Discrepancies</h2>{result.discrepancies.length ? <div className="chips">{result.discrepancies.map(item => <span className={`chip ${statusTone(item)}`} key={item}>{humanize(item)}</span>)}</div> : <p className="quiet">No discrepancies detected.</p>}</section><section className="panel action-panel"><p className="eyebrow">Next step</p><h2>Recommended action</h2><p>{result.recommended_action}</p></section></div>
    <section className="panel evidence"><p className="eyebrow">Verified record detail</p><h2>Evidence</h2><ul>{result.evidence.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ul></section>
    <section className="ai-panel"><div className="ai-heading"><div><p className="eyebrow">AI-assisted explanation</p><h2>Natural-language explanation</h2><p>Generated only from the verified investigation result above.</p></div>{!explanation && <button className="secondary" disabled={explanationLoading} onClick={generateExplanation}>{explanationLoading ? 'Generating…' : 'Generate Explanation'}</button>}</div>{explanation && <div className="explanation-grid"><Explanation label="Summary" text={explanation.summary} /><Explanation label="What happened" text={explanation.what_happened} /><Explanation label="Why" text={explanation.why} /><Explanation label="Recommended action" text={explanation.recommended_action} /><Explanation label="Uncertainty" text={explanation.uncertainty} /><div><p className="explain-label">Evidence</p><ul>{explanation.evidence.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ul></div></div>}</section>
  </div>;
}

function StatusCard({ name, values }) { const tone = statusTone(values.join(' ')); return <article className="status-card"><div className="card-title"><span className={`status-dot ${tone}`} />{name}</div>{values.map(value => <span className={`status-label ${statusTone(value)}`} key={value}>{humanize(value)}</span>)}</article>; }
function Confidence({ value, tone }) { return <div className="confidence"><p>Confidence</p><strong>{Math.round(value * 100)}%</strong><div className="meter"><span className={tone} style={{ width: `${value * 100}%` }} /></div><small>From deterministic rules</small></div>; }
function Explanation({ label, text }) { return <div><p className="explain-label">{label}</p><p>{text}</p></div>; }

function HowItWorks() { const steps = [['01', 'Transaction', 'Enter the transaction ID.'], ['02', 'Trace', 'Find corresponding Gateway, Bank and Ledger records.'], ['03', 'Reconcile', 'Compare statuses, amounts, IDs and relevant timestamps.'], ['04', 'Detect', 'Identify missing, duplicate or conflicting evidence.'], ['05', 'Investigate', 'Determine settlement state, confidence and recommended action.'], ['06', 'Explain', 'Use AI to turn the verified result into a concise explanation.']]; return <div className="info-page"><p className="page-intro">A transparent, evidence-led workflow for settlement support.</p><div className="workflow">{steps.map(([number, title, description]) => <article key={number}><span>{number}</span><h2>{title}</h2><p>{description}</p></article>)}</div><div className="principles"><article><b>Deterministic First</b><p>Code determines what happened before any AI explanation is requested.</p></article><article><b>Evidence Based</b><p>Every conclusion is grounded in the Gateway, Bank and Ledger record trace.</p></article><article><b>Honest Uncertainty</b><p>Missing or conflicting evidence is surfaced instead of being explained away.</p></article></div></div>; }
function DemoCases({ onSelect }) { return <div className="info-page"><p className="page-intro">Shortcuts to seeded cases. Each selection always runs the live backend investigation.</p><div className="demo-list">{demos.map(([id, label]) => <button key={id} onClick={() => onSelect(id)}><span><b>{id}</b><small>{label}</small></span><i>→</i></button>)}</div></div>; }

export default App;
