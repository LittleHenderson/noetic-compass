/* ── CAS Forex — Quick Start Page ── */

import { useCallback, useEffect, useState } from "react";
import { GlassPanel } from "../components/GlassPanel";
import { QuickStartItem } from "../components/QuickStartItem";
import type { QuickStartStatus } from "../components/QuickStartItem";
import "./QuickStartPage.css";
import {
  fetchHealth,
  fetchStackHealth,
  fetchAutonomousLoopHealth,
  fetchPushSubscriptions,
  fetchWebhookSubscriptions,
} from "../data/api";
import { fetchOperatorBriefing } from "../data/operatorBriefingApi";

type MilestoneKey =
  | "api"
  | "mt5"
  | "mt4"
  | "autowake"
  | "loop"
  | "pwa"
  | "notifications"
  | "briefing";

interface Milestone {
  key: MilestoneKey;
  title: string;
  status: QuickStartStatus;
  detail: string;
}

const PWA_STORAGE_KEY = "cas_forex_quick_start_pwa_installed";

function readPwaInstalled(): boolean {
  if (typeof window === "undefined") return false;
  return window.localStorage.getItem(PWA_STORAGE_KEY) === "true";
}

function writePwaInstalled(value: boolean): void {
  if (typeof window === "undefined") return;
  if (value) {
    window.localStorage.setItem(PWA_STORAGE_KEY, "true");
  } else {
    window.localStorage.removeItem(PWA_STORAGE_KEY);
  }
}

function findStackCheckStatus(
  checks: Array<{ name: string; status: string }> | undefined,
  needle: string,
): string | null {
  if (!checks) return null;
  const hit = checks.find((c) =>
    (c.name || "").toLowerCase().includes(needle.toLowerCase()),
  );
  return hit ? (hit.status || "").toUpperCase() : null;
}

export function QuickStartPage() {
  const [milestones, setMilestones] = useState<Milestone[]>(initialMilestones());
  const [expanded, setExpanded] = useState<Record<MilestoneKey, boolean>>({
    api: false,
    mt5: false,
    mt4: false,
    autowake: false,
    loop: false,
    pwa: false,
    notifications: false,
    briefing: false,
  });
  const [refreshing, setRefreshing] = useState(false);
  const [refreshedAt, setRefreshedAt] = useState<string | null>(null);
  const [pwaInstalled, setPwaInstalled] = useState<boolean>(readPwaInstalled());

  const runChecks = useCallback(async () => {
    setRefreshing(true);
    setMilestones((prev) =>
      prev.map((m) =>
        m.key === "pwa" ? m : { ...m, status: "running" as QuickStartStatus },
      ),
    );

    const [
      health,
      stack,
      loopHealth,
      briefing,
      pushSubs,
      webhookSubs,
    ] = await Promise.all([
      fetchHealth(),
      fetchStackHealth(),
      fetchAutonomousLoopHealth(),
      fetchOperatorBriefing(),
      fetchPushSubscriptions(),
      fetchWebhookSubscriptions(),
    ]);

    // 1. API server
    const apiOk =
      !!health && (health.status || "").toLowerCase() === "healthy";

    // 2. MT5 terminal — looked up via stack checks
    const mt5Status = findStackCheckStatus(stack?.checks, "mt5-terminal");
    const mt5Ok = mt5Status === "OK" || mt5Status === "PASS";

    // 3. Autowake supervisor — looked up via stack checks
    const autowakeStatus = findStackCheckStatus(
      stack?.checks,
      "autowake-supervisor",
    );
    const autowakeOk = autowakeStatus === "OK" || autowakeStatus === "PASS";

    // 4. Autonomous loop firing
    const loopStatus = (loopHealth?.overall_status || "").toUpperCase();
    const loopOk =
      !!loopHealth &&
      (loopStatus === "OK" ||
        loopStatus === "HEALTHY" ||
        loopStatus === "FIRING" ||
        loopStatus === "GREEN" ||
        (loopHealth.cycles_today ?? 0) > 0);

    // 5. PWA — self-marked
    const pwaOk = pwaInstalled;

    // 6. Notifications
    const pushCount = pushSubs?.total_subscriptions ?? 0;
    const webhookCount = webhookSubs?.total_subscriptions ?? 0;
    const notificationsOk = pushCount > 0 || webhookCount > 0;

    // 7. Operator briefing
    const briefingOk =
      !!briefing && (briefing.plain_english_briefing || "").trim().length > 0;

    setMilestones([
      {
        key: "api",
        title: "API server reachable",
        status: apiOk ? "done" : health === null ? "error" : "pending",
        detail:
          "Run uvicorn: `py -3.12 -m uvicorn api.server:app --host 127.0.0.1 --port 8765` in a new PowerShell window.",
      },
      {
        key: "mt5",
        title: "MT5 terminal connected + Algo Trading ON",
        status: mt5Ok ? "done" : "pending",
        detail:
          "Start MT5 logged into your broker (demo first). Then ENABLE ALGO TRADING — this is a MetaTrader button that only YOU can click; no app is allowed to flip it (MetaTrader requires your consent before a robot can trade). Click the 'Algo Trading' button in the MT5 top toolbar until it turns green. Belt-and-suspenders: Tools → Options → Expert Advisors → tick 'Allow Algorithmic Trading' → OK.",
      },
      {
        key: "mt4",
        title: "MT4 (optional — file-mailbox EA path)",
        status: "pending",
        detail:
          "MT4 has no Python API (MetaQuotes only built one for MT5), so there is no MT5-style 'connect' for MT4 — it works via a file-mailbox Expert Advisor, paper/demo only. To use MT4: set MT4_ENABLED=true and MT4_MAILBOX_DIR=<shared folder>, attach the CAS Forex EA (.mq4) to a chart in MT4, and in MT4 turn on AutoTrading + allow the EA to read/write files. Leave this off if you're on MT5.",
      },
      {
        key: "autowake",
        title: "Autowake supervisor running",
        status: autowakeOk ? "done" : "pending",
        detail:
          "In a new PowerShell window: `py -3.12 scripts/run_autowake_supervisor.py --tick-interval-seconds 300 --execute-cycle --summary-only`",
      },
      {
        key: "loop",
        title: "Autonomous loop is firing",
        status: loopOk ? "done" : "pending",
        detail:
          "Confirm steps 1-3 first; if all green and still stalled, run `scripts/run_session_autowake_runner.py --summary-only` to manually trigger a cycle.",
      },
      {
        key: "pwa",
        title: "PWA installed on phone",
        status: pwaOk ? "done" : "pending",
        detail:
          "On your phone, open `http://<your-LAN-IP>:5174`, then Add to Home Screen. When done, mark this step complete with the button below.",
      },
      {
        key: "notifications",
        title: "Notification subscription registered",
        status: notificationsOk ? "done" : "pending",
        detail:
          "On the Settings page, enable push notifications (recommended) or add a webhook URL.",
      },
      {
        key: "briefing",
        title: "Operator briefing returns plain English",
        status: briefingOk ? "done" : "pending",
        detail:
          "If unavailable, restart uvicorn so the new routes register.",
      },
    ]);
    setRefreshedAt(new Date().toISOString());
    setRefreshing(false);
  }, [pwaInstalled]);

  useEffect(() => {
    runChecks();
    const id = window.setInterval(runChecks, 30_000);
    return () => window.clearInterval(id);
  }, [runChecks]);

  const toggle = (key: MilestoneKey) =>
    setExpanded((prev) => ({ ...prev, [key]: !prev[key] }));

  const togglePwaSelfMark = () => {
    const next = !pwaInstalled;
    setPwaInstalled(next);
    writePwaInstalled(next);
  };

  const allDone = milestones.every((m) => m.status === "done");
  const doneCount = milestones.filter((m) => m.status === "done").length;

  return (
    <div className="quick-start-page">
      <GlassPanel
        title="Quick Start"
        subtitle="What you need to run CAS Forex — checked against live endpoints"
      >
        <div className="quick-start-controls">
          <button
            type="button"
            className="quick-start-refresh-button"
            onClick={runChecks}
            disabled={refreshing}
          >
            {refreshing ? "Checking..." : "Run all checks now"}
          </button>
          <span className="quick-start-progress">
            {doneCount} / {milestones.length} ready
          </span>
          {refreshedAt && (
            <span className="quick-start-refreshed-at">
              Last checked {new Date(refreshedAt).toLocaleTimeString()}
            </span>
          )}
        </div>
        <p className="quick-start-intro">
          This page lists operational milestones — what is running, what is not,
          and how to bring missing pieces online. It is a factual checklist, not
          trade advice. Auto-refreshes every 30 seconds.
        </p>
        <div className="quick-start-list">
          {milestones.map((m, idx) => (
            <div key={m.key}>
              <QuickStartItem
                index={idx + 1}
                title={m.title}
                status={m.status}
                detail={m.detail}
                expanded={!!expanded[m.key]}
                onToggle={() => toggle(m.key)}
              />
              {m.key === "pwa" && (
                <div className="quick-start-pwa-self-mark">
                  <button
                    type="button"
                    className="quick-start-pwa-button"
                    onClick={togglePwaSelfMark}
                  >
                    {pwaInstalled
                      ? "Mark as not installed"
                      : "Mark as installed on phone"}
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
        {allDone && (
          <div className="quick-start-completion-banner">
            Stack ready. Loop firing. Phone connected. You're set.
          </div>
        )}
      </GlassPanel>
    </div>
  );
}

function initialMilestones(): Milestone[] {
  return [
    {
      key: "api",
      title: "API server reachable",
      status: "pending",
      detail: "",
    },
    {
      key: "mt5",
      title: "MT5 terminal connected + Algo Trading ON",
      status: "pending",
      detail: "",
    },
    {
      key: "mt4",
      title: "MT4 (optional — file-mailbox EA path)",
      status: "pending",
      detail: "",
    },
    {
      key: "autowake",
      title: "Autowake supervisor running",
      status: "pending",
      detail: "",
    },
    {
      key: "loop",
      title: "Autonomous loop is firing",
      status: "pending",
      detail: "",
    },
    {
      key: "pwa",
      title: "PWA installed on phone",
      status: "pending",
      detail: "",
    },
    {
      key: "notifications",
      title: "Notification subscription registered",
      status: "pending",
      detail: "",
    },
    {
      key: "briefing",
      title: "Operator briefing returns plain English",
      status: "pending",
      detail: "",
    },
  ];
}
