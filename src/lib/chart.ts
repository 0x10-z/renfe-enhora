import * as echarts from "echarts";
import { state } from "./store";

export const CHART_COLORS = {
  delayed:  "#dc2626",
  onTime:   "#059669",
  text:     "#6b7280",
  subtext:  "#9ca3af",
  grid:     "#e2e7f2",
  tooltip:  "#111827",
  p50:      "#6366f1",
  p75:      "#f59e0b",
  p90:      "#ef4444",
};

export function getOrCreateChart(): echarts.ECharts {
  const el = document.getElementById("echart-main")!;
  if (!state.chart) {
    state.chart = echarts.init(el, undefined, { renderer: "canvas" });
    new ResizeObserver(() => state.chart?.resize()).observe(el);
  }
  return state.chart;
}

export function renderHistory() {
  if (state.historyRecords.length < 2) return;
  document.getElementById("history-section")!.style.display = "block";
  const el = document.getElementById("echart-main")!;
  if (state.activeDays === -2) {
    el.style.height = "260px";
    renderHeatmap();
  } else {
    el.style.height = "220px";
    if (state.activeDays === -1) renderHourly(); else renderDaily();
  }
  state.chart?.resize();
}

export function linearRegression(data: number[]): number[] {
  const n = data.length;
  if (n < 2) return data;
  const sumX  = (n * (n - 1)) / 2;
  const sumX2 = (n * (n - 1) * (2 * n - 1)) / 6;
  const sumY  = data.reduce((a, b) => a + b, 0);
  const sumXY = data.reduce((acc, y, i) => acc + i * y, 0);
  const m = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
  const b = (sumY - m * sumX) / n;
  return data.map((_, i) => Math.max(0, +(b + m * i).toFixed(2)));
}

export function renderDaily() {
  const byDate = new Map<string, { totalSum: number; delayedSum: number; maxMin: number; trips: number[]; p50s: number[]; p75s: number[]; p90s: number[] }>();
  for (const r of state.historyRecords) {
    if (!byDate.has(r.date)) byDate.set(r.date, { totalSum: 0, delayedSum: 0, maxMin: 0, trips: [], p50s: [], p75s: [], p90s: [] });
    const d = byDate.get(r.date)!;
    d.totalSum   += r.total   ?? 0;
    d.delayedSum += r.delayed ?? 0;
    d.maxMin = Math.max(d.maxMin, r.max_min ?? 0);
    if (r.trips > 0) d.trips.push(r.trips);
    if (r.p50 > 0) d.p50s.push(r.p50);
    if (r.p75 > 0) d.p75s.push(r.p75);
    if (r.p90 > 0) d.p90s.push(r.p90);
  }

  let dates = [...byDate.keys()].sort();
  if (state.activeDays > 0) dates = dates.slice(-state.activeDays);

  const avg = (arr: number[]) => arr.length ? +(arr.reduce((a, b) => a + b, 0) / arr.length).toFixed(1) : null;
  const delayedData = dates.map(date => {
    const d = byDate.get(date)!;
    const pct = d.totalSum > 0 ? +(d.delayedSum / d.totalSum * 100).toFixed(1) : 0;
    return { value: pct, meta: d };
  });
  const onTimeData = dates.map((_, i) => +(100 - delayedData[i].value).toFixed(1));
  const tripsRaw = dates.map(date => avg(byDate.get(date)!.trips));
  const maxTrips = Math.max(...tripsRaw.filter(v => v != null) as number[], 1);
  const tripsData = tripsRaw.map(v => v != null ? +(v / maxTrips * 100).toFixed(1) : null);
  const p50Data = dates.map(date => avg(byDate.get(date)!.p50s));
  const p75Data = dates.map(date => avg(byDate.get(date)!.p75s));
  const p90Data = dates.map(date => avg(byDate.get(date)!.p90s));

  getOrCreateChart().setOption({
    backgroundColor: "transparent",
    tooltip: {
      trigger: "axis",
      backgroundColor: CHART_COLORS.tooltip,
      borderColor: CHART_COLORS.tooltip,
      textStyle: { color: "#fff", fontSize: 12, fontFamily: "JetBrains Mono, monospace" },
      formatter: (params: any) => {
        const i = params[0].dataIndex;
        const d = byDate.get(dates[i])!;
        const pct = delayedData[i].value;
        const p50 = p50Data[i]; const p75 = p75Data[i]; const p90 = p90Data[i];
        const percLine = p50 != null ? `p50 ${p50}m · p75 ${p75}m · p90 ${p90}m<br/>` : "";
        const tripsLine = tripsRaw[i] != null ? `~${tripsRaw[i]} trenes en ruta<br/>` : "";
        return `<b>${dates[i]}</b><br/>${pct}% con retraso · max ${d.maxMin}min<br/>${percLine}${tripsLine}${d.delayedSum.toLocaleString("es")} / ${d.totalSum.toLocaleString("es")} paradas`;
      },
    },
    legend: {
      data: ["Con retraso", "A tiempo", "Tendencia", "Trenes en ruta", "p50", "p75", "p90"],
      bottom: 0,
      textStyle: { color: CHART_COLORS.text, fontSize: 11 },
      icon: "roundRect",
      itemWidth: 10,
      itemHeight: 10,
    },
    grid: { left: 52, right: 48, top: 12, bottom: 48 },
    dataZoom: dates.length > 60
      ? [{ type: "inside", startValue: dates[dates.length - 60], endValue: dates[dates.length - 1] }]
      : [],
    xAxis: {
      type: "category",
      data: dates.map(d => d.slice(5)),
      axisLine: { lineStyle: { color: CHART_COLORS.grid } },
      axisTick: { show: false },
      axisLabel: { color: CHART_COLORS.subtext, fontSize: 10, rotate: dates.length > 30 ? 45 : 0 },
    },
    yAxis: [
      {
        type: "value",
        max: 100,
        axisLabel: { formatter: "{value}%", color: CHART_COLORS.subtext, fontSize: 10 },
        splitLine: { lineStyle: { color: CHART_COLORS.grid } },
        axisLine: { show: false },
        axisTick: { show: false },
      },
      {
        type: "value",
        name: "min",
        nameTextStyle: { color: CHART_COLORS.subtext, fontSize: 10 },
        axisLabel: { formatter: "{value}m", color: CHART_COLORS.subtext, fontSize: 10 },
        splitLine: { show: false },
        axisLine: { show: false },
        axisTick: { show: false },
      },
    ],
    series: [
      {
        name: "Con retraso",
        type: "bar",
        stack: "total",
        barMaxWidth: 28,
        yAxisIndex: 0,
        data: delayedData.map(d => d.value),
        itemStyle: { color: CHART_COLORS.delayed, opacity: 0.85, borderRadius: [0, 0, 0, 0] },
        emphasis: { itemStyle: { opacity: 1 } },
      },
      {
        name: "A tiempo",
        type: "bar",
        stack: "total",
        barMaxWidth: 28,
        yAxisIndex: 0,
        data: onTimeData,
        itemStyle: { color: CHART_COLORS.onTime, opacity: 0.35, borderRadius: [3, 3, 0, 0] },
        emphasis: { itemStyle: { opacity: 0.55 } },
      },
      {
        name: "Tendencia",
        type: "line",
        yAxisIndex: 0,
        data: linearRegression(delayedData.map(d => d.value)),
        smooth: false,
        symbol: "none",
        lineStyle: { color: "#f59e0b", width: 2, type: "dashed" },
        itemStyle: { color: "#f59e0b" },
        z: 10,
      },
      {
        name: "Trenes en ruta",
        type: "line",
        yAxisIndex: 0,
        data: tripsData,
        smooth: true,
        symbol: "none",
        lineStyle: { color: "#94a3b8", width: 1.5, type: "dotted" },
        itemStyle: { color: "#94a3b8" },
        connectNulls: false,
      },
      {
        name: "p50",
        type: "line",
        yAxisIndex: 1,
        data: p50Data,
        smooth: true,
        symbol: "circle",
        symbolSize: 4,
        lineStyle: { color: CHART_COLORS.p50, width: 1.5 },
        itemStyle: { color: CHART_COLORS.p50 },
        connectNulls: false,
      },
      {
        name: "p75",
        type: "line",
        yAxisIndex: 1,
        data: p75Data,
        smooth: true,
        symbol: "circle",
        symbolSize: 4,
        lineStyle: { color: CHART_COLORS.p75, width: 1.5 },
        itemStyle: { color: CHART_COLORS.p75 },
        connectNulls: false,
      },
      {
        name: "p90",
        type: "line",
        yAxisIndex: 1,
        data: p90Data,
        smooth: true,
        symbol: "circle",
        symbolSize: 4,
        lineStyle: { color: CHART_COLORS.p90, width: 1.5 },
        itemStyle: { color: CHART_COLORS.p90 },
        connectNulls: false,
      },
    ],
  }, true);
}

export function renderHourly() {
  type HourBucket = { totalSum: number; delayedSum: number; samples: number; trips: number[]; p50s: number[]; p75s: number[]; p90s: number[] };
  const byHour: HourBucket[] = Array.from({ length: 24 }, () =>
    ({ totalSum: 0, delayedSum: 0, samples: 0, trips: [], p50s: [], p75s: [], p90s: [] })
  );
  for (const r of state.historyRecords) {
    const hour = parseInt(r.ts?.slice(11, 13) ?? "0", 10);
    if (isNaN(hour) || hour < 0 || hour > 23) continue;
    byHour[hour].totalSum   += r.total   ?? 0;
    byHour[hour].delayedSum += r.delayed ?? 0;
    byHour[hour].samples++;
    if (r.trips > 0) byHour[hour].trips.push(r.trips);
    if (r.p50 > 0) byHour[hour].p50s.push(r.p50);
    if (r.p75 > 0) byHour[hour].p75s.push(r.p75);
    if (r.p90 > 0) byHour[hour].p90s.push(r.p90);
  }

  const avgArr = (arr: number[]) => arr.length ? +(arr.reduce((a, b) => a + b, 0) / arr.length).toFixed(1) : null;
  const maxSamples = Math.max(...byHour.map(h => h.samples), 1);
  const labels = byHour.map((_, i) => `${String(i).padStart(2, "0")}h`);
  const pctData = byHour.map(h =>
    h.totalSum > 0 ? +(h.delayedSum / h.totalSum * 100).toFixed(1) : 0
  );
  const opacityData = byHour.map(h =>
    h.samples === 0 ? 0.12 : 0.35 + 0.65 * (h.samples / maxSamples)
  );
  const tripsRaw = byHour.map(h => avgArr(h.trips));
  const maxTripsH = Math.max(...tripsRaw.filter(v => v != null) as number[], 1);
  const tripsData = tripsRaw.map(v => v != null ? +(v / maxTripsH * 100).toFixed(1) : null);
  const p50Data = byHour.map(h => avgArr(h.p50s));
  const p75Data = byHour.map(h => avgArr(h.p75s));
  const p90Data = byHour.map(h => avgArr(h.p90s));

  getOrCreateChart().setOption({
    backgroundColor: "transparent",
    tooltip: {
      trigger: "axis",
      backgroundColor: CHART_COLORS.tooltip,
      borderColor: CHART_COLORS.tooltip,
      textStyle: { color: "#fff", fontSize: 12, fontFamily: "JetBrains Mono, monospace" },
      formatter: (params: any) => {
        const i   = params[0].dataIndex;
        const h   = byHour[i];
        const pct = pctData[i];
        if (h.samples === 0) return `<b>${labels[i]}</b><br/>Sin datos`;
        const p50 = p50Data[i]; const p75 = p75Data[i]; const p90 = p90Data[i];
        const percLine = p50 != null ? `p50 ${p50}m · p75 ${p75}m · p90 ${p90}m<br/>` : "";
        const tripsLine = tripsRaw[i] != null ? `~${tripsRaw[i]} trenes en ruta<br/>` : "";
        return `<b>${labels[i]}</b><br/>${pct}% con retraso<br/>${percLine}${tripsLine}${h.delayedSum.toLocaleString("es")} / ${h.totalSum.toLocaleString("es")} paradas<br/>${h.samples} muestras`;
      },
    },
    legend: {
      data: ["% con retraso", "Trenes en ruta", "p50", "p75", "p90"],
      bottom: 0,
      textStyle: { color: CHART_COLORS.text, fontSize: 11 },
      icon: "roundRect",
      itemWidth: 10,
      itemHeight: 10,
    },
    grid: { left: 52, right: 48, top: 12, bottom: 48 },
    xAxis: {
      type: "category",
      data: labels,
      axisLine: { lineStyle: { color: CHART_COLORS.grid } },
      axisTick: { show: false },
      axisLabel: { color: CHART_COLORS.subtext, fontSize: 10 },
    },
    yAxis: [
      {
        type: "value",
        max: 100,
        axisLabel: { formatter: "{value}%", color: CHART_COLORS.subtext, fontSize: 10 },
        splitLine: { lineStyle: { color: CHART_COLORS.grid } },
        axisLine: { show: false },
        axisTick: { show: false },
      },
      {
        type: "value",
        name: "min",
        nameTextStyle: { color: CHART_COLORS.subtext, fontSize: 10 },
        axisLabel: { formatter: "{value}m", color: CHART_COLORS.subtext, fontSize: 10 },
        splitLine: { show: false },
        axisLine: { show: false },
        axisTick: { show: false },
      },
    ],
    series: [
      {
        name: "% con retraso",
        type: "bar",
        yAxisIndex: 0,
        barMaxWidth: 32,
        data: pctData.map((v, i) => ({
          value: v,
          itemStyle: { color: CHART_COLORS.delayed, opacity: opacityData[i], borderRadius: [3, 3, 0, 0] },
        })),
        emphasis: { itemStyle: { opacity: 1 } },
      },
      {
        name: "Trenes en ruta",
        type: "line",
        yAxisIndex: 0,
        data: tripsData,
        smooth: true,
        symbol: "none",
        lineStyle: { color: "#94a3b8", width: 1.5, type: "dotted" },
        itemStyle: { color: "#94a3b8" },
        connectNulls: false,
      },
      {
        name: "p50",
        type: "line",
        yAxisIndex: 1,
        data: p50Data,
        smooth: true,
        symbol: "circle",
        symbolSize: 4,
        lineStyle: { color: CHART_COLORS.p50, width: 1.5 },
        itemStyle: { color: CHART_COLORS.p50 },
        connectNulls: false,
      },
      {
        name: "p75",
        type: "line",
        yAxisIndex: 1,
        data: p75Data,
        smooth: true,
        symbol: "circle",
        symbolSize: 4,
        lineStyle: { color: CHART_COLORS.p75, width: 1.5 },
        itemStyle: { color: CHART_COLORS.p75 },
        connectNulls: false,
      },
      {
        name: "p90",
        type: "line",
        yAxisIndex: 1,
        data: p90Data,
        smooth: true,
        symbol: "circle",
        symbolSize: 4,
        lineStyle: { color: CHART_COLORS.p90, width: 1.5 },
        itemStyle: { color: CHART_COLORS.p90 },
        connectNulls: false,
      },
    ],
  }, true);
}

export function renderTrainTypes(byType: Record<string, any>) {
  const el = document.getElementById("echart-train-type") as HTMLElement | null;
  const section = document.getElementById("train-type-section") as HTMLElement | null;
  if (!el || !section) return;

  if (!byType || Object.keys(byType).length === 0) {
    section.style.display = "none";
    return;
  }

  // Sort by delayed_pct ascending (worst last = displayed at top in ECharts horizontal bar)
  const entries = Object.entries(byType)
    .filter(([, v]) => v.total > 0)
    .sort((a, b) => (a[1].delayed_pct as number) - (b[1].delayed_pct as number));

  if (entries.length === 0) { section.style.display = "none"; return; }

  section.style.display = "block";

  // Narrative: worst type by delayed_pct
  const worst = entries[entries.length - 1];
  const narrativeEl = document.getElementById("train-type-narrative");
  if (narrativeEl && worst) {
    const [name, v] = worst;
    narrativeEl.textContent =
      `El tipo de tren con más retrasos acumulados este periodo es ${name}, ` +
      `con una media de ${v.avg_delay_min} min y un ${Math.round(v.delayed_pct * 100)}% de servicios con retraso.`;
  }

  const names = entries.map(([k]) => k);
  const onTimeData   = entries.map(([, v]) => v.total - v.delayed - v.cancelled);
  const delayedData  = entries.map(([, v]) => v.delayed);
  const cancelledData = entries.map(([, v]) => v.cancelled);

  el.style.height = `${Math.max(180, entries.length * 44)}px`;

  if (!state.trainTypeChart) {
    state.trainTypeChart = echarts.init(el, undefined, { renderer: "canvas" });
    new ResizeObserver(() => state.trainTypeChart?.resize()).observe(el);
  }

  state.trainTypeChart.setOption({
    backgroundColor: "transparent",
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "none" },
      backgroundColor: CHART_COLORS.tooltip,
      borderColor: CHART_COLORS.tooltip,
      textStyle: { color: "#fff", fontSize: 12, fontFamily: "JetBrains Mono, monospace" },
      formatter: (params: any) => {
        const i = params[0].dataIndex;
        const [name, v] = entries[i];
        const pct = Math.round(v.delayed_pct * 100);
        return `<b>${name}</b><br/>${v.total} trenes · ${pct}% con retraso<br/>media ${v.avg_delay_min}m · máx ${v.max_delay_min}m`;
      },
    },
    legend: {
      data: ["En hora", "Con retraso", "Cancelados"],
      bottom: 0,
      textStyle: { color: CHART_COLORS.text, fontSize: 11 },
      icon: "roundRect",
      itemWidth: 10,
      itemHeight: 10,
    },
    grid: { left: 110, right: 80, top: 8, bottom: 32 },
    xAxis: {
      type: "value",
      axisLabel: { color: CHART_COLORS.subtext, fontSize: 10 },
      splitLine: { lineStyle: { color: CHART_COLORS.grid } },
      axisLine: { show: false },
      axisTick: { show: false },
    },
    yAxis: {
      type: "category",
      data: names,
      axisLabel: { color: CHART_COLORS.text, fontSize: 11 },
      axisLine: { show: false },
      axisTick: { show: false },
    },
    series: [
      {
        name: "En hora",
        type: "bar",
        stack: "total",
        barMaxWidth: 28,
        data: onTimeData,
        itemStyle: { color: CHART_COLORS.onTime, opacity: 0.75 },
        label: { show: false },
      },
      {
        name: "Con retraso",
        type: "bar",
        stack: "total",
        barMaxWidth: 28,
        data: delayedData,
        itemStyle: { color: CHART_COLORS.p75, opacity: 0.9 },
        label: {
          show: true,
          position: "right",
          formatter: (p: any) => {
            const i = p.dataIndex;
            const [, v] = entries[i];
            const pct = Math.round(v.delayed_pct * 100);
            return `{pct|${pct}%}  {avg|avg ${v.avg_delay_min}m}`;
          },
          rich: {
            pct: { color: CHART_COLORS.p75, fontSize: 10, fontWeight: 700, fontFamily: "JetBrains Mono, monospace" },
            avg: { color: CHART_COLORS.subtext, fontSize: 10, fontFamily: "JetBrains Mono, monospace" },
          },
        },
      },
      {
        name: "Cancelados",
        type: "bar",
        stack: "total",
        barMaxWidth: 28,
        data: cancelledData,
        itemStyle: { color: "#6b7280", opacity: 0.6, borderRadius: [0, 3, 3, 0] },
        label: { show: false },
      },
    ],
  }, true);
}

export function renderHeatmap() {
  const matrix: { sum: number; count: number }[][] =
    Array.from({ length: 7 }, () =>
      Array.from({ length: 24 }, () => ({ sum: 0, count: 0 }))
    );

  for (const r of state.historyRecords) {
    if (!r.ts || !r.date || r.total === 0) continue;
    const hour = parseInt(r.ts.slice(11, 13), 10);
    if (isNaN(hour) || hour < 0 || hour > 23) continue;
    const dow = (new Date(r.date).getDay() + 6) % 7; // 0=Lun … 6=Dom
    const pct = r.delayed / r.total * 100;
    matrix[dow][hour].sum += pct;
    matrix[dow][hour].count++;
  }

  const days = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];
  const hours = Array.from({ length: 24 }, (_, i) => `${String(i).padStart(2, "0")}h`);

  const data: [number, number, number][] = [];
  for (let dow = 0; dow < 7; dow++) {
    for (let h = 0; h < 24; h++) {
      const cell = matrix[dow][h];
      if (cell.count > 0)
        data.push([h, dow, +(cell.sum / cell.count).toFixed(1)]);
    }
  }

  const maxVal = Math.max(...data.map(d => d[2]), 10);

  getOrCreateChart().setOption({
    backgroundColor: "transparent",
    tooltip: {
      trigger: "item",
      backgroundColor: CHART_COLORS.tooltip,
      borderColor: CHART_COLORS.tooltip,
      textStyle: { color: "#fff", fontSize: 12, fontFamily: "JetBrains Mono, monospace" },
      formatter: (params: any) => {
        const [h, dow, v] = params.data;
        const cell = matrix[dow][h];
        return `<b>${days[dow]} ${hours[h]}</b><br/>${v}% con retraso<br/>${cell.count} muestra${cell.count !== 1 ? "s" : ""}`;
      },
    },
    grid: { left: 36, right: 80, top: 8, bottom: 24 },
    xAxis: {
      type: "category",
      data: hours,
      axisLabel: { color: CHART_COLORS.subtext, fontSize: 9, interval: 1 },
      axisLine: { lineStyle: { color: CHART_COLORS.grid } },
      axisTick: { show: false },
      splitArea: { show: false },
    },
    yAxis: {
      type: "category",
      data: days,
      axisLabel: { color: CHART_COLORS.subtext, fontSize: 10 },
      axisLine: { show: false },
      axisTick: { show: false },
      splitArea: { show: false },
    },
    visualMap: {
      min: 0,
      max: maxVal,
      calculable: false,
      orient: "vertical",
      right: 4,
      top: "center",
      itemHeight: 140,
      textStyle: { color: CHART_COLORS.subtext, fontSize: 9 },
      text: [`${maxVal}%`, "0%"],
      inRange: { color: ["#059669", "#f59e0b", "#dc2626"] },
    },
    series: [{
      type: "heatmap",
      data,
      itemStyle: { borderRadius: 2, borderColor: "var(--bg)", borderWidth: 2 },
      emphasis: { itemStyle: { shadowBlur: 6, shadowColor: "rgba(0,0,0,0.25)" } },
    }],
  }, true);
}
