/**
 * Dashboard application — view logic for the monitoring page.
 *
 * Canonical location: site/monitoring/app.js
 * Published mirror:  docs/assets/app.js (via site/scripts/sync-dashboard.mjs)
 *
 * Consumes the synced mirrors of the canonical tested modules:
 *   - ./client.js     (site/api/client.js — fetcher, fallback mock)
 *   - ./dashboard.js  (site/monitoring/dashboard.js — risk levels, formatting)
 *
 * States: loading (skeleton) -> real data | mock fallback (labeled).
 *
 * The page is deliberately simple: one column, one explanation per number,
 * and a diagnostics panel ("Copiar diagnóstico") that dumps everything the
 * page sees so support can reproduce issues without guesswork.
 */

import { fetchLatestSnapshot, fetchRecentSnapshots } from "./client.js";
import {
  getRiskLevel,
  getRiskColor,
  formatTimestamp,
  summarizeAggregated,
  summarizeShadow,
  summarizeAccuracy,
  summarizePipeline,
  directionLabel,
} from "./dashboard.js";

const REFRESH_MS = 5 * 60 * 1000; // auto-refresh every 5 min

const els = {
  statusBadge: () => document.getElementById("mode-badge"),
  lastUpdate: () => document.getElementById("last-update"),
  refreshBtn: () => document.getElementById("refresh-btn"),
  hero: () => document.getElementById("hero"),
  heroLevel: () => document.getElementById("hero-level"),
  heroExplained: () => document.getElementById("hero-explained"),
  heroRisk: () => document.getElementById("hero-risk"),
  heroErrors: () => document.getElementById("hero-errors"),
  heroTime: () => document.getElementById("hero-time"),
  gaugeLevel: () => document.getElementById("gauge-level"),
  gaugeMarker: () => document.getElementById("gauge-marker"),
  gaugeReadout: () => document.getElementById("gauge-readout"),
  chart: () => document.getElementById("trend-chart"),
  chartEmpty: () => document.getElementById("trend-empty"),
  factsStamp: () => document.getElementById("facts-stamp"),
  factLogs: () => document.getElementById("fact-logs"),
  factErrors: () => document.getElementById("fact-errors"),
  factSlow: () => document.getElementById("fact-slow"),
  factRetries: () => document.getElementById("fact-retries"),
  factValidation: () => document.getElementById("fact-validation"),
  alertsList: () => document.getElementById("alerts-list"),
  alertsEmpty: () => document.getElementById("alerts-empty"),
  alertsCount: () => document.getElementById("alerts-count"),
  shadowVerdict: () => document.getElementById("shadow-verdict"),
  shadowMlRisk: () => document.getElementById("shadow-ml-risk"),
  shadowAnomalies: () => document.getElementById("shadow-anomalies"),
  shadowForecast: () => document.getElementById("shadow-forecast"),
  shadowCaption: () => document.getElementById("shadow-caption"),
  accuracyVerdict: () => document.getElementById("accuracy-verdict"),
  accuracyExpected: () => document.getElementById("accuracy-expected"),
  accuracyActual: () => document.getElementById("accuracy-actual"),
  accuracyAnomaly: () => document.getElementById("accuracy-anomaly"),
  accuracyCaption: () => document.getElementById("accuracy-caption"),
  pipelineDuration: () => document.getElementById("pipeline-duration"),
  pipelineSteps: () => document.getElementById("pipeline-steps"),
  pipelineErrors: () => document.getElementById("pipeline-errors"),
  pageStatus: () => document.getElementById("page-status"),
  skeleton: () => document.getElementById("skeleton"),
  content: () => document.getElementById("content"),
  diagCopy: () => document.getElementById("diag-copy"),
  diagStatus: () => document.getElementById("diag-status"),
};

const THRESHOLDS = [0.4, 0.7]; // WARNING / CRITICAL (matches dashboard.js)

/* ---------------------------------------------------------------- helpers */

function fmtNumber(value) {
  return Number(value ?? 0).toLocaleString("pt-BR");
}

function fmtPct(value) {
  return (Number(value ?? 0) * 100).toLocaleString("pt-BR", {
    maximumFractionDigits: 2,
  });
}

function fmtAge(seconds) {
  if (seconds === null || !isFinite(seconds)) return "";
  if (seconds < 60) return `há ${Math.max(0, Math.round(seconds))} s`;
  if (seconds < 3600) return `há ${Math.round(seconds / 60)} min`;
  return `há ${(seconds / 3600).toFixed(1)} h`;
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

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

/* ------------------------------------------------------------- diagnostics */

const DIAG = {
  version: "2.0",
  page: typeof location !== "undefined" ? location.pathname : "?",
  generatedAt: null,
  userAgent: navigator.userAgent,
  viewport: `${window.innerWidth}x${window.innerHeight}`,
  mode: null,
  latestSnapshotTimestamp: null,
  dataAgeSeconds: null,
  renderErrors: [],
  snapshot: null,
};

window.addEventListener("error", (event) => {
  DIAG.renderErrors.push(String(event.message || event.error || "erro desconhecido"));
});
window.addEventListener("unhandledrejection", (event) => {
  DIAG.renderErrors.push(`promise: ${String(event.reason)}`);
});

function buildDiagnostics() {
  DIAG.generatedAt = new Date().toISOString();
  return JSON.stringify(DIAG, null, 2);
}

function wireDiagnostics() {
  const btn = els.diagCopy();
  const status = els.diagStatus();
  if (!btn) return;
  btn.addEventListener("click", async () => {
    const text = buildDiagnostics();
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const ta = document.createElement("textarea");
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      ta.remove();
    }
    if (status) {
      status.textContent = "Copiado! Cole na conversa do assistente.";
      setTimeout(() => {
        status.textContent = "";
      }, 4000);
    }
  });
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

/* ------------------------------------------------------- hero / estado atual */

function renderHero(snapshot) {
  const hero = els.hero();
  if (!hero) return;

  const risk = Number(snapshot.risk_score ?? 0);
  const level = getRiskLevel(risk);

  hero.dataset.level = level;
  setText(els.heroLevel(), level);
  setText(
    els.heroExplained(),
    level === "CRITICAL"
      ? "Crítico: o risco está acima de 70% — a integração provavelmente está com problemas agora. Veja os alertas."
      : level === "WARNING"
        ? "Atenção: o risco está entre 40% e 70% — vale conferir os alertas abaixo."
        : "Nada urgente: o risco calculado está abaixo de 40%."
  );
  setText(els.heroRisk(), `${fmtPct(risk)}%`);
  setText(els.heroErrors(), fmtNumber(snapshot.errors_count));
  setText(els.heroTime(), formatTimestamp(snapshot.timestamp));
}

/* ---------------------------------------------------------- gauge render */

function renderGauge(snapshot) {
  const risk = Number(snapshot.risk_score ?? 0);
  const level = getRiskLevel(risk);
  const color = getRiskColor(risk);
  const marker = els.gaugeMarker();
  const readout = els.gaugeReadout();

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

  const lastTimestamp = last.timestamp ? formatTimestamp(last.timestamp) : "";

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
}

/* ------------------------------------------------------------- facts row */

function renderFacts(snapshot) {
  setText(els.factsStamp(), formatTimestamp(snapshot.timestamp));
  setText(els.factLogs(), fmtNumber(snapshot.logs_processed));
  setText(els.factErrors(), fmtNumber(snapshot.errors_count));
  setText(els.factSlow(), fmtNumber(snapshot.slow_requests_count));
  setText(els.factRetries(), fmtNumber(snapshot.retried_count));

  const validation = snapshot.validation;
  const ok = !validation || validation.valid !== false;
  const node = els.factValidation();
  if (node) {
    node.textContent = ok ? "OK" : "FALHA";
    node.style.color = ok ? "#2fbf71" : "#ef4444";
  }
}

/* ------------------------------------------------------------- header row */

function renderHeader(snapshot) {
  const badge = els.statusBadge();
  if (!badge) return;

  const real = isReal(snapshot);
  badge.textContent = real ? "DADOS REAIS" : "DADOS DE EXEMPLO";
  badge.dataset.mode = real ? "real" : "mock";

  const age = snapshot.timestamp
    ? (Date.now() - new Date(snapshot.timestamp).getTime()) / 1000
    : null;
  setText(
    els.lastUpdate(),
    snapshot.timestamp
      ? `atualizado ${formatTimestamp(snapshot.timestamp)} (${fmtAge(age)})`
      : ""
  );

  const status = els.pageStatus();
  if (status) {
    status.textContent = real
      ? ""
      : "Falha ao alcançar a branch data — exibindo dados de exemplo.";
    status.classList.toggle("hidden", real);
  }
}

/* ---------------------------------------------------------- shadow mode */

function renderShadow(snapshot) {
  const tag = els.shadowVerdict();
  if (!tag) return;

  const summary = summarizeShadow(snapshot.shadow_mode);
  tag.textContent = summary.verdict;
  tag.dataset.state = summary.enabled
    ? summary.verdict === "CONCORDA" ? "agree" : "disagree"
    : "off";

  setText(els.shadowMlRisk(), summary.enabled ? `${fmtPct(summary.mlRisk)}%` : "—");
  setText(els.shadowAnomalies(), summary.enabled ? fmtNumber(summary.anomalies) : "—");
  setText(
    els.shadowForecast(),
    summary.enabled
      ? summary.predicted
          .map((v) => v.toLocaleString("pt-BR", { maximumFractionDigits: 2 }))
          .join(" · ")
      : "—"
  );
  setText(
    els.shadowCaption(),
    summary.enabled
      ? "Observação: a IA concorda com a heurística quando os dois riscos caminham juntos."
      : "Sem série temporal suficiente nesta coleta para a IA."
  );
}

function renderAccuracy(snapshot) {
  const tag = els.accuracyVerdict();
  if (!tag) return;

  const summary = summarizeAccuracy(snapshot.accuracy);
  tag.textContent = summary.verdict;
  tag.dataset.state = !summary.available
    ? "off"
    : summary.verdict === "ACERTOU"
      ? "hit"
      : summary.verdict === "ERROU"
        ? "miss"
        : "unknown";

  setText(els.accuracyExpected(), summary.available ? directionLabel(summary.directionExpected) : "—");
  setText(els.accuracyActual(), summary.available ? directionLabel(summary.directionActual) : "—");
  setText(
    els.accuracyAnomaly(),
    summary.available
      ? summary.anomalyFlagged
        ? summary.anomalyHit === true
          ? "confirmada"
          : summary.anomalyHit === false
            ? "falso positivo"
            : "em análise"
        : "nenhuma"
      : "—"
  );
  setText(
    els.accuracyCaption(),
    summary.available
      ? "Avaliação do ciclo anterior: sem efeito no risco heurístico."
      : "Sem avaliação anterior: o pipeline registra a acurácia automaticamente."
  );
}

function renderPipeline(snapshot) {
  const summary = summarizePipeline(snapshot.pipeline);
  const duration = els.pipelineDuration();
  if (duration) {
    duration.textContent = summary.available
      ? `último ciclo em ${summary.durationMs !== null ? `${summary.durationMs} ms` : "tempo não medido"}`
      : "sem dados do ciclo";
  }

  const steps = els.pipelineSteps();
  if (steps) {
    const failed = new Set(
      summary.stepErrors.map((e) => (e && e.step ? e.step : ""))
    );
    steps.innerHTML = summary.steps
      .map(
        (s) =>
          `<span class="pipeline-step ${failed.has(s) ? "failed" : "ok"}">${escapeHtml(s)}</span>`
      )
      .join("");
  }

  const errors = els.pipelineErrors();
  if (errors) {
    if (summary.hasErrors) {
      errors.innerHTML = `<strong>Passos com falha neste ciclo</strong>${summary.stepErrors
        .map((e) => escapeHtml(`${e.step}: ${e.error}`))
        .join("<br>")}`;
      errors.classList.remove("hidden");
    } else {
      errors.classList.add("hidden");
    }
  }
}

/* ---------------------------------------------------------------- render */

async function renderAll() {
  const [latest, recent] = await Promise.all([
    fetchLatestSnapshot(),
    fetchRecentSnapshots(12),
  ]);

  DIAG.mode = latest && latest.mode ? latest.mode : null;
  DIAG.latestSnapshotTimestamp = latest && latest.timestamp ? latest.timestamp : null;
  DIAG.dataAgeSeconds = latest && latest.timestamp
    ? Math.round((Date.now() - new Date(latest.timestamp).getTime()) / 1000)
    : null;
  DIAG.snapshot = latest;

  hideSkeleton();
  renderHeader(latest);
  renderHero(latest);
  renderGauge(latest);
  buildChart(recent);
  renderFacts(latest);
  renderAlerts(latest);
  renderShadow(latest);
  renderAccuracy(latest);
  renderPipeline(latest);
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

function debounce(fn, ms) {
  let timer = null;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
}

async function boot() {
  showSkeleton();
  wireDiagnostics();
  document
    .getElementById("refresh-btn")
    ?.addEventListener("click", onRefresh);
  window.addEventListener("resize", debounce(onResize, 250));

  await renderAll();
  setInterval(() => {
    if (!document.hidden) onRefresh();
  }, REFRESH_MS);
}

boot();
