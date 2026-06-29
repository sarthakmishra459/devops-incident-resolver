import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import clsx from "clsx";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock3,
  Cpu,
  Database,
  FileText,
  Gauge,
  Play,
  RefreshCw,
  Terminal,
  Upload
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ReactNode } from "react";

import {
  createIncident,
  listDemos,
  listIncidents,
  listTrace,
  subscribeToIncident,
  uploadIncident
} from "./api";
import { useIncidentStore } from "./store";
import type { DemoIncident, Incident, IncidentSeverity, TraceEvent } from "./types";

const severityStyles: Record<IncidentSeverity, string> = {
  low: "bg-emerald-100 text-emerald-800",
  medium: "bg-sky-100 text-sky-800",
  high: "bg-amber-100 text-amber-900",
  critical: "bg-rose-100 text-rose-900"
};

export function App() {
  const queryClient = useQueryClient();
  const [manualTitle, setManualTitle] = useState("Disk usage exceeded 95%");
  const [manualDescription, setManualDescription] = useState(
    "Production alert fired for payments-db-01. Disk usage is above 95% and checkout latency is rising."
  );
  const [severity, setSeverity] = useState<IncidentSeverity>("critical");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const { selectedIncidentId, liveIncident, traces, selectIncident, mergeIncident, addTrace, setTraces } =
    useIncidentStore();

  const incidentsQuery = useQuery({ queryKey: ["incidents"], queryFn: listIncidents, refetchInterval: 5000 });
  const demosQuery = useQuery({ queryKey: ["demos"], queryFn: listDemos });

  const createMutation = useMutation({
    mutationFn: createIncident,
    onSuccess: (incident) => {
      selectIncident(incident);
      void queryClient.invalidateQueries({ queryKey: ["incidents"] });
    }
  });

  const uploadMutation = useMutation({
    mutationFn: uploadIncident,
    onSuccess: (incident) => {
      selectIncident(incident);
      setUploadFile(null);
      void queryClient.invalidateQueries({ queryKey: ["incidents"] });
    }
  });

  useEffect(() => {
    const first = incidentsQuery.data?.[0];
    if (!selectedIncidentId && first) {
      selectIncident(first);
    }
  }, [incidentsQuery.data, selectIncident, selectedIncidentId]);

  useEffect(() => {
    if (!selectedIncidentId) {
      return;
    }
    let source: EventSource | null = null;
    void listTrace(selectedIncidentId).then(setTraces);
    source = subscribeToIncident(
      selectedIncidentId,
      (event) => {
        if (event.trace) {
          addTrace(event.trace);
        }
        if (event.incident) {
          mergeIncident(event.incident);
          void queryClient.invalidateQueries({ queryKey: ["incidents"] });
        }
      },
      () => undefined
    );
    return () => source?.close();
  }, [addTrace, mergeIncident, queryClient, selectedIncidentId, setTraces]);

  const incidents = incidentsQuery.data ?? [];
  const selectedIncident =
    liveIncident ?? incidents.find((incident) => incident.id === selectedIncidentId) ?? incidents[0] ?? null;
  const metrics = useMemo(() => buildMetrics(selectedIncident, traces), [selectedIncident, traces]);

  function launchManual() {
    createMutation.mutate({
      title: manualTitle,
      description: manualDescription,
      severity
    });
  }

  function launchDemo(demo: DemoIncident) {
    createMutation.mutate({
      title: demo.title,
      description: demo.description,
      severity: demo.severity,
      demo_key: demo.key
    });
  }

  function launchUpload() {
    if (!uploadFile) {
      return;
    }
    uploadMutation.mutate({
      title: manualTitle,
      description: manualDescription,
      severity,
      file: uploadFile
    });
  }

  return (
    <main className="min-h-screen bg-[#eef2e8] text-ink">
      <header className="border-b border-line bg-white/90">
        <div className="mx-auto flex max-w-[1600px] flex-col gap-4 px-5 py-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-normal">Adaptive DevOps Incident Resolver</h1>
            <p className="mt-1 text-sm text-slate-600">Planner, executor, tools, reflection, and final report.</p>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Metric icon={Clock3} label="Resolution" value={`${metrics.resolution}s`} />
            <Metric icon={Gauge} label="Confidence" value={`${metrics.confidence}%`} />
            <Metric icon={RefreshCw} label="Retries" value={`${metrics.retries}`} />
            <Metric icon={Terminal} label="Tools" value={`${metrics.tools}`} />
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-[1600px] grid-cols-1 gap-4 px-5 py-5 xl:grid-cols-[360px_1fr_420px]">
        <section className="space-y-4">
          <Panel title="New Incident" icon={AlertTriangle}>
            <div className="space-y-3">
              <input
                value={manualTitle}
                onChange={(event) => setManualTitle(event.target.value)}
                className="w-full rounded border border-line bg-white px-3 py-2 text-sm outline-none focus:border-signal"
              />
              <textarea
                value={manualDescription}
                onChange={(event) => setManualDescription(event.target.value)}
                rows={4}
                className="w-full resize-none rounded border border-line bg-white px-3 py-2 text-sm outline-none focus:border-signal"
              />
              <div className="grid grid-cols-[1fr_auto] gap-2">
                <select
                  value={severity}
                  onChange={(event) => setSeverity(event.target.value as IncidentSeverity)}
                  className="rounded border border-line bg-white px-3 py-2 text-sm outline-none focus:border-signal"
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </select>
                <button
                  onClick={launchManual}
                  disabled={createMutation.isPending}
                  className="inline-flex items-center justify-center gap-2 rounded bg-signal px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
                >
                  <Play size={16} /> Start
                </button>
              </div>
              <div className="grid grid-cols-[1fr_auto] gap-2">
                <input
                  type="file"
                  accept=".log,.txt,text/plain"
                  onChange={(event) => setUploadFile(event.target.files?.[0] ?? null)}
                  className="min-w-0 rounded border border-line bg-white px-3 py-2 text-sm"
                />
                <button
                  onClick={launchUpload}
                  disabled={!uploadFile || uploadMutation.isPending}
                  className="inline-flex items-center justify-center gap-2 rounded border border-signal px-3 py-2 text-sm font-medium text-signal disabled:opacity-50"
                >
                  <Upload size={16} /> Upload
                </button>
              </div>
            </div>
          </Panel>

          <Panel title="Demo Incidents" icon={Cpu}>
            <div className="grid gap-2">
              {(demosQuery.data ?? []).map((demo) => (
                <button
                  key={demo.key}
                  onClick={() => launchDemo(demo)}
                  className="flex items-center justify-between rounded border border-line bg-white px-3 py-2 text-left text-sm hover:border-signal"
                >
                  <span className="font-medium">{demo.title}</span>
                  <span className={clsx("rounded px-2 py-1 text-xs", severityStyles[demo.severity])}>
                    {demo.severity}
                  </span>
                </button>
              ))}
            </div>
          </Panel>

          <Panel title="Incident History" icon={Database}>
            <div className="space-y-2">
              {incidents.map((incident) => (
                <button
                  key={incident.id}
                  onClick={() => selectIncident(incident)}
                  className={clsx(
                    "w-full rounded border px-3 py-3 text-left text-sm",
                    selectedIncident?.id === incident.id
                      ? "border-signal bg-white shadow-soft"
                      : "border-line bg-white/70 hover:border-signal"
                  )}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-semibold">{incident.title}</span>
                    <StatusBadge status={incident.status} />
                  </div>
                  <p className="mt-1 line-clamp-2 text-xs text-slate-600">{incident.description}</p>
                </button>
              ))}
              {!incidents.length && <EmptyState text="No incidents yet." />}
            </div>
          </Panel>
        </section>

        <section className="space-y-4">
          <Panel title="Investigation Timeline" icon={Activity}>
            <Timeline traces={traces} />
          </Panel>
          <Panel title="Final Incident Report" icon={FileText}>
            <Report incident={selectedIncident} />
          </Panel>
        </section>

        <section className="space-y-4">
          <Panel title="Live Terminal Output" icon={Terminal}>
            <TerminalPanel traces={traces} />
          </Panel>
          <Panel title="Metrics" icon={Gauge}>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={metrics.chart}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#d8ded2" />
                  <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Bar dataKey="value" fill="#0f766e" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Panel>
        </section>
      </div>
    </main>
  );
}

function Panel({
  title,
  icon: Icon,
  children
}: {
  title: string;
  icon: typeof Activity;
  children: ReactNode;
}) {
  return (
    <section className="rounded border border-line bg-panel p-4 shadow-sm">
      <div className="mb-3 flex items-center gap-2">
        <Icon size={18} className="text-signal" />
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">{title}</h2>
      </div>
      {children}
    </section>
  );
}

function Metric({ icon: Icon, label, value }: { icon: typeof Clock3; label: string; value: string }) {
  return (
    <div className="min-w-[130px] rounded border border-line bg-panel px-3 py-2">
      <div className="flex items-center gap-2 text-xs text-slate-600">
        <Icon size={14} />
        {label}
      </div>
      <div className="mt-1 text-lg font-semibold">{value}</div>
    </div>
  );
}

function StatusBadge({ status }: { status: Incident["status"] }) {
  const styles = {
    created: "bg-slate-100 text-slate-700",
    investigating: "bg-amber-100 text-amber-900",
    resolved: "bg-emerald-100 text-emerald-800",
    failed: "bg-rose-100 text-rose-900"
  };
  return <span className={clsx("rounded px-2 py-1 text-xs", styles[status])}>{status}</span>;
}

function Timeline({ traces }: { traces: TraceEvent[] }) {
  if (!traces.length) {
    return <EmptyState text="Waiting for agent trace." />;
  }
  return (
    <div className="max-h-[520px] space-y-3 overflow-auto pr-1">
      {traces.map((trace) => (
        <article key={trace.id} className="rounded border border-line bg-white p-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="rounded bg-slate-100 px-2 py-1 text-xs font-medium uppercase text-slate-700">
              {trace.role}
            </span>
            <time className="text-xs text-slate-500">{new Date(trace.created_at).toLocaleTimeString()}</time>
          </div>
          <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-800">{trimLong(trace.message, 900)}</p>
        </article>
      ))}
    </div>
  );
}

function TerminalPanel({ traces }: { traces: TraceEvent[] }) {
  const terminal = traces.filter((trace) => trace.role === "executor");
  return (
    <pre className="terminal-scroll h-[410px] overflow-auto rounded bg-[#172026] p-3 text-xs leading-5 text-[#dce8dc]">
      {terminal.length
        ? terminal
            .map((trace) => {
              const tool = typeof trace.metadata.tool === "string" ? trace.metadata.tool : "executor";
              return `$ ${tool}\n${trace.message}`;
            })
            .join("\n\n")
        : "$ waiting-for-tool-output"}
    </pre>
  );
}

function Report({ incident }: { incident: Incident | null }) {
  if (!incident) {
    return <EmptyState text="Select or create an incident." />;
  }
  if (!incident.report) {
    return (
      <div className="flex items-center gap-2 rounded border border-line bg-white p-4 text-sm text-slate-700">
        <RefreshCw size={16} className="animate-spin text-signal" />
        Investigation status: {incident.status}
      </div>
    );
  }
  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-2">
        <div className="rounded border border-line bg-white p-3">
          <h3 className="text-xs font-semibold uppercase text-slate-500">Root Cause</h3>
          <p className="mt-2 text-sm leading-6">{incident.report.root_cause}</p>
        </div>
        <div className="rounded border border-line bg-white p-3">
          <h3 className="text-xs font-semibold uppercase text-slate-500">Suggested Fix</h3>
          <p className="mt-2 text-sm leading-6">{incident.report.suggested_fix}</p>
        </div>
      </div>
      <div className="rounded border border-line bg-white p-3">
        <h3 className="mb-2 text-xs font-semibold uppercase text-slate-500">Evidence</h3>
        <div className="space-y-2">
          {incident.report.evidence.map((item) => (
            <p key={item} className="rounded bg-slate-50 p-2 text-xs leading-5 text-slate-700">
              {trimLong(item, 700)}
            </p>
          ))}
        </div>
      </div>
    </div>
  );
}

function EmptyState({ text }: { text: string }) {
  return <div className="rounded border border-dashed border-line bg-white/60 p-4 text-sm text-slate-500">{text}</div>;
}

function buildMetrics(incident: Incident | null, traces: TraceEvent[]) {
  const report = incident?.report;
  const confidence = report?.confidence ?? 0;
  const retries = report?.retries ?? traces.filter((trace) => trace.role === "reflector").length;
  const tools = report?.tools_executed ?? traces.filter((trace) => trace.role === "executor").length;
  const resolution = report ? Math.max(1, Math.round(report.resolution_time_ms / 1000)) : 0;
  return {
    confidence,
    retries,
    tools,
    resolution,
    chart: [
      { name: "Confidence", value: confidence },
      { name: "Retries", value: retries },
      { name: "Tools", value: tools },
      { name: "Seconds", value: resolution }
    ]
  };
}

function trimLong(value: string, max: number) {
  return value.length > max ? `${value.slice(0, max)}...` : value;
}
