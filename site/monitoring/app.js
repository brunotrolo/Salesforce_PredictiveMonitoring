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

import {
  fetchLatestSnapshot,
  fetchRecentSnapshots,
  fetchTrace,
  fetchTimeout,
  dispatchWorkflow,
  fetchWorkflowRuns,
  validateToken,
} from "./client.js";
import {
  getRiskLevel,
  getRiskColor,
  formatTimestamp,
  summarizeAggregated,
  summarizeShadow,
  summarizeAccuracy,
  summarizePipeline,
  summarizeLogs,
  summarizeTrace,
  isStale,
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
  staleWarning: () => document.getElementById("stale-warning"),
  staleAge: () => document.getElementById("stale-age"),
  staleRefresh: () => document.getElementById("stale-refresh"),
  traceNote: () => document.getElementById("trace-note"),
  traceChips: () => document.getElementById("trace-chips"),
  traceTimeline: () => document.getElementById("trace-timeline"),
  traceEvents: () => document.getElementById("trace-events"),
  logsNote: () => document.getElementById("logs-note"),
  logsBody: () => document.getElementById("logs-body"),
  logsEmpty: () => document.getElementById("logs-empty"),
  refreshModal: () => document.getElementById("refresh-modal"),
  modalClose: () => document.getElementById("modal-close"),
  modalStatus: () => document.getElementById("modal-status"),
  modalBar: () => document.getElementById("modal-bar"),
  modalSteps: () => document.getElementById("modal-steps"),
  modalGithub: () => document.getElementById("modal-github"),
  modalStart: () => document.getElementById("modal-start"),
  modalHint: () => document.getElementById("modal-hint"),
  tokenInput: () => document.getElementById("token-input"),
  tokenSave: () => document.getElementById("token-save"),
  tokenRemove: () => document.getElementById("token-remove"),
  tokenStatus: () => document.getElementById("token-status"),
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
      const label = d
        ? d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", timeZone: "America/Sao_Paulo" })
        : "";
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

/* ------------------------------------------------------- stale warning */

function renderStale(snapshot) {
  const banner = els.staleWarning();
  if (!banner) return;
  if (!isStale(snapshot)) {
    banner.classList.add("hidden");
    return;
  }
  const ageMin = Math.round(
    (Date.now() - new Date(snapshot.timestamp).getTime()) / 60000
  );
  setText(els.staleAge(), String(ageMin));
  banner.classList.remove("hidden");
}

/* --------------------------------------------------- 24h trace section */

function traceSegLevel(entry) {
  return getRiskLevel(Number(entry.risk_score ?? 0));
}

function fmtTraceTime(timestamp) {
  const d = new Date(timestamp);
  if (Number.isNaN(d.getTime())) return timestamp;
  return d.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "America/Sao_Paulo",
  });
}

function renderTrace(trace) {
  const summary = summarizeTrace(trace);
  const chips = els.traceChips();
  const timeline = els.traceTimeline();
  const events = els.traceEvents();
  const note = els.traceNote();
  if (!chips && !timeline && !events) return;

  if (note) {
    note.textContent =
      summary.cycles > 0 ? `${summary.cycles} ciclos no período` : "sem dados de trace";
  }

  if (chips) {
    const worst = summary.maxRisk >= 0.7 ? "critical" : summary.maxRisk >= 0.4 ? "warn" : "good";
    chips.innerHTML = [
      `<span class="trace-chip" data-kind="${worst}"><b>${fmtNumber(summary.cycles)}</b> ciclos</span>`,
      `<span class="trace-chip" data-kind="${worst}"><b>${(summary.maxRisk * 100).toLocaleString("pt-BR", { maximumFractionDigits: 0 })}%</b> risco máximo</span>`,
      `<span class="trace-chip" data-kind="${summary.downWindows.length > 0 ? "critical" : "good"}"><b>${fmtNumber(summary.downWindows.length)}</b> queda(s)</span>`,
      `<span class="trace-chip" data-kind="${summary.anomalies.length > 0 ? "warn" : "good"}"><b>${fmtNumber(summary.anomalies.length)}</b> ciclo(s) com anomalia</span>`,
      `<span class="trace-chip" data-kind="${summary.breakers.length > 0 ? "critical" : "good"}"><b>${fmtNumber(summary.breakers.length)}</b> circuit breaker</span>`,
      `<span class="trace-chip" data-kind="${summary.gaps.length > 0 ? "warn" : "good"}"><b>${fmtNumber(summary.gaps.length)}</b> sem coleta</span>`,
    ].join("");
  }

  if (timeline && summary.cycles > 0) {
    const list = trace.slice().sort((a, b) =>
      String(a.timestamp ?? "").localeCompare(String(b.timestamp ?? ""))
    );
    timeline.innerHTML = list
      .map((entry, i) => {
        const gap = i > 0 && entry.timestamp
          ? (new Date(entry.timestamp) - new Date(list[i - 1].timestamp)) / 60000
          : 0;
        const isGap = Number.isFinite(gap) && gap > 15;
        const title = `${fmtTraceTime(entry.timestamp)} — risco ${(Number(entry.risk_score ?? 0) * 100).toLocaleString("pt-BR", { maximumFractionDigits: 0 })}%${isGap ? " · após intervalo de " + Math.round(gap) + " min" : ""}`;
        return `<span class="tl-seg" data-level="${isGap ? "GAP" : traceSegLevel(entry)}" data-gap="${isGap ? "true" : "false"}" title="${escapeHtml(title)}"></span>`;
      })
      .join("");
  }

  if (events) {
    const items = [];
    for (const gap of summary.gaps) {
      items.push(
        `<li><b>Sem coleta</b> de ${fmtTraceTime(gap.from)} até ${fmtTraceTime(gap.to)} (<b>${gap.minutes} min</b>) — agendador do GitHub atrasou</li>`
      );
    }
    for (const down of summary.downWindows) {
      items.push(
        `<li><b class="sev-critical">Queda</b> de ${fmtTraceTime(down.from)} até ${fmtTraceTime(down.to)} (pico ${(down.peak * 100).toLocaleString("pt-BR", { maximumFractionDigits: 0 })}%)</li>`
      );
    }
    for (const ts of summary.anomalies) {
      items.push(
        `<li><b class="sev-warning">Anomalia detectada</b> pela IA de sombra em ${fmtTraceTime(ts)}</li>`
      );
    }
    for (const ts of summary.breakers) {
      items.push(
        `<li><b class="sev-critical">Circuit breaker</b> aberto em ${fmtTraceTime(ts)} — integração recusou chamadas</li>`
      );
    }
    events.innerHTML =
      items.length > 0
        ? `<ul>${items.slice(0, 8).join("")}</ul>`
        : summary.cycles > 0
          ? `<ul><li>Nenhum evento fora do normal nas últimas 24 horas.</li></ul>`
          : `<ul><li>Sem dados de trace ainda — o histórico começa a ser gravado na próxima coleta.</li></ul>`;
  }
}

/* ---------------------------------------------------- real logs section */

function renderLogs(logs) {
  const body = els.logsBody();
  const note = els.logsNote();
  const empty = els.logsEmpty();
  if (!body) return;

  const summary = summarizeLogs(logs);
  if (note) {
    const parts = [`${fmtNumber(summary.total)} logs`];
    if (summary.errors > 0) parts.push(`${fmtNumber(summary.errors)} com erro`);
    if (summary.retried > 0) parts.push(`${fmtNumber(summary.retried)} retried`);
    if (summary.circuitBreaker > 0) parts.push(`${fmtNumber(summary.circuitBreaker)} circuit breaker`);
    note.textContent = parts.join(" · ");
  }

  const list = Array.isArray(logs) ? logs : [];
  if (empty) empty.classList.toggle("hidden", list.length > 0);

  const rows = list
    .slice()
    .sort((a, b) =>
      String(b.timestamp ?? "").localeCompare(String(a.timestamp ?? ""))
    )
    .slice(0, 100)
    .map((log) => {
      const status = Number(log.status_code ?? 0);
      const sev = log.severity ? String(log.severity).toUpperCase() : status >= 500 ? "ERROR" : "INFO";
      const sevLabel = sev === "ERROR" || sev === "CRITICAL" ? "CRITICAL" : sev === "WARNING" ? "WARNING" : "INFO";
      const isError = status >= 500;
      const msg = String(log.message ?? "");
      return `<tr data-error="${isError ? "true" : "false"}">
        <td>${escapeHtml(log.timestamp ? fmtTraceTime(log.timestamp) : "—")}</td>
        <td>${isError ? escapeHtml(`HTTP ${status}`) : escapeHtml(String(status || "—"))}</td>
        <td><span class="sev-badge" data-sev="${sevLabel}">${sevLabel}</span></td>
        <td>${escapeHtml(String(log.resource ?? "—"))}</td>
        <td>${log.retried ? "sim" : "não"}</td>
        <td class="logs-msg" title="${escapeHtml(msg)}">${escapeHtml(msg || "—")}</td>
      </tr>`;
    })
    .join("");

  body.innerHTML = rows || '<tr><td colspan="6">—</td></tr>';
}

/* ---------------------------------------------------------------- render */

async function renderAll() {
  const [latest, recent, trace] = await Promise.all([
    fetchLatestSnapshot(),
    fetchRecentSnapshots(12),
    fetchTrace(),
  ]);

  DIAG.mode = latest && latest.mode ? latest.mode : null;
  DIAG.latestSnapshotTimestamp = latest && latest.timestamp ? latest.timestamp : null;
  DIAG.dataAgeSeconds = latest && latest.timestamp
    ? Math.round((Date.now() - new Date(latest.timestamp).getTime()) / 1000)
    : null;
  DIAG.snapshot = latest;
  DIAG.traceCycles = Array.isArray(trace) ? trace.length : null;
  DIAG.logsTotal = latest && Array.isArray(latest.logs) ? latest.logs.length : null;
  DIAG.tokenConfigured = Boolean(getSavedToken());

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
  renderStale(latest);
  renderTrace(trace);
  renderLogs(latest && latest.logs ? latest.logs : []);
}

/* ------------------------------------------------ manual refresh modal */

// Public Actions REST API: read-only, no auth needed for public repos.
// Polls the latest workflow_dispatch run to follow a manual collection.
const GITHUB_RUNS_URL =
  "https://api.github.com/repos/brunotrolo/Salesforce_PredictiveMonitoring/actions/workflows/collect.yml/runs?event=workflow_dispatch&per_page=1";
const MODAL_POLL_MS = 5000;
const MODAL_EXPECTED_SEC = 60;
const MODAL_TIMEOUT_SEC = 8 * 60;
const MODAL_HINT_SEC = 30;
// Tolerates a run dispatched up to 5 min before the modal opened (clock
// skew between browser and GitHub, or user clicked Run first).
const RUN_FRESH_MARGIN_MS = 5 * 60 * 1000;
const DEFAULT_STEPS = ["collect", "analyze", "aggregate", "compare", "shadow", "save"];
// Rough weight per pipeline step (from real snapshots: collect dominates).
const PIPELINE_STEP_WEIGHTS = {
  collect: 0.45,
  analyze: 0.2,
  aggregate: 0.1,
  compare: 0.05,
  shadow: 0.15,
  accuracy: 0.05,
  save: 0.05,
};

let modalTimer = null;
let modalState = null;

function getModalSteps() {
  const fromSnapshot = DIAG.snapshot && DIAG.snapshot.pipeline && DIAG.snapshot.pipeline.steps;
  return Array.isArray(fromSnapshot) && fromSnapshot.length > 0 ? fromSnapshot : DEFAULT_STEPS;
}

function renderModalSteps(fraction, failed) {
  const steps = getModalSteps();
  const weights = steps.map((s) => PIPELINE_STEP_WEIGHTS[s] ?? 0.15);
  const total = weights.reduce((a, b) => a + b, 0) || 1;
  let acc = 0;
  const states = steps.map((s, i) => {
    if (failed) return "fail";
    const doneAt = (acc + weights[i]) / total;
    const startedAt = acc / total;
    acc += weights[i];
    if (fraction >= doneAt) return "ok";
    if (fraction >= startedAt) return "active";
    return "pending";
  });
  const wrap = els.modalSteps();
  if (wrap) {
    wrap.innerHTML = steps
      .map(
        (s, i) =>
          `<span class="modal-step" data-state="${states[i]}">${escapeHtml(s)}</span>`
      )
      .join("");
  }
}

function setModalStatus(text, state) {
  const status = els.modalStatus();
  if (status) {
    status.textContent = text;
    status.dataset.state = state;
  }
}

function setModalHint(text) {
  setText(els.modalHint(), text);
}

function updateModalBar(pct, state = "idle") {
  const bar = els.modalBar();
  if (bar) {
    bar.style.width = `${Math.max(0, Math.min(100, pct))}%`;
    bar.dataset.state = state;
  }
}

async function checkLatestDispatchRun(sinceMs) {
  try {
    const res = await fetchTimeout(GITHUB_RUNS_URL, 7000);
    if (!res || !res.ok) {
      if (modalState && (res.status === 403 || res.status === 429)) {
        modalState.rateLimited = true;
        setModalHint("O GitHub limitou as consultas da janela (60/h) — ela passa a verificar de 30 em 30 s.");
      }
      return null;
    }
    const data = await res.json();
    const run = data.workflow_runs && data.workflow_runs[0];
    if (!run) return null;
    const started = new Date(run.started_at || run.created_at).getTime();
    if (!Number.isFinite(started) || started < sinceMs - RUN_FRESH_MARGIN_MS) return null;
    return run;
  } catch {
    return null;
  }
}

const TOKEN_STORAGE_KEY = "gh_pat_monitoring";

function getSavedToken() {
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY) || "";
  } catch {
    return "";
  }
}

function setSavedToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_STORAGE_KEY, token);
    else localStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch {
    /* storage unavailable (private mode) — token just won't persist */
  }
}

function updateTokenUi() {
  const token = getSavedToken();
  const input = els.tokenInput();
  if (input) input.value = token ? "••••••••••••••••" : "";
  const status = els.tokenStatus();
  if (status) {
    if (token) {
      status.textContent = "Token salvo NESTE navegador — a coleta dispara com 1 clique.";
      status.dataset.state = "ok";
    } else {
      status.textContent = "Sem token: a janela abre o GitHub para você clicar em Run workflow.";
      status.dataset.state = "muted";
    }
  }
  if (els.tokenRemove()) els.tokenRemove().style.display = token ? "" : "none";
  syncModalCta();
}

/** Swaps the modal CTA: one-click start (token) vs GitHub link (no token). */
function syncModalCta() {
  const token = getSavedToken();
  const startBtn = els.modalStart();
  if (startBtn) {
    startBtn.disabled = false;
    startBtn.style.display = token ? "" : "none";
  }
  if (els.modalGithub()) els.modalGithub().style.display = token ? "none" : "";
}

/**
 * Newest dispatch run respecting the saved token: with a token we use the
 * authenticated endpoint (5000 req/h), without it the public read-only one.
 */
async function getLatestDispatchRun(sinceMs) {
  const token = getSavedToken();
  if (!token) return checkLatestDispatchRun(sinceMs);
  const runs = await fetchWorkflowRuns(token);
  if (!runs || runs.length === 0) return null;
  const run = runs[0];
  const started = new Date(run.started_at || run.created_at).getTime();
  if (!Number.isFinite(started) || started < sinceMs - RUN_FRESH_MARGIN_MS) return null;
  return run;
}

/** POST workflow_dispatch with the saved token — the one-click path. */
async function startManualRun() {
  if (!modalState || modalState.phase === "starting") return;
  const token = getSavedToken();
  if (!token) return;
  modalState.phase = "starting";
  modalState.rateLimited = false;
  const startBtn = els.modalStart();
  if (startBtn) startBtn.disabled = true;
  setModalStatus("Disparando a coleta no GitHub…", "idle");
  setModalHint("");
  updateModalBar(2);
  renderModalSteps(0, false);
  const result = await dispatchWorkflow(token);
  if (!modalState || modalState.phase === "failed" || modalState.phase === "done") return;
  if (!result.ok) {
    modalState.phase = "waiting";
    if (startBtn) startBtn.disabled = false;
    updateModalBar(0);
    if (result.status === 401 || result.status === 403) {
      setModalStatus("O token foi recusado pelo GitHub.", "failed");
      setModalHint("Atualize o token abaixo (permite Actions: read/write) e tente de novo.");
    } else {
      setModalStatus(`Não foi possível disparar a coleta (${result.error || "erro de rede"}).`, "failed");
      setModalHint("Verifique sua conexão e tente de novo, ou abra o GitHub manualmente.");
    }
    return;
  }
  modalState.phase = "running";
  modalState.runStartedAt = Date.now();
  setModalStatus("Coleta disparada no GitHub — acompanhando a execução…", "idle");
  setModalHint("");
  scheduleNextPoll();
}

async function onTokenSave() {
  const input = els.tokenInput();
  if (!input) return;
  const value = input.value.trim();
  if (value === "" || value.startsWith("•")) return;
  const saveBtn = els.tokenSave();
  const status = els.tokenStatus();
  if (saveBtn) saveBtn.disabled = true;
  if (status) status.textContent = "Validando token…";
  const ok = await validateToken(value);
  if (saveBtn) saveBtn.disabled = false;
  if (ok) {
    setSavedToken(value);
    input.value = "";
    if (status) {
      status.textContent = "Token validado e salvo NESTE navegador — a coleta agora dispara com 1 clique.";
      status.dataset.state = "ok";
    }
    if (els.tokenRemove()) els.tokenRemove().style.display = "";
  } else if (status) {
    status.textContent = "Token inválido ou sem acesso de leitura/escrita em Actions — nada foi salvo.";
    status.dataset.state = "error";
  }
}

function onTokenRemove() {
  setSavedToken("");
  updateTokenUi();
}

function scheduleNextPoll() {
  if (!modalState || modalState.phase === "failed" || modalState.phase === "done") return;
  const elapsedSec = (Date.now() - modalState.openedAt) / 1000;
  let delay = MODAL_POLL_MS;
  if (modalState.rateLimited) delay = 30000;
  else if (elapsedSec > 60) delay = 15000;
  modalTimer = setTimeout(pollModal, delay);
}

function failModal(message) {
  modalState = modalState || { phase: "failed" };
  modalState.phase = "failed";
  if (modalTimer) {
    clearTimeout(modalTimer);
    modalTimer = null;
  }
  renderModalSteps(1, true);
  setModalStatus(message, "failed");
  setModalHint("Feche e tente novamente, ou veja o log da execução no GitHub.");
}

async function doneModal() {
  modalState.phase = "done";
  if (modalTimer) {
    clearTimeout(modalTimer);
    modalTimer = null;
  }
  renderModalSteps(1, false);
  updateModalBar(100, "done");
  setModalStatus("Coleta concluída — atualizando a página…", "done");
  setTimeout(() => {
    closeModal();
    renderAll();
  }, 1400);
}

async function pollModal() {
  if (!modalState || modalState.phase === "failed" || modalState.phase === "done") return;
  const now = Date.now();
  const elapsedSec = (now - modalState.openedAt) / 1000;

  if (modalState.phase === "waiting") {
    if (elapsedSec > MODAL_TIMEOUT_SEC) {
      failModal("Tempo esgotado: nenhuma execução detectada em 8 minutos.");
      return;
    }
    const run = await getLatestDispatchRun(modalState.openedAt);
    if (run) {
      modalState.phase = "running";
      modalState.rateLimited = false;
      modalState.run = run;
      modalState.runStartedAt = new Date(run.started_at || run.created_at).getTime();
      setModalHint("");
      if (els.modalStart()) els.modalStart().disabled = true;
    } else {
      if (getSavedToken()) {
        setModalStatus("1 clique em \"Iniciar coleta\" dispara tudo — ou aguarde a coleta agendada.", "idle");
      } else {
        setModalStatus("Aguardando a coleta começar no GitHub…", "idle");
      }
      if (elapsedSec > MODAL_HINT_SEC) {
        setModalHint(
          getSavedToken()
            ? "Já existe execução em andamento? Ela será detectada sozinha."
            : "Nenhuma execução detectada ainda — confira se clicou em Run workflow."
        );
      }
      renderModalSteps(Math.min(1, elapsedSec / MODAL_EXPECTED_SEC), false);
      updateModalBar(2);
    }
    scheduleNextPoll();
    return;
  }

  if (modalState.phase === "running") {
    const runElapsedSec = (now - modalState.runStartedAt) / 1000;
    const fraction = Math.min(1, runElapsedSec / MODAL_EXPECTED_SEC);
    renderModalSteps(fraction, false);
    updateModalBar(Math.min(92, Math.round(fraction * 92)));

    const run = await getLatestDispatchRun(modalState.openedAt);
    const concluded = run && (run.conclusion || run.status === "completed");
    if (run && run.conclusion === "failure") {
      failModal("A coleta falhou no GitHub — confira o log do workflow.");
      return;
    }
    if (runElapsedSec > MODAL_TIMEOUT_SEC) {
      failModal("Tempo esgotado: a coleta demorou mais de 8 minutos.");
      return;
    }
    // A fresh snapshot (committed after this modal opened) is the ground
    // truth for completion — the GitHub run list can lag by seconds.
    if (concluded || runElapsedSec > MODAL_EXPECTED_SEC) {
      const latest = await fetchLatestSnapshot();
      const snapshotTime = latest && latest.timestamp ? new Date(latest.timestamp).getTime() : 0;
      if (Number.isFinite(snapshotTime) && snapshotTime > modalState.openedAt - 60000) {
        await doneModal();
        return;
      }
    }
    setModalStatus(
      concluded
        ? "Execução concluída no GitHub — aguardando o snapshot aparecer…"
        : run && run.status === "queued"
          ? "Execução aguardando runner disponível no GitHub…"
          : `Coleta em andamento no GitHub… (${Math.min(92, Math.round(fraction * 92))}%)`,
      "idle"
    );
    scheduleNextPoll();
  }
}

function openModal() {
  if (modalTimer) {
    clearTimeout(modalTimer);
    modalTimer = null;
  }
  updateTokenUi();
  modalState = { openedAt: Date.now(), phase: "waiting", run: null, runStartedAt: null, rateLimited: false };
  updateModalBar(0);
  renderModalSteps(0, false);
  setModalHint("");
  syncModalCta();
  if (getSavedToken()) {
    setModalStatus(
      "Com o token salvo, 1 clique inicia a coleta — acompanho tudo aqui e atualizo a página sozinho.",
      "idle"
    );
  } else {
    setModalStatus(
      "A coleta manual roda exatamente como a agendada: 1º abra o workflow no GitHub, 2º clique em Run workflow.",
      "idle"
    );
  }
  els.refreshModal()?.classList.remove("hidden");
  pollModal();
}

function closeModal() {
  if (modalTimer) {
    clearTimeout(modalTimer);
    modalTimer = null;
  }
  modalState = null;
  els.refreshModal()?.classList.add("hidden");
}

/* ---------------------------------------------------------------- wiring */

function onRefresh() {
  openModal();
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
  els.staleRefresh()?.addEventListener("click", onRefresh);
  els.modalClose()?.addEventListener("click", closeModal);
  els.modalStart()?.addEventListener("click", startManualRun);
  els.tokenSave()?.addEventListener("click", onTokenSave);
  els.tokenRemove()?.addEventListener("click", onTokenRemove);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeModal();
  });
  window.addEventListener("resize", debounce(onResize, 250));

  await renderAll();
  setInterval(() => {
    if (!document.hidden) onRefresh();
  }, REFRESH_MS);
}

boot();
