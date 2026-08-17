/**
 * Dashboard application — view logic for docs/dashboard/index.html.
 *
 * Consumes the synced mirrors of the canonical tested modules:
 *   - ./client.js     (site/api/client.js — fetcher, fallback mock)
 *   - ./dashboard.js  (site/monitoring/dashboard.js — risk levels, formatting)
 *
 * States: loading (skeleton) -> real data | mock fallback (labeled).
 * Scope v1: overview (risk instrument, stats, alerts) + trend (SVG chart).
 */

import { fetchLatestSnapshot, fetchRecentSnapshots } from "./client.js";
import {
  getRiskLevel,
  getRiskColor,
  formatTimestamp,
  summarizeAggregated,
} from "./dashboard.js";

const REFRESH_MS = 5 * 60 * 1000; // auto-refresh every 5 min

const els = {
  statusBadge: () => document.getElementById("mode-badge"),
  lastUpdate: () => document.getElementById("last-update"),
  refreshBtn: () => document.getElementById("refresh-btn"),
  gaugeValue: () => document.getElementById("gauge-value"),
  gaugeLevel: () => document.getElementById("gauge-level"),
  gaugeMarker: () => document.getElementById("gauge-marker"),
  gaugeReadout: () => document.getElementById("gauge-readout"),
  chart: () => document.getElementById("trend-chart"),
  chartEmpty: () => document.getElementById("trend-empty"),
  statErrors: () => document.getElementById("stat-errors"),
  statSlow: () => document.getElementById("stat-slow"),
  statLogs: () => document.getElementById("stat-logs"),
  statValidation: () => document.getElementById("stat-validation"),
  alertsList: () => document.getElementById("alerts-list"),
  alertsEmpty: () => document.getElementById("alerts-empty"),
  alertsCount: () => document.getElementById("alerts-count"),
  alertsCaption: () => document.getElementById("alerts-caption"),
  pageStatus: () => document.getElementById("page-status"),
  skeleton: () => document.getElementById("skeleton"),
  content: () => document.getElementById("content"),
};

const THRESHOLDS = [0.4, 0.7]; // WARNING / CRITICAL (matches dashboard.js)

let isFirstRender = true;

/* ---------------------------------------------------------------- helpers */

function fmtNumber(value) {
  return Number(value ?? 0).toLocaleString("pt-BR");
}

function fmtPct(value) {
  return (value * 100).toLocaleString("pt-BR", { maximumFractionDigits: 1 });
}

function severityColor(severity) {
  if (severity === "CRITICAL") return "#ef4444";
  if (severity === "WARNING") return "#f59e0b";
  return "#2fbf71";
}

function isReal(snapshot) {
  return snapshot && snapshot.mode === "real";
}

function setText(node, value) {
  if (node) node.textContent = value;
}

/* ------------------------------------------------------------- skeleton */

function showSkeleton() {
  els.skeleton()?.classList.remove("hidden");
  els.content()?.classList.add("hidden");
}

function hideSkeleton() {
  els.skeleton()?.classList.add("hidden");
  els.content()?.classList.remove("hidden");
}

/* ---------------------------------------------------------- gauge render */

function renderGauge(snapshot) {
  const risk = Number(snapshot.risk_score ?? 0);
  const level = getRiskLevel(risk);
  const color = getRiskColor(risk);
  const marker = els.gaugeMarker();
  const readout = els.gaugeReadout();

  setText(els.gaugeValue(), fmtPct(risk));
  setText(els.gaugeLevel(), level);

  const pct = Math.min(1, Math.max(0, risk)) * 100;
  if (marker) {
    marker.style.left = `${pct}%`;
    marker.style.setProperty("--marker-color", color);
  }
  if (readout) {
    readout.textContent = `${fmtPct(risk)}%`;
    readout.style.color = color;
  }

  if (isFirstRender && marker && readout) {
    marker.style.transition = "left 0.8s cubic-bezier(0.16, 1, 0.3, 1)";
    readout.style.transition = "opacity 0.6s ease-out";
    readout.style.opacity = "1";
    isFirstRender = false;
  }
}

/* ----------------------------------------------------------- chart render */

function buildChart(snapshots) {
  const container = els.chart();
  if (!container) return;

  const points = snapshots.filter((s) => typeof s.risk_score === "number");
  if (points.length < 2) {
    container.innerHTML = "";
    els.chartEmpty()?.classList.remove("hidden");
    return;
  }
  els.chartEmpty()?.classList.add("hidden");

  const width = container.clientWidth || 720;
  const height = 240;
  const padL = 34;
  const padR = 14;
  const padT = 12;
  const padB = 26;
  const plotW = width - padL - padR;
  const plotH = height - padT - padB;

  const chronological = [...points].reverse();
  const xs = chronological.map((_, i) =>
    padL + (plotW * i) / Math.max(1, chronological.length - 1)
  );

  const yFor = (value) =>
    padT + plotH * (1 - Math.min(1, Math.max(0, value)));

  const linePoints = chronological
    .map((s, i) => `${xs[i].toFixed(1)},${yFor(s.risk_score).toFixed(1)}`)
    .join(" ");

  const areaPoints = `${padL},${padT + plotH} ${linePoints} ${padL + plotW},${padT + plotH}`;

  const bandRects = [
    { from: 0, to: THRESHOLDS[0], color: "#22c55e" },
    { from: THRESHOLDS[0], to: THRESHOLDS[1], color: "#f59e0b" },
    { from: THRESHOLDS[1], to: 1, color: "#ef4444" },
  ]
    .map(
      (b) =>
        `<rect x="${padL}" y="${yFor(b.to)}" width="${plotW}" height="${(yFor(b.from) - yFor(b.to)).toFixed(1)}" fill="${b.color}" fill-opacity="0.07" />`
    )
    .join("");

  const grid = [0.4, 0.7]
    .map(
      (t) =>
        `<line x1="${padL}" y1="${yFor(t)}" x2="${padL + plotW}" y2="${yFor(t)}" stroke="#9aa3b2" stroke-opacity="0.16" stroke-dasharray="3 4" />`
    )
    .join("");

  const xTicks = chronological
    .map((s, i) => {
      if (chronological.length > 12 && i % 3 !== 0 && i !== chronological.length - 1) return "";
      const d = s.timestamp ? new Date(s.timestamp) : null;
      const label = d ? formatTimestamp(d.toISOString()).slice(11, 16) : "";
      return `<text x="${xs[i]}" y="${height - 8}" text-anchor="middle" class="chart-label">${label}</text>`;
    })
    .join("");

  const yLabels = [1, 0.7, 0.4, 0].map(
    (v) =>
      `<text x="${padL - 8}" y="${(yFor(v) + 4).toFixed(1)}" text-anchor="end" class="chart-label">${v}</text>`
  ).join("");

  const last = chronological[chronological.length - 1];
  const lastColor = getRiskColor(last.risk_score);
  const lastX = xs[xs.length - 1];
  const lastY = yFor(last.risk_score);

  const pointDots = chronological
    .map((s, i) => {
      const isLast = i === chronological.length - 1;
      const dotColor = isLast ? lastColor : "#6b7280";
      const r = isLast ? 4.5 : 2.5;
      return `<circle cx="${xs[i].toFixed(1)}" cy="${yFor(s.risk_score).toFixed(1)}" r="${r}" fill="${dotColor}" stroke="#0a0c10" stroke-width="1.2" />`;
    })
    .join("");

  const lastTimestamp = last.timestamp
    ? formatTimestamp(last.timestamp)
    : "";

  container.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Tendência do risco de integração nas últimas ${chronological.length} coletas" class="trend-svg">
      ${bandRects}
      ${grid}
      <polygon points="${areaPoints}" fill="#38bdf8" fill-opacity="0.10" />
      <polyline points="${linePoints}" fill="none" stroke="#9aa3b2" stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round" />
      ${pointDots}
      ${yLabels}
      ${xTicks}
    </svg>
    <span class="chart-caption" id="trend-caption">${lastTimestamp}</span>
  `;
}

/* ------------------------------------------------------------ alerts list */

function renderAlerts(snapshot) {
  const list = els.alertsList();
  if (!list) return;
  const aggregated = Array.isArray(snapshot.alerts_aggregated)
    ? snapshot.alerts_aggregated
    : null;
  const alerts = aggregated || (Array.isArray(snapshot.alerts) ? snapshot.alerts : []);

  const summary = summarizeAggregated(aggregated || alerts);
  const countLabel = aggregated
    ? `${summary.counts.CRITICAL} críticos · ${summary.counts.WARNING} avisos`
    : fmtNumber(alerts.length);

  setText(els.alertsCount(), countLabel);

  const empty = els.alertsEmpty();
  if (alerts.length === 0) {
    list.innerHTML = "";
    empty?.classList.remove("hidden");
    return;
  }
  empty?.classList.add("hidden");

  const recurringNote = summary.recurring > 0
    ? ` · ${summary.recurring} recorrentes`
    : "";

  const rows = alerts
    .slice(0, 50)
    .map((a) => {
      const ref = a.log_id || (a.timestamp ? formatTimestamp(a.timestamp) : "");
      const dot = `<span class="alert-dot" style="background:${severityColor(a.severity)}"></span>`;
      const countBadge = aggregated && a.count > 1
        ? `<span class="alert-count">×${fmtNumber(a.count)}</span>`
        : "";
      const recurringTag = aggregated && a.recurring
        ? `<span class="alert-recurring">recorrente</span>`
        : "";
      const refNode = ref ? `<span class="alert-ref">${ref}</span>` : "";
      return `<li class="alert-row">
        ${dot}
        <span class="alert-msg">${escapeHtml(a.message || "")}</span>
        ${countBadge}
        ${recurringTag}
        ${refNode}
      </li>`;
    })
    .join("");

  list.innerHTML = rows;

  const caption = els.alertsCaption();
  if (caption) {
    caption.textContent = summary.recurring > 0
      ? `${summary.recurring} alerta(s) recorrente(s) em ciclos anteriores${recurringNote}`
      : aggregated ? "agrupados por endpoint" : "";
  }
}

/* ------------------------------------------------------------- stats row */

function renderStats(snapshot) {
  setText(els.statErrors(), fmtNumber(snapshot.errors_count));
  setText(els.statSlow(), fmtNumber(snapshot.slow_requests_count));
  setText(els.statLogs(), fmtNumber(snapshot.logs_processed));

  const validation = snapshot.validation;
  const ok = !validation || validation.valid !== false;
  const validationNode = els.statValidation();
  if (validationNode) {
    validationNode.textContent = ok ? "OK" : "FALHA";
    validationNode.style.color = ok ? "#2fbf71" : "#ef4444";
  }
}

/* ------------------------------------------------------------- header row */

function renderHeader(snapshot) {
  const badge = els.statusBadge();
  if (!badge) return;

  const real = isReal(snapshot);
  badge.textContent = real ? "DADOS REAIS" : "DADOS DE EXEMPLO";
  badge.dataset.mode = real ? "real" : "mock";

  setText(
    els.lastUpdate(),
    snapshot.timestamp ? `atualizado ${formatTimestamp(snapshot.timestamp)}` : ""
  );

  const status = els.pageStatus();
  if (status) {
    status.textContent = real
      ? ""
      : "Falha ao alcançar a branch data — exibindo dados de exemplo.";
    status.classList.toggle("hidden", real);
  }
}

/* ---------------------------------------------------------------- render */

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

async function renderAll() {
  const [latest, recent] = await Promise.all([
    fetchLatestSnapshot(),
    fetchRecentSnapshots(12),
  ]);

  hideSkeleton();
  renderHeader(latest);
  renderGauge(latest);
  buildChart(recent);
  renderAlerts(latest);
  renderStats(latest);
}

/* ---------------------------------------------------------------- wiring */

async function onRefresh() {
  const btn = els.refreshBtn();
  if (!btn || btn.disabled) return;
  btn.disabled = true;
  btn.textContent = "Atualizando…";
  try {
    await renderAll();
  } finally {
    btn.disabled = false;
    btn.textContent = "Atualizar";
  }
}

function onResize() {
  const chart = els.chart();
  if (!chart) return;
  fetchRecentSnapshots(12)
    .then((recent) => {
      if (chart.innerHTML) buildChart(recent);
    })
    .catch(() => {});
}

async function boot() {
  showSkeleton();
  document
    .getElementById("refresh-btn")
    ?.addEventListener("click", onRefresh);
  window.addEventListener("resize", debounce(onResize, 250));

  await renderAll();
  setInterval(() => {
    if (!document.hidden) onRefresh();
  }, REFRESH_MS);
}

function debounce(fn, ms) {
  let timer = null;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
}

boot();
