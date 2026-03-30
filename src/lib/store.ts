import type * as echarts from "echarts";

export const state = {
  activeSvc: "ave-larga-distancia" as string,
  allStations: [] as any[],
  historyRecords: [] as any[],
  activeDays: -1 as number,
  chart: null as echarts.ECharts | null,
  modalSelectedTrainName: "" as string,
  modalSelectedArrival: null as any,
  modalStationName: "" as string,
  modalStationId: "" as string,
  stationFromInsight: false as boolean,
  filteredStations: [] as any[],
  displayedCount: 0 as number,
  scrollObserver: null as IntersectionObserver | null,
  refreshTimer: null as ReturnType<typeof setInterval> | null,
  countdownTimer: null as ReturnType<typeof setInterval> | null,
  nextRefreshAt: 0 as number,
};
