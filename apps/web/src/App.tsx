import { useEffect, useMemo, useState } from "react";
import { loadDashboard } from "./api";
import { demoData } from "./data";
import type { DashboardData, Deployment, DORASummary } from "./types";

function formatDuration(seconds: number | null): string {
  if (seconds === null) return "—";
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  return `${(seconds / 3600).toFixed(1)}h`;
}

function formatRelative(date: string): string {
  const hours = Math.max(1, Math.round((Date.now() - new Date(date).getTime()) / 3_600_000));
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

function MetricCard({ label, value, note, detail, tone }: { label: string; value: string; note: string; detail: string; tone: string }) {
  return (
    <article className={`metric-card ${tone}`}>
      <div className="metric-topline"><span>{label}</span><span className="metric-detail">{detail}</span></div>
      <strong>{value}</strong>
      <div className="metric-note"><span className="trend-up">↗</span>{note}</div>
    </article>
  );
}

function Sparkline({ values, label }: { values: number[]; label: string }) {
  const max = Math.max(...values, 1);
  const points = values.map((value, index) => `${(index / Math.max(values.length - 1, 1)) * 100},${92 - (value / max) * 76}`).join(" ");
  return (
    <svg className="sparkline" viewBox="0 0 100 100" preserveAspectRatio="none" role="img" aria-label={label}>
      <polyline points={points} fill="none" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

function StatusMark({ status }: { status: Deployment["status"] }) {
  const label = status === "succeeded" ? "Healthy" : status === "running" ? "In progress" : status === "rolled_back" ? "Rolled back" : "Failed";
  return <span className={`status-mark ${status}`}><span aria-hidden="true" />{label}</span>;
}

function EnvironmentMatrix({ deployments }: { deployments: Deployment[] }) {
  const matrix = [
    { name: "checkout-api", owner: "commerce-platform", production: "succeeded", staging: "running", last: "12m ago" },
    { name: "edge-web", owner: "experience", production: "succeeded", staging: "succeeded", last: "2h ago" },
    { name: "ledger-worker", owner: "platform", production: "succeeded", staging: "failed", last: "5h ago" },
  ];
  const hasFailure = deployments.some((deployment) => deployment.status === "failed");
  return (
    <section className="panel matrix-panel" aria-labelledby="matrix-title">
      <div className="panel-heading"><div><p className="eyebrow">Service catalog</p><h2 id="matrix-title">Environment matrix</h2></div><button className="quiet-button" type="button">View catalog <span aria-hidden="true">↗</span></button></div>
      <div className="matrix-table-wrap">
        <table className="matrix-table"><caption className="sr-only">Service health by environment</caption><thead><tr><th scope="col">Service</th><th scope="col">Owner</th><th scope="col">Production</th><th scope="col">Staging</th><th scope="col">Last change</th></tr></thead><tbody>
          {matrix.map((row) => <tr key={row.name}><th scope="row"><span className="service-glyph">{row.name.slice(0, 1).toUpperCase()}</span><span>{row.name}</span></th><td>{row.owner}</td><td><StatusMark status={row.production as Deployment["status"]} /></td><td><StatusMark status={row.staging as Deployment["status"]} /></td><td className="muted-cell">{row.last}</td></tr>)}
        </tbody></table>
      </div>
      {hasFailure && <div className="matrix-callout"><span className="callout-icon">!</span><span><strong>One active signal needs attention.</strong> Ledger Worker is failing its staging verification.</span><button type="button">Open signal</button></div>}
    </section>
  );
}

function DeploymentTable({ deployments }: { deployments: Deployment[] }) {
  return (
    <section className="panel deployments-panel" aria-labelledby="deployments-title">
      <div className="panel-heading"><div><p className="eyebrow">Change stream</p><h2 id="deployments-title">Recent deployments</h2></div><button className="quiet-button" type="button">Export CSV <span aria-hidden="true">↓</span></button></div>
      <div className="deployment-table-wrap"><table className="deployment-table"><caption className="sr-only">Recent deployment events</caption><thead><tr><th scope="col">Service</th><th scope="col">Revision</th><th scope="col">Environment</th><th scope="col">Result</th><th scope="col">Lead time</th><th scope="col"><span className="sr-only">When</span></th></tr></thead><tbody>
        {deployments.slice(0, 7).map((deployment) => <tr key={deployment.id}><th scope="row"><span className="service-glyph compact">{deployment.service_slug.slice(0, 1).toUpperCase()}</span>{deployment.service_slug}</th><td className="revision">{deployment.revision.slice(0, 7)}</td><td><span className={`environment ${deployment.environment}`}>{deployment.environment}</span></td><td><StatusMark status={deployment.status} /></td><td className="mono-cell">{formatDuration(deployment.lead_time_seconds)}</td><td className="muted-cell">{formatRelative(deployment.created_at)}</td></tr>)}
      </tbody></table></div>
    </section>
  );
}

function HealthGauge({ value, label, inverse = false }: { value: number; label: string; inverse?: boolean }) {
  const good = inverse ? value <= 10 : value >= 90;
  return <div className="gauge-row"><div className="gauge-label"><span>{label}</span><strong>{value.toFixed(1)}%</strong></div><div className="gauge-track"><span className={good ? "good" : "watch"} style={{ width: `${Math.min(100, Math.max(4, inverse ? 100 - value * 2 : value))}%` }} /></div></div>;
}

function App() {
  const [selectedService, setSelectedService] = useState<string | null>(null);
  const [data, setData] = useState<DashboardData>(demoData);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    loadDashboard(selectedService).then((next) => { if (active) { setData(next); setError(null); } }).catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "Unable to load API"); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [selectedService]);

  const metrics: DORASummary = data.dora.summary;
  const successfulTrend = useMemo(() => data.dora.trend.map((point) => point.deployments), [data.dora.trend]);
  const healthScore = Math.max(0, Math.min(100, 100 - metrics.change_fail_rate_percent * 2 - metrics.deployment_rework_rate_percent));

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><div className="brand-mark"><span /><span /><span /></div><span>DeployLedger</span></div>
        <div className="workspace-switcher"><span className="workspace-label">Workspace</span><button type="button" className="workspace-button"><span className="workspace-avatar">A</span><span>Acme Platform</span><span aria-hidden="true" className="chevron">⌄</span></button></div>
        <nav aria-label="Primary navigation"><p className="nav-label">Operate</p><a className="nav-item active" href="#overview"><span className="nav-icon">◈</span>Overview</a><a className="nav-item" href="#services"><span className="nav-icon">▦</span>Services<span className="nav-count">12</span></a><a className="nav-item" href="#deployments"><span className="nav-icon">↯</span>Deployments</a><a className="nav-item" href="#signals"><span className="nav-icon">◉</span>Signals<span className="nav-count alert">1</span></a><p className="nav-label secondary">Improve</p><a className="nav-item" href="#metrics"><span className="nav-icon">⌁</span>DORA metrics</a><a className="nav-item" href="#audit"><span className="nav-icon">≡</span>Audit trail</a></nav>
        <div className="sidebar-bottom"><div className="system-status"><span className="pulse-dot" /><div><strong>All systems operational</strong><span>Updated just now</span></div></div><a className="profile-link" href="https://github.com/kyan9400" target="_blank" rel="noreferrer"><span className="profile-avatar">HA</span><span><strong>Hassan Ak</strong><small>Platform engineer</small></span><span aria-hidden="true">⋯</span></a></div>
      </aside>
      <main className="main-content" id="overview">
        <header className="topbar"><div className="breadcrumb"><span className="breadcrumb-muted">Workspace</span><span>/</span><strong>Release operations</strong></div><div className="topbar-actions"><span className={`data-mode ${data.demo ? "demo" : "live"}`}><span />{data.demo ? "Demo data" : "Live API"}</span><button className="icon-button" aria-label="Search" type="button">⌕</button><button className="icon-button" aria-label="Notifications" type="button">♧<span className="notification-dot" /></button><button className="top-avatar" type="button" aria-label="Open account menu">HA</button></div></header>
        <div className="content-wrap">
          <section className="hero"><div><p className="eyebrow">Release operations <span className="live-line" /> Last 30 days</p><h1>Move with<br /><em>confidence.</em></h1><p className="hero-copy">A single view of delivery speed, change stability, and the signals that decide whether to ship.</p></div><div className="hero-controls"><label htmlFor="service-filter">Scope</label><select id="service-filter" value={selectedService ?? "all"} onChange={(event) => setSelectedService(event.target.value === "all" ? null : event.target.value)}><option value="all">All services</option>{data.services.map((service) => <option key={service.slug} value={service.slug}>{service.name}</option>)}</select><button className="primary-button" type="button"><span aria-hidden="true">+</span> Record deployment</button></div></section>
          {error && <div className="error-banner" role="alert">{error}. Showing the last known demo snapshot.</div>}
          <section className="metric-grid" id="metrics" aria-label="DORA metrics"><MetricCard label="Deploy frequency" value={`${metrics.deployment_frequency_per_week.toFixed(1)} / wk`} note="18% above your 30d baseline" detail="THROUGHPUT" tone="amber" /><MetricCard label="Change lead time" value={formatDuration(metrics.change_lead_time_p50_seconds)} note="p50 · 12m faster than last month" detail="THROUGHPUT" tone="blue" /><MetricCard label="Change fail rate" value={`${metrics.change_fail_rate_percent.toFixed(1)}%`} note="Target < 10%" detail="STABILITY" tone="coral" /><MetricCard label="Failed deploy recovery" value={formatDuration(metrics.failed_deployment_recovery_p50_seconds)} note="p50 · within team target" detail="STABILITY" tone="green" /></section>
          <div className="dashboard-grid"><section className="panel throughput-panel"><div className="panel-heading"><div><p className="eyebrow">Delivery throughput</p><h2>Deployment rhythm</h2></div><div className="panel-legend"><span><i className="legend-bar" />Successful</span><span><i className="legend-failure" />Failed</span><button className="period-button" type="button">30 days <span>⌄</span></button></div></div><div className="chart-wrap"><div className="chart-y-axis"><span>4</span><span>3</span><span>2</span><span>1</span><span>0</span></div><div className="chart"><div className="chart-grid-lines"><i /><i /><i /><i /><i /></div><div className="bar-chart">{data.dora.trend.map((point) => <div className="bar-column" key={point.date}><span className="bar-value" style={{ height: `${Math.min(88, point.deployments * 20)}%` }} />{point.failures > 0 && <span className="failure-marker" />} </div>)}</div><div className="chart-labels"><span>30d ago</span><span>20d ago</span><span>10d ago</span><span>Today</span></div></div></div><div className="throughput-footer"><div><span className="footer-number">{data.dora.trend.reduce((sum, point) => sum + point.deployments, 0)}</span><span>successful deployments</span></div><div><span className="footer-number accent">{data.dora.trend.reduce((sum, point) => sum + point.failures, 0)}</span><span>needed intervention</span></div><div className="sparkline-box"><Sparkline values={successfulTrend} label="Successful deployments trend" /></div></div></section><section className="panel health-panel" id="signals"><div className="panel-heading"><div><p className="eyebrow">Stability signals</p><h2>Release health</h2></div><span className="health-score"><span>{Math.round(healthScore)}</span>/100</span></div><div className="health-ring"><div className="ring-outer"><div className="ring-inner"><strong>{Math.round(healthScore)}<small>%</small></strong><span>healthy</span></div></div></div><div className="health-gauges"><HealthGauge label="Change success" value={100 - metrics.change_fail_rate_percent} /><HealthGauge label="Planned work" value={100 - metrics.deployment_rework_rate_percent} /><HealthGauge label="Recovery within target" value={88} /></div><button className="text-button" type="button">Open reliability report <span aria-hidden="true">→</span></button></section></div>
          <EnvironmentMatrix deployments={data.deployments} /><DeploymentTable deployments={data.deployments} />
          <footer className="footer-note"><span>DeployLedger v0.1</span><span>Built for teams that ship responsibly.</span><a href="https://github.com/kyan9400/deployledger" target="_blank" rel="noreferrer">View source <span aria-hidden="true">↗</span></a></footer>
        </div>
        {loading && <div className="loading-bar" aria-label="Refreshing data" />}
      </main>
    </div>
  );
}

export default App;
