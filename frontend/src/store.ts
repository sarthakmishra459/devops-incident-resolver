import { create } from "zustand";

import type { Incident, TraceEvent } from "./types";

interface IncidentState {
  selectedIncidentId: string | null;
  liveIncident: Incident | null;
  traces: TraceEvent[];
  selectIncident: (incident: Incident) => void;
  mergeIncident: (incident: Incident) => void;
  addTrace: (trace: TraceEvent) => void;
  setTraces: (traces: TraceEvent[]) => void;
}

export const useIncidentStore = create<IncidentState>((set) => ({
  selectedIncidentId: null,
  liveIncident: null,
  traces: [],
  selectIncident: (incident) =>
    set({ selectedIncidentId: incident.id, liveIncident: incident, traces: [] }),
  mergeIncident: (incident) =>
    set((state) => ({
      liveIncident: state.selectedIncidentId === incident.id ? incident : state.liveIncident
    })),
  addTrace: (trace) =>
    set((state) => {
      if (state.traces.some((item) => item.id === trace.id)) {
        return state;
      }
      return { traces: [...state.traces, trace].slice(-300) };
    }),
  setTraces: (traces) => set({ traces })
}));
