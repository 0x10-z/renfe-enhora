import { state } from "./store";
import { esc } from "./utils";
import { openModal } from "./stationModal";
import { stationHTML } from "./stations";

export const SEVERITY_LABELS: Record<string, string> = {
  ok: "Sin problemas", warn: "Atención", bad: "Alerta", info: "Dato del día",
};

export const INSIGHT_ICONS: Record<string, string> = {
  ok:   `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`,
  warn: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`,
  bad:  `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
  info: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`,
};

export const CHEVRON_ICON = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>`;

const MOBILE_INSIGHTS_LIMIT = 3;

export function renderInsights(insights: any[]) {
  const section  = document.getElementById("insights-section")!;
  const grid     = document.getElementById("insights-grid")!;
  const countEl  = document.getElementById("insight-count")!;
  const showMore = document.getElementById("insights-show-more") as HTMLButtonElement | null;

  if (!insights.length) { section.style.display = "none"; return; }

  countEl.textContent = `${insights.length}`;

  const renderCards = (list: any[]) => list.map(({ id, text, severity = "info", meta }) => {
    const drillable = meta && ["A", "B", "C"].includes(id);
    const extraCls  = drillable ? " insight-drillable" : "";
    const dataAttrs = drillable
      ? ` data-insight-id="${id}" data-meta="${encodeURIComponent(JSON.stringify(meta))}"`
      : "";
    const cta = drillable
      ? `<span class="insight-cta">${CHEVRON_ICON}</span>`
      : "";
    return `<div class="insight-card insight-${severity}${extraCls}"${dataAttrs}>
      <div class="insight-icon-wrap">${INSIGHT_ICONS[severity] ?? INSIGHT_ICONS.info}</div>
      <div class="insight-body">
        <span class="insight-label">${SEVERITY_LABELS[severity] ?? "Info"}</span>
        <p class="insight-text">${esc(text)}</p>
      </div>
      ${cta}
    </div>`;
  }).join("");

  const isMobile = () => window.innerWidth <= 600;
  const hasMore  = insights.length > MOBILE_INSIGHTS_LIMIT;

  if (showMore) {
    if (isMobile() && hasMore) {
      grid.innerHTML = renderCards(insights.slice(0, MOBILE_INSIGHTS_LIMIT));
      showMore.style.display = "flex";
      showMore.onclick = () => {
        grid.innerHTML = renderCards(insights);
        showMore.style.display = "none";
      };
    } else {
      grid.innerHTML = renderCards(insights);
      showMore.style.display = "none";
    }
  } else {
    grid.innerHTML = renderCards(insights);
  }

  section.style.display = "block";
}

export function openInsightDrilldown(meta: any) {
  const hour: number | undefined = meta.hour;
  const delayed = state.allStations
    .filter(s => (s.delayed_count ?? 0) > 0)
    .sort((a, b) => (b.delayed_count ?? 0) - (a.delayed_count ?? 0));

  document.getElementById("insight-modal-title")!.textContent =
    hour !== undefined
      ? `Retrasos acumulados a las ${String(hour).padStart(2, "0")}h`
      : "Estaciones con retrasos en curso";
  document.getElementById("insight-modal-sub")!.textContent =
    delayed.length
      ? `${delayed.length} estación${delayed.length !== 1 ? "es" : ""} afectada${delayed.length !== 1 ? "s" : ""} — pulsa una para ver sus trenes`
      : "Sin estaciones con retrasos en este momento";

  const body = document.getElementById("insight-modal-body")!;
  body.innerHTML = delayed.length
    ? `<div class="stations-grid">${delayed.map(stationHTML).join("")}</div>`
    : `<div class="empty-state"><p>Sin retrasos activos en este momento.</p></div>`;

  document.getElementById("insight-modal")!.style.display = "flex";
  document.body.style.overflow = "hidden";
}

export function closeInsightModal() {
  document.getElementById("insight-modal")!.style.display = "none";
  document.body.style.overflow = "";
}

// Re-export openModal so callers that go through insightModal get the right reference
export { openModal };
