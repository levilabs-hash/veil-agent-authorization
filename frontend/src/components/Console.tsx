"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { fetchEvents, fetchHealth, runDemo } from "@/lib/api";
import type { AuditEvent, Decision, DemoRun } from "@/lib/types";

const STAGES = [
  { id: "email", label: "EXTERNAL EMAIL" },
  { id: "agent", label: "AI AGENT" },
  { id: "action", label: "PROPOSED ACTION" },
  { id: "gateway", label: "VEIL GATEWAY" },
  { id: "engine", label: "POLICY ENGINE" },
  { id: "verdict", label: "DECISION" },
] as const;

type StageId = (typeof STAGES)[number]["id"];

function decisionTone(decision: Decision | null) {
  if (decision === "ALLOW") {
    return {
      text: "text-emerald-300",
      border: "border-emerald-500/50",
      bg: "bg-emerald-950/40",
      chip: "bg-emerald-500 text-emerald-950",
    };
  }
  if (decision === "REVIEW") {
    return {
      text: "text-amber-300",
      border: "border-amber-500/50",
      bg: "bg-amber-950/40",
      chip: "bg-amber-400 text-amber-950",
    };
  }
  if (decision === "BLOCK") {
    return {
      text: "text-rose-300",
      border: "border-rose-500/70",
      bg: "bg-rose-950/50",
      chip: "bg-rose-500 text-white",
    };
  }
  return {
    text: "text-slate-300",
    border: "border-slate-700",
    bg: "bg-slate-900/50",
    chip: "bg-slate-700 text-slate-100",
  };
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid grid-cols-[11rem_1fr] gap-3 border-b border-slate-800/80 py-2.5 last:border-0">
      <dt className="text-xs uppercase tracking-wider text-slate-500">{label}</dt>
      <dd className="font-mono text-sm text-slate-100 break-all">{value}</dd>
    </div>
  );
}

export default function Console() {
  const [connected, setConnected] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [run, setRun] = useState<DemoRun | null>(null);
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [activeStage, setActiveStage] = useState<number>(-1);

  const refreshEvents = useCallback(async () => {
    const next = await fetchEvents();
    setEvents([...next].reverse());
  }, []);

  useEffect(() => {
    let cancelled = false;
    const ping = async () => {
      const ok = await fetchHealth();
      if (!cancelled) setConnected(ok);
      if (ok && !cancelled) {
        try {
          await refreshEvents();
        } catch {
          /* health can succeed while events fail on first boot */
        }
      }
    };
    void ping();
    const timer = window.setInterval(ping, 8000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [refreshEvents]);

  const decision = run?.decision ?? null;
  const tone = useMemo(() => decisionTone(decision), [decision]);

  async function play(scenario: string) {
    setBusy(true);
    setError(null);
    setActiveStage(0);
    try {
      const result = await runDemo(scenario);
      setRun(result);
      for (let i = 0; i < STAGES.length; i += 1) {
        setActiveStage(i);
        await new Promise((resolve) => window.setTimeout(resolve, 160));
      }
      await refreshEvents();
    } catch (err) {
      setRun(null);
      setActiveStage(-1);
      setError(
        err instanceof Error
          ? err.message
          : "Cannot reach the VEIL backend. No security decision was displayed."
      );
    } finally {
      setBusy(false);
    }
  }

  function stageState(index: number, id: StageId) {
    const reached = activeStage >= index;
    const isVerdict = id === "verdict";
    if (!reached) {
      return "border-slate-800 bg-slate-950/60 text-slate-500";
    }
    if (isVerdict && decision === "BLOCK") {
      return "border-rose-500 bg-rose-950 text-white shadow-[0_0_40px_rgba(244,63,94,0.35)]";
    }
    if (isVerdict && decision === "ALLOW") {
      return "border-emerald-500 bg-emerald-950 text-emerald-100";
    }
    if (isVerdict && decision === "REVIEW") {
      return "border-amber-500 bg-amber-950 text-amber-100";
    }
    return "border-cyan-500/60 bg-slate-900 text-cyan-100";
  }

  function verdictLabel() {
    if (!run || activeStage < STAGES.length - 1) return "AWAITING BACKEND";
    if (run.decision === "BLOCK") return "BLOCKED";
    return run.decision;
  }

  return (
    <div className="veil-grid min-h-full flex-1">
      <header className="border-b border-slate-800 bg-slate-950/80 px-6 py-4 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-lg font-semibold tracking-[0.35em] text-cyan-300">
              VEIL
            </p>
            <p className="text-sm text-slate-400">
              Runtime Authorization Gateway for AI Agents
            </p>
          </div>
          <div
            className={`flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-semibold tracking-widest ${
              connected
                ? "border-emerald-500/40 bg-emerald-950/50 text-emerald-300"
                : connected === false
                  ? "border-rose-500/40 bg-rose-950/50 text-rose-300"
                  : "border-slate-700 bg-slate-900 text-slate-400"
            }`}
          >
            <span
              className={`h-2 w-2 rounded-full ${
                connected ? "bg-emerald-400" : "bg-rose-400"
              }`}
            />
            {connected
              ? "PROTECTION ACTIVE"
              : connected === false
                ? "BACKEND UNREACHABLE"
                : "CHECKING BACKEND"}
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-7xl gap-6 px-6 py-6 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
        <section className="space-y-6">
          <div
            className={`rounded-2xl border p-5 ${
              decision === "BLOCK"
                ? "border-rose-500/50 bg-rose-950/20"
                : "border-slate-800 bg-slate-950/70"
            }`}
          >
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-sm font-semibold tracking-widest text-slate-300">
                LIVE ATTACK TRACE
              </h2>
              {run ? (
                <span className={`rounded-full px-2.5 py-1 text-xs font-bold ${tone.chip}`}>
                  {run.decision}
                </span>
              ) : null}
            </div>
            <ol className="space-y-2">
              {STAGES.map((stage, index) => (
                <li key={stage.id} className="flex flex-col items-stretch">
                  <div
                    className={`rounded-lg border px-4 py-3 text-center text-sm font-semibold tracking-wide ${stageState(index, stage.id)}`}
                  >
                    {stage.id === "verdict" ? verdictLabel() : stage.label}
                  </div>
                  {index < STAGES.length - 1 ? (
                    <div className="flex justify-center py-1 text-slate-600">↓</div>
                  ) : null}
                </li>
              ))}
            </ol>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-5">
            <h2 className="mb-4 text-sm font-semibold tracking-widest text-slate-300">
              DEMO CONTROLS
            </h2>
            <p className="mb-4 text-xs text-slate-500">
              Each control calls the VEIL backend. The console does not decide
              ALLOW, REVIEW, or BLOCK.
            </p>
            <div className="grid gap-3 sm:grid-cols-2">
              <button
                type="button"
                disabled={busy}
                onClick={() => void play("attack")}
                className="rounded-lg bg-rose-600 px-4 py-3 text-sm font-semibold text-white hover:bg-rose-500 disabled:opacity-50"
              >
                Run Attack Simulation
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() => void play("read")}
                className="rounded-lg bg-emerald-700 px-4 py-3 text-sm font-semibold text-white hover:bg-emerald-600 disabled:opacity-50"
              >
                Run Safe Read
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() => void play("draft")}
                className="rounded-lg bg-emerald-800 px-4 py-3 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
              >
                Run Draft
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() => void play("unapproved-send")}
                className="rounded-lg bg-amber-600 px-4 py-3 text-sm font-semibold text-amber-950 hover:bg-amber-500 disabled:opacity-50"
              >
                Run Unapproved Send
              </button>
            </div>
          </div>
        </section>

        <section className="space-y-6">
          {error ? (
            <div className="rounded-2xl border border-rose-500/60 bg-rose-950/40 p-4 text-sm text-rose-100">
              <p className="font-semibold">Connection error</p>
              <p className="mt-1 text-rose-200/90">{error}</p>
              <p className="mt-2 text-xs text-rose-300">
                No authorization decision is shown because the backend did not
                respond.
              </p>
            </div>
          ) : null}

          <div className={`rounded-2xl border p-5 ${tone.border} ${tone.bg}`}>
            <h2 className="mb-3 text-sm font-semibold tracking-widest text-slate-300">
              ACTION INSPECTION
            </h2>
            {run ? (
              <dl>
                <Field label="Instruction" value={run.instruction} />
                <Field label="Action" value={run.action.toUpperCase()} />
                <Field label="Recipient" value={run.recipient ?? "—"} />
                <Field label="Resource" value={run.resource ?? "—"} />
                <Field
                  label="Resource classification"
                  value={run.resource_classification ?? "—"}
                />
                <Field label="Instruction provenance" value={run.provenance} />
                <Field label="Risk" value={run.risk} />
                <Field
                  label="Decision"
                  value={run.decision === "BLOCK" ? "BLOCKED" : run.decision}
                />
                <Field label="Reason" value={run.reason} />
                <Field label="Matched rule" value={run.matched_policy_rule} />
                <Field
                  label="Tool executed"
                  value={run.executed ? "YES" : "NO"}
                />
              </dl>
            ) : (
              <p className="text-sm text-slate-500">
                Run a scenario to inspect the backend authorization result.
              </p>
            )}
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-5">
            <h2 className="mb-3 text-sm font-semibold tracking-widest text-slate-300">
              POLICY
            </h2>
            <ul className="space-y-2 text-sm text-slate-200">
              <li className="flex justify-between gap-4">
                <span>Read emails</span>
                <span className="font-mono text-emerald-300">ALLOWED</span>
              </li>
              <li className="flex justify-between gap-4">
                <span>Draft replies</span>
                <span className="font-mono text-emerald-300">ALLOWED</span>
              </li>
              <li className="flex justify-between gap-4">
                <span>Send email</span>
                <span className="font-mono text-amber-300">REQUIRES APPROVAL</span>
              </li>
              <li className="flex justify-between gap-4">
                <span>Confidential resource disclosure</span>
                <span className="font-mono text-rose-300">DENIED</span>
              </li>
              <li className="flex justify-between gap-4">
                <span>Delete files</span>
                <span className="font-mono text-rose-300">DENIED</span>
              </li>
            </ul>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-5">
            <h2 className="mb-3 text-sm font-semibold tracking-widest text-slate-300">
              EVENT / AUDIT STREAM
            </h2>
            {events.length === 0 ? (
              <p className="text-sm text-slate-500">
                No authorization events yet. Run a demo scenario.
              </p>
            ) : (
              <ul className="space-y-2 font-mono text-xs">
                {events.map((event) => (
                  <li
                    key={`${event.timestamp}-${event.action}-${event.decision}`}
                    className="flex flex-wrap gap-x-2 rounded-md border border-slate-800 bg-slate-900/70 px-3 py-2 text-slate-300"
                  >
                    <span className="text-slate-500">
                      {event.timestamp.replace("T", " ").replace("Z", "")}
                    </span>
                    <span>{event.provenance}</span>
                    <span>|</span>
                    <span>{event.action}</span>
                    <span>|</span>
                    <span>{event.resource ?? "—"}</span>
                    <span>|</span>
                    <span
                      className={
                        event.decision === "BLOCK"
                          ? "text-rose-300"
                          : event.decision === "REVIEW"
                            ? "text-amber-300"
                            : "text-emerald-300"
                      }
                    >
                      {event.decision}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
