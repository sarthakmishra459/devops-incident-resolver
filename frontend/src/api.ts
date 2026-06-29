import axios from "axios";

import type { DemoIncident, Incident, IncidentSeverity, StreamEvent, TraceEvent } from "./types";

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "/api",
  timeout: 20_000
});

export async function listIncidents(): Promise<Incident[]> {
  const response = await client.get<{ incidents: Incident[] }>("/incidents");
  return response.data.incidents;
}

export async function getIncident(id: string): Promise<Incident> {
  const response = await client.get<{ incident: Incident }>(`/incidents/${id}`);
  return response.data.incident;
}

export async function createIncident(payload: {
  title: string;
  description: string;
  severity: IncidentSeverity;
  demo_key?: string;
}): Promise<Incident> {
  const response = await client.post<{ incident: Incident }>("/incidents", payload);
  return response.data.incident;
}

export async function uploadIncident(payload: {
  title: string;
  description: string;
  severity: IncidentSeverity;
  file: File;
}): Promise<Incident> {
  const form = new FormData();
  form.append("title", payload.title);
  form.append("description", payload.description);
  form.append("severity", payload.severity);
  form.append("file", payload.file);
  const response = await client.post<{ incident: Incident }>("/incidents/upload", form, {
    headers: { "Content-Type": "multipart/form-data" }
  });
  return response.data.incident;
}

export async function listDemos(): Promise<DemoIncident[]> {
  const response = await client.get<{ demos: DemoIncident[] }>("/demos");
  return response.data.demos;
}

export async function listTrace(id: string): Promise<TraceEvent[]> {
  const response = await client.get<{ trace: TraceEvent[] }>(`/incidents/${id}/trace`);
  return response.data.trace;
}

export function subscribeToIncident(
  id: string,
  onEvent: (event: StreamEvent) => void,
  onError: () => void
): EventSource {
  const base = import.meta.env.VITE_API_BASE_URL ?? "/api";
  const source = new EventSource(`${base}/incidents/${id}/stream`);
  source.onmessage = (message) => onEvent(JSON.parse(message.data) as StreamEvent);
  const eventTypes = ["trace", "trace.replay", "incident.updated", "incident.resolved"];
  eventTypes.forEach((type) => {
    source.addEventListener(type, (message) => {
      onEvent(JSON.parse((message as MessageEvent).data) as StreamEvent);
    });
  });
  source.onerror = onError;
  return source;
}
