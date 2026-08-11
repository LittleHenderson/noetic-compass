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
  fetchMobileReadinessLatest,
  fetchMobileProofSessionLatest,
  fetchMobileFinalVerificationLatest,
  fetchMobileVerificationPlanLatest,
  fetchMobileVerificationSessionLatest,
  downloadMobileDebugApk,
  downloadMobileReleaseApk,
  postMobilePhoneProof,
  refreshMobileVerificationPlan,
  refreshMobileVerificationSession,
  refreshMobileFinalVerification,
  type MobileFinalVerification,
  type MobileNextVerificationAction,
  type MobileProofSession,
  type MobileVerificationPlan,
  type MobilePhoneVerificationSession,
  type MobileReadinessLatest,
  type MobilePhoneProofPayload,
} from "../data/api";
import { fetchOwnerPairing, isLoopbackHost } from "../data/ownerAuthApi";
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

interface LaunchSequenceStep {
  title: string;
  status: QuickStartStatus;
  detail: string;
  href?: string;
}

type PhoneProofSubmitStatus = "idle" | "skipped" | "submitting" | "recorded" | "failed";

interface PhoneProofSubmitState {
  status: PhoneProofSubmitStatus;
  detail: string;
}

const PWA_STORAGE_KEY = "cas_forex_quick_start_pwa_installed";

interface BeforeInstallPromptEvent extends Event {
  readonly platforms: string[];
  readonly userChoice: Promise<{ outcome: "accepted" | "dismissed"; platform: string }>;
  prompt: () => Promise<void>;
}

function isStandalonePwa(): boolean {
  if (typeof window === "undefined") return false;
  const standaloneNavigator = window.navigator as Navigator & { standalone?: boolean };
  const canReadDisplayMode = typeof window.matchMedia === "function";
  return (canReadDisplayMode
    && (window.matchMedia("(display-mode: standalone)").matches
      || window.matchMedia("(display-mode: fullscreen)").matches))
    || standaloneNavigator.standalone === true;
}

function readDisplayMode(): MobilePhoneProofPayload["display_mode"] {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") return "unknown";
  for (const mode of ["standalone", "fullscreen", "minimal-ui"] as const) {
    if (window.matchMedia(`(display-mode: ${mode})`).matches) return mode;
  }
  return "browser";
}

function readAppSurface(): MobilePhoneProofPayload["app_surface"] {
  if (typeof window === "undefined") return "web";
  const maybeCapacitor = (window as unknown as { Capacitor?: unknown }).Capacitor;
  if (maybeCapacitor || window.location.protocol === "capacitor:") return "apk";
  return "pwa";
}

function buildPhoneProofPayload(): MobilePhoneProofPayload {
  const nav = window.navigator;
  const tz = Intl.DateTimeFormat().resolvedOptions().timeZone || "";
  return {
    source: "quick-start",
    app_surface: readAppSurface(),
    url_origin: window.location.origin,
    url_path: window.location.pathname,
    display_mode: readDisplayMode(),
    standalone_pwa: isStandalonePwa(),
    user_agent: nav.userAgent || "",
    platform: nav.platform || "",
    language: nav.language || "",
    timezone: tz,
    viewport_width: window.innerWidth,
    viewport_height: window.innerHeight,
    screen_width: window.screen?.width ?? 0,
    screen_height: window.screen?.height ?? 0,
    device_pixel_ratio: window.devicePixelRatio || 1,
    max_touch_points: nav.maxTouchPoints || 0,
    online: nav.onLine,
  };
}

function shouldSubmitPhoneProof(payload: MobilePhoneProofPayload): boolean {
  if (payload.app_surface === "apk") return true;
  if (payload.standalone_pwa) return true;
  if (["standalone", "fullscreen", "minimal-ui"].includes(payload.display_mode || "")) {
    return true;
  }

  const userAgent = (payload.user_agent || "").toLowerCase();
  const platform = (payload.platform || "").toLowerCase();
  const phoneHint = ["mobile", "iphone", "ipod", "android"].some(
    (token) => userAgent.includes(token) || platform.includes(token),
  );
  if (!phoneHint) return false;

  const widths = [
    payload.viewport_width,
    payload.screen_width,
  ].filter((value): value is number => Number.isFinite(value || 0) && Boolean(value));
  const narrowWidth = widths.length ? Math.min(...widths) : null;
  const hasTouch = Boolean((payload.max_touch_points ?? 0) > 0);
  return hasTouch || Boolean(narrowWidth && narrowWidth <= 480);
}

function readPwaInstalled(): boolean {
  if (typeof window === "undefined") return false;
  return isStandalonePwa() || window.localStorage.getItem(PWA_STORAGE_KEY) === "true";
}

function writePwaInstalled(value: boolean): void {
  if (typeof window === "undefined") return;
  if (value) {
    window.localStorage.setItem(PWA_STORAGE_KEY, "true");
  } else {
    window.localStorage.removeItem(PWA_STORAGE_KEY);
  }
}

function recordFlag(record: Record<string, unknown> | null | undefined, key: string): boolean {
  return record?.[key] === true;
}

function mobileEvidenceShowsInstalledMode(
  readiness: MobileReadinessLatest | null,
  verificationSession: MobilePhoneVerificationSession | null,
  proofSession: MobileProofSession | null,
): boolean {
  return Boolean(
    readiness?.phone_proof_installed_mode
      || readiness?.phone_observation_installed_mode
      || readiness?.apk_runtime_installed_mode
      || recordFlag(verificationSession, "phone_proof_installed_mode")
      || recordFlag(verificationSession, "phone_observation_installed_mode")
      || recordFlag(verificationSession, "apk_runtime_installed_mode")
      || recordFlag(verificationSession?.proof_state, "installed_mode_detected")
      || recordFlag(proofSession?.phone_watch_status, "installed_mode_detected"),
  );
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
  const [installPrompt, setInstallPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [installingPwa, setInstallingPwa] = useState(false);
  const [mobileReadiness, setMobileReadiness] = useState<MobileReadinessLatest | null>(null);
  const [mobileProofSession, setMobileProofSession] = useState<MobileProofSession | null>(null);
  const [mobileVerificationSession, setMobileVerificationSession] = useState<MobilePhoneVerificationSession | null>(null);
  const [mobileVerificationPlan, setMobileVerificationPlan] = useState<MobileVerificationPlan | null>(null);
  const [mobileFinalVerification, setMobileFinalVerification] = useState<MobileFinalVerification | null>(null);
  const [phonePairingUrl, setPhonePairingUrl] = useState<string | null>(null);
  const [nativePairingUrl, setNativePairingUrl] = useState<string | null>(null);
  const [phonePairingLanModeEnabled, setPhonePairingLanModeEnabled] = useState<boolean | null>(null);
  const [phoneProofSubmit, setPhoneProofSubmit] = useState<PhoneProofSubmitState>({
    status: "idle",
    detail: "Waiting",
  });

  const submitCurrentDeviceProof = useCallback(async (mode: "auto" | "manual" = "manual") => {
    const payload = buildPhoneProofPayload();
    const phoneLikeEnoughForAuto = shouldSubmitPhoneProof(payload);
    if (!phoneLikeEnoughForAuto && mode === "auto") {
      setPhoneProofSubmit({ status: "skipped", detail: "Desktop QA" });
      return;
    }
    setPhoneProofSubmit({
      status: "submitting",
      detail: payload.app_surface === "apk"
        ? "Native APK"
        : payload.standalone_pwa
          ? "Installed PWA"
          : phoneLikeEnoughForAuto
            ? "Phone browser"
            : "Manual QA",
    });
    const proof = await postMobilePhoneProof(payload);
    if (proof) {
      setPhoneProofSubmit({
        status: "recorded",
        detail: proof.phone_browser_verified
          ? "Network verified"
          : proof.phone_browser_observed
            ? "Runtime observed"
            : "Recorded",
      });
      const [latest, session, plan, finalVerification] = await Promise.all([
        fetchMobileReadinessLatest(),
        fetchMobileVerificationSessionLatest(),
        fetchMobileVerificationPlanLatest(),
        fetchMobileFinalVerificationLatest(),
      ]);
      if (latest) setMobileReadiness(latest);
      if (session) setMobileVerificationSession(session);
      if (plan) setMobileVerificationPlan(plan);
      if (finalVerification) setMobileFinalVerification(finalVerification);
    } else {
      setPhoneProofSubmit({ status: "failed", detail: "Submit failed" });
    }
  }, []);

  const loadOwnerPairing = useCallback(async (): Promise<boolean> => {
    if (!isLoopbackHost()) return false;
    const pairing = await fetchOwnerPairing();
    const pairingUrl = pairing?.pairing_urls?.[0] ?? null;
    const nativeUrl = pairing?.native_pairing_urls?.[0] ?? null;
    setPhonePairingUrl(pairingUrl);
    setNativePairingUrl(nativeUrl);
    setPhonePairingLanModeEnabled(pairing?.lan_mode_enabled ?? null);
    return Boolean(pairingUrl || nativeUrl || pairing);
  }, []);

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
      mobileLatest,
      proofSession,
      verificationSession,
      verificationPlan,
      finalVerification,
    ] = await Promise.all([
      fetchHealth(),
      fetchStackHealth(),
      fetchAutonomousLoopHealth(),
      fetchOperatorBriefing(),
      fetchPushSubscriptions(),
      fetchWebhookSubscriptions(),
      fetchMobileReadinessLatest(),
      fetchMobileProofSessionLatest(),
      fetchMobileVerificationSessionLatest(),
      fetchMobileVerificationPlanLatest(),
      fetchMobileFinalVerificationLatest(),
    ]);
    setMobileReadiness(mobileLatest);
    setMobileProofSession(proofSession);
    setMobileVerificationSession(verificationSession);
    setMobileVerificationPlan(verificationPlan);
    setMobileFinalVerification(finalVerification);
    void loadOwnerPairing();

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

    // 5. PWA - installed mode, browser prompt, owner-marked, or mobile evidence.
    const mobileInstalledModeOk = mobileEvidenceShowsInstalledMode(
      mobileLatest,
      verificationSession,
      proofSession,
    );
    const pwaOk = pwaInstalled || isStandalonePwa() || mobileInstalledModeOk;

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
          "Run the guarded API launcher: `python scripts/run_api_server.py --host 127.0.0.1 --port 8765 --workers 1` in a new PowerShell window.",
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
        detail: mobileInstalledModeOk
          ? "Installed-app/PWA mode is already present in the current mobile evidence. For full phone completion, open Quick Start from the real phone over LAN/direct API so the proof is non-localhost and verified."
          : "On your phone, open `http://<your-LAN-IP>:4173`, use the browser install prompt or Add to Home Screen, then CAS Forex opens from the phone icon.",
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
  }, [loadOwnerPairing, pwaInstalled]);

  useEffect(() => {
    runChecks();
    const id = window.setInterval(runChecks, 30_000);
    return () => window.clearInterval(id);
  }, [runChecks]);

  useEffect(() => {
    if (!isLoopbackHost()) return;
    const retryDelays = [0, 1_500, 5_000, 10_000];
    let cancelled = false;
    const timers: number[] = [];
    const runAttempt = (index: number) => {
      const timer = window.setTimeout(() => {
        if (cancelled) return;
        void loadOwnerPairing().then((loaded) => {
          if (!loaded && !cancelled && index + 1 < retryDelays.length) {
            runAttempt(index + 1);
          }
        });
      }, retryDelays[index] ?? 0);
      timers.push(timer);
    };
    runAttempt(0);
    return () => {
      cancelled = true;
      timers.forEach((timer) => window.clearTimeout(timer));
    };
  }, [loadOwnerPairing]);

  useEffect(() => {
    void submitCurrentDeviceProof("auto");
  }, [submitCurrentDeviceProof]);

  useEffect(() => {
    const onBeforeInstallPrompt = (event: Event) => {
      event.preventDefault();
      setInstallPrompt(event as BeforeInstallPromptEvent);
    };
    const onAppInstalled = () => {
      setInstallPrompt(null);
      setPwaInstalled(true);
      writePwaInstalled(true);
    };
    window.addEventListener("beforeinstallprompt", onBeforeInstallPrompt);
    window.addEventListener("appinstalled", onAppInstalled);
    if (isStandalonePwa()) {
      setPwaInstalled(true);
      writePwaInstalled(true);
    }
    return () => {
      window.removeEventListener("beforeinstallprompt", onBeforeInstallPrompt);
      window.removeEventListener("appinstalled", onAppInstalled);
    };
  }, []);

  const toggle = (key: MilestoneKey) =>
    setExpanded((prev) => ({ ...prev, [key]: !prev[key] }));

  const togglePwaSelfMark = () => {
    const next = !pwaInstalled;
    setPwaInstalled(next);
    writePwaInstalled(next);
  };

  const installPwa = async () => {
    if (!installPrompt) return;
    setInstallingPwa(true);
    try {
      await installPrompt.prompt();
      const choice = await installPrompt.userChoice;
      setInstallPrompt(null);
      if (choice.outcome === "accepted") {
        setPwaInstalled(true);
        writePwaInstalled(true);
      }
    } catch {
      setInstallPrompt(null);
    } finally {
      setInstallingPwa(false);
    }
  };

  const allDone = milestones.every((m) => m.status === "done");
  const doneCount = milestones.filter((m) => m.status === "done").length;
  const launchSequence = buildLaunchSequence(milestones);

  return (
    <div className="quick-start-page">
      <GlassPanel
        title="Quick Start"
        subtitle="What you need to run CAS Forex — checked against live endpoints"
      >
        <MobileReadinessSummary
          readiness={mobileReadiness}
          proofSession={mobileProofSession}
          verificationSession={mobileVerificationSession}
          verificationPlan={mobileVerificationPlan}
          finalVerification={mobileFinalVerification}
          phonePairingUrl={phonePairingUrl}
          nativePairingUrl={nativePairingUrl}
          phonePairingLanModeEnabled={phonePairingLanModeEnabled}
          phoneProofSubmit={phoneProofSubmit}
          onSubmitDeviceProof={submitCurrentDeviceProof}
          onVerificationSessionUpdated={setMobileVerificationSession}
          onProofSessionUpdated={setMobileProofSession}
          onVerificationPlanUpdated={setMobileVerificationPlan}
          onFinalVerificationUpdated={setMobileFinalVerification}
        />
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
        <LaunchSequencePanel steps={launchSequence} />
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
                <div className="quick-start-pwa-actions">
                  {installPrompt && !pwaInstalled ? (
                    <button
                      type="button"
                      className="quick-start-pwa-button primary"
                      disabled={installingPwa}
                      onClick={() => void installPwa()}
                    >
                      {installingPwa ? "Opening install..." : "Install app"}
                    </button>
                  ) : null}
                  <button
                    type="button"
                    className="quick-start-pwa-button"
                    onClick={togglePwaSelfMark}
                  >
                    {pwaInstalled
                      ? "Mark as not installed"
                      : "Mark installed"}
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

function MobileReadinessSummary({
  readiness,
  proofSession,
  verificationSession,
  verificationPlan,
  finalVerification,
  phonePairingUrl,
  nativePairingUrl,
  phonePairingLanModeEnabled,
  phoneProofSubmit,
  onSubmitDeviceProof,
  onVerificationSessionUpdated,
  onProofSessionUpdated,
  onVerificationPlanUpdated,
  onFinalVerificationUpdated,
}: {
  readiness: MobileReadinessLatest | null;
  proofSession: MobileProofSession | null;
  verificationSession: MobilePhoneVerificationSession | null;
  verificationPlan: MobileVerificationPlan | null;
  finalVerification: MobileFinalVerification | null;
  phonePairingUrl: string | null;
  nativePairingUrl: string | null;
  phonePairingLanModeEnabled: boolean | null;
  phoneProofSubmit: PhoneProofSubmitState;
  onSubmitDeviceProof: () => Promise<void>;
  onVerificationSessionUpdated: (session: MobilePhoneVerificationSession | null) => void;
  onProofSessionUpdated: (session: MobileProofSession | null) => void;
  onVerificationPlanUpdated: (plan: MobileVerificationPlan | null) => void;
  onFinalVerificationUpdated: (verification: MobileFinalVerification | null) => void;
}) {
  const [copiedAction, setCopiedAction] = useState<string | null>(null);
  const [manualCopyValue, setManualCopyValue] = useState<string | null>(null);
  const [refreshingVerificationSession, setRefreshingVerificationSession] = useState(false);
  const [refreshingVerificationPlan, setRefreshingVerificationPlan] = useState(false);
  const [refreshingFinalVerification, setRefreshingFinalVerification] = useState(false);
  const packageReady = readiness?.package_ready_for_phone_install ?? false;
  const physicalPhoneVerified = readiness?.physical_phone_verified ?? false;
  const phoneBrowserObserved = readiness?.phone_browser_observed ?? false;
  const phoneBrowserVerified = readiness?.phone_browser_verified ?? false;
  const apkPairingVerified = readiness?.apk_install_pairing_verified ?? physicalPhoneVerified;
  const apkArtifact = readiness?.apk_artifact ?? null;
  const apkTransferReady = apkArtifact?.transfer_ready ?? false;
  const releaseApkArtifact = readiness?.release_apk_artifact ?? null;
  const releaseApkTransferReady = releaseApkArtifact?.transfer_ready ?? false;
  const dockerAvailable = readiness?.docker_available ?? false;
  const dockerEngineDetail = formatDockerEngineState(readiness);
  const dockerInstallAttemptDetail = formatDockerInstallAttemptState(readiness);
  const dockerInstallAttemptGood = readiness?.docker_desktop_install_attempt_status === "installed_or_started";
  const proofSessionDetail = formatProofSessionState(proofSession);
  const proofSessionGood = proofSession?.status === "verified";
  const verificationSessionDetail = formatVerificationSessionState(verificationSession);
  const verificationSessionGood = verificationSession?.status === "verified";
  const finalVerificationDetail = formatFinalVerificationState(finalVerification);
  const finalVerificationGood = finalVerification?.status === "verified";
  const status = readiness?.status ?? "UNAVAILABLE";
  const generatedAt = readiness?.generated_at
    ? new Date(readiness.generated_at).toLocaleString()
    : "not generated";
  const activePhoneGeneratedAt = phoneBrowserVerified && readiness?.phone_proof_generated_at
    ? readiness.phone_proof_generated_at
    : phoneBrowserObserved && readiness?.phone_observation_generated_at
      ? readiness.phone_observation_generated_at
      : readiness?.phone_proof_generated_at || readiness?.phone_observation_generated_at || null;
  const activePhoneFresh = phoneBrowserVerified
    ? readiness?.phone_proof_fresh
    : phoneBrowserObserved
      ? readiness?.phone_observation_fresh
      : readiness?.phone_proof_fresh ?? readiness?.phone_observation_fresh ?? false;
  const activePhoneAgeSeconds = phoneBrowserVerified
    ? readiness?.phone_proof_age_seconds
    : phoneBrowserObserved
      ? readiness?.phone_observation_age_seconds
      : readiness?.phone_proof_age_seconds ?? readiness?.phone_observation_age_seconds ?? null;
  const activePhoneExpiresAt = phoneBrowserVerified
    ? readiness?.phone_proof_expires_at
    : phoneBrowserObserved
      ? readiness?.phone_observation_expires_at
      : readiness?.phone_proof_expires_at || readiness?.phone_observation_expires_at || null;
  const activePhoneMaxAgeHours = phoneBrowserVerified
    ? readiness?.phone_proof_max_age_hours
    : phoneBrowserObserved
      ? readiness?.phone_observation_max_age_hours
      : readiness?.phone_proof_max_age_hours ?? readiness?.phone_observation_max_age_hours ?? null;
  const phoneProofTimestamp = activePhoneGeneratedAt
    ? new Date(activePhoneGeneratedAt).toLocaleString()
    : null;
  const hasPhoneRuntimeEvidence = Boolean(activePhoneGeneratedAt);
  const phoneProofLabel = phoneBrowserVerified
    ? "Browser verified"
    : phoneBrowserObserved
      ? "Phone-like observed"
      : hasPhoneRuntimeEvidence
        ? "Stale proof"
        : "Not observed";
  const phoneProofDetail = phoneProofTimestamp
    ? `${phoneProofLabel} ${phoneProofTimestamp}`
    : phoneProofLabel;
  const phoneProofFreshness = hasPhoneRuntimeEvidence
    ? formatPhoneProofFreshness(
        activePhoneFresh,
        activePhoneAgeSeconds,
        activePhoneExpiresAt,
        activePhoneMaxAgeHours,
      )
    : "No timestamp";
  const phoneFreshnessMetricLabel = phoneBrowserVerified
    ? "Phone proof freshness"
    : phoneBrowserObserved
      ? "Phone observation freshness"
      : "Phone proof freshness";
  const phoneProofFreshnessGood = Boolean(activePhoneFresh && (phoneBrowserVerified || phoneBrowserObserved));
  const phoneProofSubmitGood = phoneProofSubmit.status === "recorded";
  const phoneProofSubmitValue = phoneProofSubmit.status === "idle"
    ? "Waiting"
    : `${phoneProofSubmit.detail}`;
  const installedMode = readiness?.phone_proof_installed_mode
    || readiness?.phone_observation_installed_mode
    || false;
  const apkPairingGeneratedAt = readiness?.apk_install_pairing_generated_at
    ? new Date(readiness.apk_install_pairing_generated_at).toLocaleString()
    : null;
  const apkProofDetail = apkPairingVerified
    ? apkPairingGeneratedAt
      ? `Verified ${apkPairingGeneratedAt}`
      : "Verified"
    : "Not verified";
  const apkRuntimeDetail = formatApkRuntimeState(readiness);
  const apkRuntimeGood = readiness?.apk_runtime_verified ?? false;
  const apkAttemptDetail = formatApkAttemptState(readiness);
  const apkAttemptGood = readiness?.apk_install_pairing_attempt_status === "verified";
  const apkArtifactDetail = apkTransferReady
    ? `${formatBytes(apkArtifact?.size_bytes)} ${shortHash(apkArtifact?.sha256)}`
    : "Missing build";
  const releaseApkArtifactDetail = releaseApkTransferReady
    ? `${formatBytes(releaseApkArtifact?.size_bytes)} ${shortHash(releaseApkArtifact?.sha256)}`
    : readiness?.android_release_apk_exists
      ? `Built ${shortHash(readiness?.android_release_apk_sha256)}`
      : "Missing release";
  const androidReleaseSigningGood = readiness?.android_release_signing_ready ?? false;
  const androidReleaseSigningDetail = formatAndroidReleaseSigningState(readiness);
  const androidDeviceReady = readiness?.android_device_ready ?? false;
  const androidDeviceDetail = formatAndroidDeviceState(readiness);
  const networkEvidence = physicalPhoneVerified
    ? "Native launch"
    : phoneBrowserVerified
      ? `LAN/proxy ${readiness?.phone_observation_client_host_source || "verified"}`
      : phoneBrowserObserved && readiness?.phone_observation_local_runtime_only
        ? "Localhost only"
        : phoneBrowserObserved
          ? "Observed, not verified"
          : "Not observed";
  const phoneApiRoute = readiness?.phone_proof_api_base_network_path
    || readiness?.phone_observation_api_base_network_path
    || null;
  const phoneApiHost = readiness?.phone_proof_api_base_host
    || readiness?.phone_observation_api_base_host
    || null;
  const phoneApiRouteGood = Boolean(phoneApiRoute && !["loopback_api", "unknown"].includes(phoneApiRoute));
  const phoneApiRouteDetail = formatPhoneApiRoute(phoneApiRoute, phoneApiHost);
  const pairedApiBasesGood = readiness?.paired_api_bases_reachable ?? false;
  const pairedApiBasesDetail = readiness?.paired_api_bases_detail
    || readiness?.paired_api_bases_status
    || "Not checked";
  const probeAttemptsDetail = formatProbeAttemptSummary(readiness);
  const probeAttemptsGood = readinessChecksSucceeded(readiness, [
    "web_phone_smoke",
    "owner_pairing_payload",
    "paired_api_bases",
  ]);
  const phoneWebBase = readiness?.web_base || "http://<YOUR-PC-LAN-IP>:4173";
  const phoneQuickStartUrl = readiness?.phone_quick_start_url || quickStartUrl(phoneWebBase);
  const phoneProofUrl = phonePairingUrl || phoneQuickStartUrl;
  const phoneProofUrlMode = phonePairingUrl ? "pairing" : "quick-start";
  const lanAccessValue = phonePairingLanModeEnabled === null
    ? "Unknown"
    : phonePairingLanModeEnabled
      ? "ON"
      : "OFF";
  const pairingNeedsLan = phoneProofUrlMode === "pairing" && phonePairingLanModeEnabled === false;
  const phoneProofCopyLabel = phoneProofUrlMode === "pairing" ? "Copy pairing URL" : "Copy phone URL";
  const phoneProofCopyStatusLabel = phoneProofUrlMode === "pairing" ? "Pairing URL" : "Phone URL";
  const commands = readiness?.verification_commands ?? null;
  const proofSessionCommands: Record<string, string> = proofSession?.owner_commands ?? {};
  const verificationPlanCommands: Record<string, string> = verificationPlan?.owner_commands ?? {};
  const finalVerificationCommands: Record<string, string> = finalVerification?.owner_commands ?? {};
  const proofSessionCommand = commands?.mobile_proof_session || "npm --prefix ui run mobile:proof-session";
  const verificationSessionCommand = commands?.phone_verification_session || "npm --prefix ui run mobile:verify-session";
  const phoneProofCommand = commands?.phone_proof_watcher || "npm --prefix ui run mobile:phone-proof -- --exit-code-on-missing";
  const readinessCommand = commands?.mobile_readiness || `npm --prefix ui run mobile:readiness -- --web-base ${phoneWebBase}`;
  const finalVerificationCommand = finalVerificationCommands.mobile_final_verification
    || verificationPlanCommands.mobile_final_verification
    || proofSessionCommands.mobile_final_verification
    || "npm --prefix ui run mobile:finish";
  const finalVerificationWatchCommand = finalVerificationCommands.mobile_final_verification_watch
    || verificationPlanCommands.mobile_final_verification_watch
    || proofSessionCommands.mobile_final_verification_watch
    || "npm --prefix ui run mobile:finish -- --watch-phone";
  const finalVerificationWatchAllCommand = finalVerificationCommands.mobile_final_verification_watch_all
    || verificationPlanCommands.mobile_final_verification_watch_all
    || proofSessionCommands.mobile_final_verification_watch_all
    || commands?.mobile_final_verification_watch_all
    || "npm --prefix ui run mobile:finish -- --watch-all";
  const finalVerificationWatchAllLiveLinksCommand = finalVerificationCommands.mobile_final_verification_watch_all_live_links
    || verificationPlanCommands.mobile_final_verification_watch_all_live_links
    || proofSessionCommands.mobile_final_verification_watch_all_live_links
    || commands?.mobile_final_verification_watch_all_live_links
    || (finalVerificationWatchAllCommand.includes("--print-live-pairing-links")
    ? finalVerificationWatchAllCommand
    : `${finalVerificationWatchAllCommand} --print-live-pairing-links`);
  const apkBuildCommand = apkArtifact?.build_command || commands?.apk_debug_build || "npm --prefix ui run mobile:apk:debug";
  const apkBuildAllCommand = commands?.apk_build_all || "npm --prefix ui run mobile:apk:build-all";
  const apkReleaseSigningSetupCommand = readiness?.android_release_signing?.setup_command || commands?.apk_release_signing_setup || "npm --prefix ui run mobile:apk:setup-release-signing";
  const apkReleaseCommand = readiness?.android_release_signing?.build_command || commands?.apk_release_build || "npm --prefix ui run mobile:apk:release";
  const apkDeviceCommand = commands?.apk_device_list || "npm --prefix ui run mobile:apk:devices";
  const apkProofCommand = commands?.apk_wait_install_pair || apkArtifact?.wait_install_pair_command || apkArtifact?.install_pair_command || commands?.apk_install_pair || "npm --prefix ui run mobile:apk:wait-install-pair";
  const dockerCheckCommand = commands?.docker_engine_diagnose || commands?.docker_engine_check || "npm --prefix ui run mobile:docker-check";
  const dockerInstallCommand = commands?.docker_desktop_install || "npm --prefix ui run mobile:docker-install";
  const dockerElevatedInstallCommand = commands?.docker_desktop_install_elevated || readiness?.docker_desktop_elevated_install_command || "npm --prefix ui run mobile:docker-install-elevated";
  const nextActions = readiness?.next_verification_actions ?? [];
  const verificationPlanText = buildVerificationPlanText({
    readiness,
    proofSession,
    verificationSession,
    verificationPlan,
    finalVerification,
    phoneProofUrl,
    phoneQuickStartUrl,
    phoneProofUrlMode,
    pairingNeedsLan,
    proofSessionCommand,
    verificationSessionCommand,
    finalVerificationCommand,
    finalVerificationWatchCommand,
    finalVerificationWatchAllCommand,
    finalVerificationWatchAllLiveLinksCommand,
    phoneProofCommand,
    readinessCommand,
    apkDeviceCommand,
    apkProofCommand,
    dockerCheckCommand,
    dockerInstallCommand,
    dockerElevatedInstallCommand,
    nextActions,
  });

  const copyAction = async (label: string, value: string) => {
    try {
      await writeClipboardText(value);
      setCopiedAction(`${label} copied`);
      setManualCopyValue(null);
      window.setTimeout(() => setCopiedAction(null), 2400);
    } catch {
      setCopiedAction("Copy unavailable");
      setManualCopyValue(redactSensitiveDisplayValue(value));
      window.setTimeout(() => setCopiedAction(null), 2400);
    }
  };

  const downloadApkAction = async () => {
    try {
      const { blob, filename } = await downloadMobileDebugApk();
      startBrowserDownload(blob, filename);
      setCopiedAction("APK download started");
      setManualCopyValue(null);
      window.setTimeout(() => setCopiedAction(null), 2400);
    } catch {
      setCopiedAction("APK download unavailable");
      setManualCopyValue(apkBuildCommand);
      window.setTimeout(() => setCopiedAction(null), 2400);
    }
  };

  const downloadReleaseApkAction = async () => {
    try {
      const { blob, filename } = await downloadMobileReleaseApk();
      startBrowserDownload(blob, filename);
      setCopiedAction("Release APK download started");
      setManualCopyValue(null);
      window.setTimeout(() => setCopiedAction(null), 2400);
    } catch {
      setCopiedAction("Release APK download unavailable");
      setManualCopyValue(apkReleaseCommand);
      window.setTimeout(() => setCopiedAction(null), 2400);
    }
  };

  const refreshVerificationSessionAction = async () => {
    setRefreshingVerificationSession(true);
    try {
      const [session, proofSessionLatest, verificationPlanLatest] = await Promise.all([
        refreshMobileVerificationSession(),
        fetchMobileProofSessionLatest(),
        refreshMobileVerificationPlan(),
      ]);
      if (session) {
        onVerificationSessionUpdated(session);
        onProofSessionUpdated(proofSessionLatest);
        onVerificationPlanUpdated(verificationPlanLatest);
        setCopiedAction("Session refreshed");
        setManualCopyValue(session.written_paths?.readme_path || session.default_output_paths?.readme_path || null);
      } else {
        setCopiedAction("Session refresh failed");
        setManualCopyValue(verificationSessionCommand);
      }
    } finally {
      setRefreshingVerificationSession(false);
      window.setTimeout(() => setCopiedAction(null), 2400);
    }
  };

  const refreshVerificationPlanAction = async () => {
    setRefreshingVerificationPlan(true);
    try {
      const plan = await refreshMobileVerificationPlan();
      if (plan) {
        onVerificationPlanUpdated(plan);
        setCopiedAction("Plan refreshed");
        setManualCopyValue(plan.written_paths?.readme_path || plan.default_output_paths?.readme_path || null);
      } else {
        setCopiedAction("Plan refresh failed");
        setManualCopyValue("npm --prefix ui run mobile:verification-plan");
      }
    } finally {
      setRefreshingVerificationPlan(false);
      window.setTimeout(() => setCopiedAction(null), 2400);
    }
  };

  const refreshFinalVerificationAction = async () => {
    setRefreshingFinalVerification(true);
    try {
      const [finalLatest, proofSessionLatest, verificationPlanLatest] = await Promise.all([
        refreshMobileFinalVerification(),
        fetchMobileProofSessionLatest(),
        refreshMobileVerificationPlan(),
      ]);
      if (finalLatest) {
        onFinalVerificationUpdated(finalLatest);
        onProofSessionUpdated(proofSessionLatest);
        onVerificationPlanUpdated(verificationPlanLatest);
        setCopiedAction("Final refreshed");
        setManualCopyValue(finalLatest.written_paths?.readme_path || finalLatest.default_output_paths?.readme_path || null);
      } else {
        setCopiedAction("Final refresh failed");
        setManualCopyValue(finalVerificationCommand);
      }
    } finally {
      setRefreshingFinalVerification(false);
      window.setTimeout(() => setCopiedAction(null), 2400);
    }
  };

  return (
    <div className="quick-start-mobile-readiness">
      <div className="quick-start-mobile-readiness-header">
        <div>
          <div className="quick-start-mobile-readiness-title">Phone/Web Readiness Evidence</div>
          <div className="quick-start-mobile-readiness-subtitle">
            {readiness?.summary ?? "No mobile readiness evidence has been loaded yet."}
          </div>
        </div>
        <span className={`quick-start-readiness-pill ${packageReady ? "ready" : "pending"}`}>
          {packageReady ? "PACKAGE READY" : status}
        </span>
      </div>
      <div className="quick-start-mobile-readiness-grid">
        <ReadinessMetric label="Web/PWA/APK package" value={packageReady ? "Ready" : "Needs evidence"} good={packageReady} />
        <ReadinessMetric label="Phone runtime proof" value={phoneProofDetail} good={phoneBrowserVerified} />
        <ReadinessMetric label={phoneFreshnessMetricLabel} value={phoneProofFreshness} good={phoneProofFreshnessGood} />
        <ReadinessMetric label="This device proof" value={phoneProofSubmitValue} good={phoneProofSubmitGood} />
        <ReadinessMetric label="LAN access" value={lanAccessValue} good={phonePairingLanModeEnabled === true} />
        <ReadinessMetric label="Phone network proof" value={networkEvidence} good={physicalPhoneVerified || phoneBrowserVerified} />
        <ReadinessMetric label="Phone API route" value={phoneApiRouteDetail} good={phoneApiRouteGood} />
        <ReadinessMetric label="Paired API bases" value={pairedApiBasesDetail} good={pairedApiBasesGood} />
        <ReadinessMetric label="Probe attempts" value={probeAttemptsDetail} good={probeAttemptsGood} />
        <ReadinessMetric label="Debug APK" value={apkArtifactDetail} good={apkTransferReady} />
        <ReadinessMetric label="Release APK" value={releaseApkArtifactDetail} good={releaseApkTransferReady} />
        <ReadinessMetric label="Release signing" value={androidReleaseSigningDetail} good={androidReleaseSigningGood} />
        <ReadinessMetric label="Android device" value={androidDeviceDetail} good={androidDeviceReady} />
        <ReadinessMetric label="Android APK proof" value={apkProofDetail} good={apkPairingVerified} />
        <ReadinessMetric label="APK runtime" value={apkRuntimeDetail} good={apkRuntimeGood} />
        <ReadinessMetric label="APK last attempt" value={apkAttemptDetail} good={apkAttemptGood} />
        <ReadinessMetric label="Installed app mode" value={installedMode ? "Detected" : "Not detected"} good={installedMode} />
        <ReadinessMetric label="Docker Engine" value={dockerEngineDetail} good={dockerAvailable} />
        <ReadinessMetric label="Docker install attempt" value={dockerInstallAttemptDetail} good={dockerInstallAttemptGood} />
        <ReadinessMetric label="Proof session" value={proofSessionDetail} good={proofSessionGood} />
        <ReadinessMetric label="Verify session" value={verificationSessionDetail} good={verificationSessionGood} />
        <ReadinessMetric label="Final verification" value={finalVerificationDetail} good={finalVerificationGood} />
        <ReadinessMetric label="Generated" value={generatedAt} good={Boolean(readiness?.generated_at)} />
      </div>
      <PhoneProofQrCode
        url={phoneProofUrl}
        mode={phoneProofUrlMode}
        fallbackUrl={phoneQuickStartUrl}
        pairingNeedsLan={pairingNeedsLan}
      />
      {nativePairingUrl ? (
        <PhoneProofQrCode url={nativePairingUrl} mode="apk-pairing" fallbackUrl={phoneQuickStartUrl} />
      ) : null}
      <NextVerificationActions
        actions={nextActions}
        phoneProofUrl={phoneProofUrl}
        phoneProofUrlMode={phoneProofUrlMode}
        pairingNeedsLan={pairingNeedsLan}
        onCopy={copyAction}
      />
      <div className="quick-start-mobile-readiness-actions" aria-label="Phone verification actions">
        <button
          type="button"
          className="quick-start-readiness-action primary"
          onClick={() => void copyAction("Verification plan", verificationPlanText)}
        >
          Copy verification plan
        </button>
        <button
          type="button"
          className="quick-start-readiness-action primary"
          onClick={() => void copyAction("Final verification command", finalVerificationCommand)}
        >
          Copy finish
        </button>
        <button
          type="button"
          className="quick-start-readiness-action"
          onClick={() => void copyAction("Final verification watcher", finalVerificationWatchAllCommand)}
        >
          Copy finish watcher
        </button>
        <button
          type="button"
          className="quick-start-readiness-action"
          onClick={() => void copyAction("Final verification live-link watcher", finalVerificationWatchAllLiveLinksCommand)}
        >
          Copy live watcher
        </button>
        <button
          type="button"
          className="quick-start-readiness-action"
          disabled={refreshingFinalVerification}
          onClick={() => void refreshFinalVerificationAction()}
        >
          {refreshingFinalVerification ? "Refreshing final" : "Refresh final"}
        </button>
        <button
          type="button"
          className="quick-start-readiness-action"
          disabled={refreshingVerificationPlan}
          onClick={() => void refreshVerificationPlanAction()}
        >
          {refreshingVerificationPlan ? "Refreshing plan" : "Refresh plan"}
        </button>
        <button
          type="button"
          className="quick-start-readiness-action"
          disabled={phoneProofSubmit.status === "submitting"}
          onClick={() => void onSubmitDeviceProof()}
        >
          {phoneProofSubmit.status === "submitting" ? "Submitting proof" : "Submit device proof"}
        </button>
        <button
          type="button"
          className="quick-start-readiness-action"
          onClick={() => void copyAction(phoneProofCopyStatusLabel, phoneProofUrl)}
        >
          {phoneProofCopyLabel}
        </button>
        <button
          type="button"
          className="quick-start-readiness-action"
          onClick={() => void copyAction("Phone proof command", phoneProofCommand)}
        >
          Copy phone proof
        </button>
        <button
          type="button"
          className="quick-start-readiness-action"
          disabled={refreshingVerificationSession}
          onClick={() => void refreshVerificationSessionAction()}
        >
          {refreshingVerificationSession ? "Refreshing session" : "Refresh session"}
        </button>
        <button
          type="button"
          className="quick-start-readiness-action"
          onClick={() => void copyAction("Proof session command", proofSessionCommand)}
        >
          Copy proof session
        </button>
        <button
          type="button"
          className="quick-start-readiness-action"
          onClick={() => void copyAction("Verification session command", verificationSessionCommand)}
        >
          Copy verify session
        </button>
        <button
          type="button"
          className="quick-start-readiness-action"
          onClick={() => void copyAction("Readiness command", readinessCommand)}
        >
          Copy readiness check
        </button>
        <button
          type="button"
          className="quick-start-readiness-action"
          onClick={() => void downloadApkAction()}
        >
          Download debug APK
        </button>
        <button
          type="button"
          className="quick-start-readiness-action"
          onClick={() => void downloadReleaseApkAction()}
        >
          Download release APK
        </button>
        <button
          type="button"
          className="quick-start-readiness-action"
          onClick={() => void copyAction("Release signing setup command", apkReleaseSigningSetupCommand)}
        >
          Copy signing setup
        </button>
        <button
          type="button"
          className="quick-start-readiness-action"
          onClick={() => void copyAction("APK build-all command", apkBuildAllCommand)}
        >
          Copy APK build all
        </button>
        <button
          type="button"
          className="quick-start-readiness-action"
          onClick={() => void copyAction("Release build command", apkReleaseCommand)}
        >
          Copy release build
        </button>
        {nativePairingUrl ? (
          <button
            type="button"
            className="quick-start-readiness-action"
            onClick={() => void copyAction("APK pairing URL", nativePairingUrl)}
          >
            Copy APK pairing URL
          </button>
        ) : null}
        <button
          type="button"
          className="quick-start-readiness-action"
          onClick={() => void copyAction("Android devices command", apkDeviceCommand)}
        >
          Copy Android devices
        </button>
        <button
          type="button"
          className="quick-start-readiness-action"
          onClick={() => void copyAction("APK proof command", apkProofCommand)}
        >
          Copy APK proof
        </button>
        <button
          type="button"
          className="quick-start-readiness-action"
          onClick={() => void copyAction("Docker diagnosis command", dockerCheckCommand)}
        >
          Copy Docker diagnosis
        </button>
        <button
          type="button"
          className="quick-start-readiness-action"
          onClick={() => void copyAction("Docker install command", dockerInstallCommand)}
        >
          Copy Docker install
        </button>
        <button
          type="button"
          className="quick-start-readiness-action"
          onClick={() => void copyAction("Elevated Docker install command", dockerElevatedInstallCommand)}
        >
          Copy elevated Docker install
        </button>
        {copiedAction ? (
          <span className="quick-start-readiness-copy-status">{copiedAction}</span>
        ) : null}
        {manualCopyValue ? (
          <code className="quick-start-readiness-manual-copy">{manualCopyValue}</code>
        ) : null}
      </div>
      {readiness?.remaining_external_gates?.length ? (
        <div className="quick-start-mobile-readiness-gates">
          {readiness.remaining_external_gates.map((gate) => (
            <div key={gate}>{gate}</div>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function NextVerificationActions({
  actions,
  phoneProofUrl,
  phoneProofUrlMode,
  pairingNeedsLan,
  onCopy,
}: {
  actions: MobileNextVerificationAction[];
  phoneProofUrl: string;
  phoneProofUrlMode: "pairing" | "quick-start";
  pairingNeedsLan: boolean;
  onCopy: (label: string, value: string) => Promise<void>;
}) {
  if (!actions.length) return null;
  return (
    <div className="quick-start-next-actions" aria-label="Next verification actions">
      <div className="quick-start-next-actions-title">Next verification actions</div>
      <div className="quick-start-next-actions-list">
        {actions.map((action, index) => (
          <NextVerificationActionRow
            action={action}
            index={index}
            key={action.action_id}
            phoneProofUrl={phoneProofUrl}
            phoneProofUrlMode={phoneProofUrlMode}
            pairingNeedsLan={pairingNeedsLan}
            onCopy={onCopy}
          />
        ))}
      </div>
    </div>
  );
}

function buildVerificationPlanText({
  readiness,
  proofSession,
  verificationSession,
  verificationPlan,
  finalVerification,
  phoneProofUrl,
  phoneQuickStartUrl,
  phoneProofUrlMode,
  pairingNeedsLan,
  proofSessionCommand,
  verificationSessionCommand,
  finalVerificationCommand,
  finalVerificationWatchCommand,
  finalVerificationWatchAllCommand,
  finalVerificationWatchAllLiveLinksCommand,
  phoneProofCommand,
  readinessCommand,
  apkDeviceCommand,
  apkProofCommand,
  dockerCheckCommand,
  dockerInstallCommand,
  dockerElevatedInstallCommand,
  nextActions,
}: {
  readiness: MobileReadinessLatest | null;
  proofSession: MobileProofSession | null;
  verificationSession: MobilePhoneVerificationSession | null;
  verificationPlan: MobileVerificationPlan | null;
  finalVerification: MobileFinalVerification | null;
  phoneProofUrl: string;
  phoneQuickStartUrl: string;
  phoneProofUrlMode: "pairing" | "quick-start";
  pairingNeedsLan: boolean;
  proofSessionCommand: string;
  verificationSessionCommand: string;
  finalVerificationCommand: string;
  finalVerificationWatchCommand: string;
  finalVerificationWatchAllCommand: string;
  finalVerificationWatchAllLiveLinksCommand: string;
  phoneProofCommand: string;
  readinessCommand: string;
  apkDeviceCommand: string;
  apkProofCommand: string;
  dockerCheckCommand: string;
  dockerInstallCommand: string;
  dockerElevatedInstallCommand: string;
  nextActions: MobileNextVerificationAction[];
}): string {
  if (verificationPlan?.text?.trim()) {
    const lines = [
      verificationPlan.text.trim(),
      "",
      "Live desktop copy context:",
      `- Phone proof URL mode: ${phoneProofUrlMode}`,
      `- Phone proof URL: ${phoneProofUrl}`,
      `- Phone Quick Start URL: ${phoneQuickStartUrl}`,
    ];
    if (finalVerification) {
      lines.push(
        `- Final verification: ${finalVerification.status}`,
        `- Final summary: ${finalVerification.summary}`,
        `- Final next owner step: ${finalVerification.next_owner_step}`,
        `- Final command: ${finalVerificationCommand}`,
        `- Final watch-all command: ${finalVerificationWatchAllCommand}`,
        `- Final live-link watch command: ${finalVerificationWatchAllLiveLinksCommand}`,
      );
    }
    const backendTarget = verificationPlan.phone_proof_target_url || verificationPlan.phone_quick_start_url || "";
    if (backendTarget && backendTarget !== phoneProofUrl) {
      lines.push(`- Backend saved proof target: ${backendTarget}`);
    }
    if (pairingNeedsLan) {
      lines.push("- Pairing note: turn LAN access ON in Owner Access before scanning this pairing URL.");
    }
    return lines.join("\n");
  }
  const lines = [
    "CAS Forex mobile/web verification plan",
    `Package ready: ${readiness?.package_ready_for_phone_install ? "yes" : "no"}`,
    `Phone browser verified: ${readiness?.phone_browser_verified ? "yes" : "no"}`,
    `Android APK/native pairing verified: ${readiness?.apk_install_pairing_verified ? "yes" : "no"}`,
    `Docker Engine available: ${readiness?.docker_available ? "yes" : "no"}`,
    `Phone Quick Start URL: ${phoneQuickStartUrl}`,
    `Phone proof URL mode: ${phoneProofUrlMode}`,
    `Phone proof URL: ${phoneProofUrl}`,
  ];
  if (pairingNeedsLan) {
    lines.push("Pairing note: turn LAN access ON in Owner Access before scanning this pairing URL.");
  }
  if (proofSession?.summary) lines.push(`Proof session: ${proofSession.summary}`);
  if (verificationSession?.summary) lines.push(`Verification session: ${verificationSession.summary}`);
  if (finalVerification?.summary) {
    lines.push(`Final verification: ${finalVerification.status}`);
    lines.push(`Final summary: ${finalVerification.summary}`);
  }
  if (finalVerification?.next_owner_step) {
    lines.push(`Final next owner step: ${finalVerification.next_owner_step}`);
  }
  const remaining = readiness?.remaining_external_gates ?? verificationSession?.remaining_external_gates ?? proofSession?.remaining_external_gates ?? [];
  if (remaining.length) {
    lines.push("", "Remaining gates:");
    remaining.forEach((gate, index) => lines.push(`${index + 1}. ${gate}`));
  }
  if (nextActions.length) {
    lines.push("", "Next verification actions:");
    nextActions.forEach((action, index) => {
      lines.push(`${index + 1}. ${action.title}`);
      if (action.target_url) lines.push(`   Target: ${action.target_url}`);
      if (action.command) lines.push(`   Command: ${action.command}`);
      if (action.secondary_commands?.length) {
        lines.push("   Secondary commands:");
        action.secondary_commands.forEach((command) => lines.push(`   - ${command}`));
      }
    });
  }
  lines.push(
    "",
    "Owner commands:",
    `- Proof session: ${proofSessionCommand}`,
    `- Verification session: ${verificationSessionCommand}`,
    `- Final verification: ${finalVerificationCommand}`,
    `- Final verification watch: ${finalVerificationWatchCommand}`,
    `- Final verification watch all: ${finalVerificationWatchAllCommand}`,
    `- Final verification watch all with live links: ${finalVerificationWatchAllLiveLinksCommand}`,
    `- Phone proof watcher: ${phoneProofCommand}`,
    `- Readiness refresh: ${readinessCommand}`,
    `- Android device list: ${apkDeviceCommand}`,
    `- APK wait/install-pair: ${apkProofCommand}`,
    `- Docker diagnosis: ${dockerCheckCommand}`,
    `- Docker install: ${dockerInstallCommand}`,
    `- Docker elevated install: ${dockerElevatedInstallCommand}`,
  );
  return lines.join("\n");
}

function NextVerificationActionRow({
  action,
  index,
  phoneProofUrl,
  phoneProofUrlMode,
  pairingNeedsLan,
  onCopy,
}: {
  action: MobileNextVerificationAction;
  index: number;
  phoneProofUrl: string;
  phoneProofUrlMode: "pairing" | "quick-start";
  pairingNeedsLan: boolean;
  onCopy: (label: string, value: string) => Promise<void>;
}) {
  const isPhoneProofAction = action.action_id === "phone_browser_proof";
  const usesPairingUrl = isPhoneProofAction && phoneProofUrlMode === "pairing";
  const targetUrl = isPhoneProofAction
    ? phoneProofUrl
    : action.target_url;
  const detail = usesPairingUrl
    ? pairingNeedsLan
      ? "Turn LAN access ON in Owner Access before scanning from the phone; then wait for the phone proof watcher to report VERIFIED."
      : "Scan/copy the pairing proof URL from this desktop page, then wait for the phone proof watcher to report VERIFIED."
    : action.detail;
  const targetCopyLabel = usesPairingUrl ? "Copy pairing URL" : "Copy URL";
  const targetCopyStatusLabel = usesPairingUrl ? `${action.title} pairing URL` : `${action.title} URL`;
  return (
    <div className="quick-start-next-action">
      <span className="quick-start-next-action-index">{index + 1}</span>
      <div className="quick-start-next-action-copy">
        <strong>{action.title}</strong>
        <p>{detail}</p>
        {targetUrl ? <code>{redactSensitiveDisplayValue(targetUrl)}</code> : null}
      </div>
      <div className="quick-start-next-action-controls">
        {targetUrl ? (
          <button
            type="button"
            className="quick-start-readiness-action"
            onClick={() => void onCopy(targetCopyStatusLabel, targetUrl)}
          >
            {targetCopyLabel}
          </button>
        ) : null}
        {action.command ? (
          <button
            type="button"
            className="quick-start-readiness-action"
            onClick={() => void onCopy(`${action.title} command`, action.command || "")}
          >
            Copy command
          </button>
        ) : null}
      </div>
    </div>
  );
}

async function writeClipboardText(value: string): Promise<void> {
  try {
    if (navigator.clipboard) {
      await navigator.clipboard.writeText(value);
      return;
    }
  } catch {
    // Fall back to the textarea path for LAN/HTTP browsers that block the async API.
  }
  const textarea = document.createElement("textarea");
  textarea.value = value;
  textarea.setAttribute("readonly", "true");
  textarea.style.position = "fixed";
  textarea.style.left = "-9999px";
  textarea.style.top = "0";
  document.body.appendChild(textarea);
  textarea.focus();
  textarea.select();
  const copied = document.execCommand("copy");
  document.body.removeChild(textarea);
  if (!copied) throw new Error("clipboard unavailable");
}

function startBrowserDownload(blob: Blob, filename: string): void {
  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  window.setTimeout(() => window.URL.revokeObjectURL(url), 1000);
}

function quickStartUrl(webBase: string): string {
  const base = webBase.trim().replace(/\/+$/, "");
  if (!base) return "http://<YOUR-PC-LAN-IP>:4173/?page=quick-start";
  if (base.includes("?page=quick-start")) return base;
  return `${base}/?page=quick-start`;
}

function formatBytes(value: number | null | undefined): string {
  if (!Number.isFinite(value || 0) || !value) return "0 B";
  if (value < 1024) return `${value} B`;
  const mib = value / (1024 * 1024);
  return `${mib.toFixed(mib >= 10 ? 1 : 2)} MiB`;
}

function shortHash(value: string | null | undefined): string {
  if (!value) return "";
  return value.length > 12 ? value.slice(0, 12) : value;
}

function redactSensitiveDisplayValue(value: string): string {
  return value
    .replace(/(cas_owner_token=)[^&#\s]+/g, "$1REDACTED")
    .replace(/([?&]owner_token=)[^&#\s]+/g, "$1REDACTED");
}

function formatPhoneApiRoute(
  route: string | null | undefined,
  host: string | null | undefined,
): string {
  const hostLabel = host ? ` ${host}` : "";
  if (route === "same_origin_proxy") return `PWA proxy${hostLabel}`;
  if (route === "direct_api") return `Direct API${hostLabel}`;
  if (route === "loopback_api") return `Loopback${hostLabel}`;
  return "Unknown";
}

function findReadinessCheck(
  readiness: MobileReadinessLatest | null,
  checkId: string,
) {
  return readiness?.checks?.find((check) => check.check_id === checkId) ?? null;
}

function readinessChecksSucceeded(
  readiness: MobileReadinessLatest | null,
  checkIds: string[],
): boolean {
  if (!readiness?.checks?.length) return false;
  return checkIds.every((checkId) => findReadinessCheck(readiness, checkId)?.success === true);
}

function formatProbeAttemptSummary(readiness: MobileReadinessLatest | null): string {
  const targets = [
    ["web_phone_smoke", "web"],
    ["owner_pairing_payload", "pair"],
    ["paired_api_bases", "bases"],
  ] as const;
  const parts = targets
    .map(([checkId, label]) => {
      const check = findReadinessCheck(readiness, checkId);
      if (!check) return null;
      const raw = check.attempts ?? 1;
      const attempts = Number.isFinite(raw) ? Math.max(1, Math.floor(raw)) : 1;
      const status = check.success ? "" : ` ${check.status || "fail"}`;
      return `${label} ${attempts}x${status}`;
    })
    .filter((part): part is string => Boolean(part));
  return parts.length ? compactMetricText(parts.join(" / ")) : "Not checked";
}

function formatPhoneProofFreshness(
  isFresh: boolean | null | undefined,
  ageSeconds: number | null | undefined,
  expiresAt: string | null | undefined,
  maxAgeHours: number | null | undefined,
): string {
  const parts = [isFresh ? "Fresh" : "Expired"];
  const ageLabel = formatAge(ageSeconds);
  if (ageLabel) parts.push(ageLabel);
  if (expiresAt) {
    const expiry = new Date(expiresAt).toLocaleString();
    parts.push(`${isFresh ? "expires" : "expired"} ${expiry}`);
  } else if (maxAgeHours) {
    parts.push(`${maxAgeHours}h window`);
  }
  return parts.join(", ");
}

function formatAge(seconds: number | null | undefined): string | null {
  if (!Number.isFinite(seconds ?? Number.NaN)) return null;
  const total = Math.max(0, Math.floor(seconds ?? 0));
  if (total < 60) return `${total}s old`;
  if (total < 3600) return `${Math.floor(total / 60)}m old`;
  if (total < 86400) {
    const hours = Math.floor(total / 3600);
    const minutes = Math.floor((total % 3600) / 60);
    return minutes > 0 ? `${hours}h ${minutes}m old` : `${hours}h old`;
  }
  const days = Math.floor(total / 86400);
  const hours = Math.floor((total % 86400) / 3600);
  return hours > 0 ? `${days}d ${hours}h old` : `${days}d old`;
}

function formatAndroidDeviceState(readiness: MobileReadinessLatest | null): string {
  const count = readiness?.android_device_count ?? 0;
  const ready = readiness?.android_device_ready_count ?? 0;
  if (readiness?.android_device_ready) {
    return ready > 0
      ? `${ready} ready${count > ready ? ` / ${count} seen` : ""}`
      : "Ready";
  }
  if (count > 0) return `${ready} ready / ${count} seen`;
  const detail = readiness?.android_device_detail || "";
  if (/adb was not found/i.test(detail)) return "adb missing";
  if (/no ready|no android devices|not attached/i.test(detail)) {
    return readiness?.android_adb_path ? "No device, adb ready" : "No device";
  }
  const status = readiness?.android_device_status || "";
  return status && status !== "unknown" ? status : "Unknown";
}

function formatAndroidReleaseSigningState(readiness: MobileReadinessLatest | null): string {
  if (readiness?.android_release_signing_ready) {
    return readiness.android_release_apk_exists
      ? `Ready ${shortHash(readiness.android_release_apk_sha256)}`
      : "Ready, build pending";
  }
  const status = readiness?.android_release_signing_status || "unknown";
  const detail = readiness?.android_release_signing_detail || "";
  if (status === "missing_config") return "Missing config";
  if (status === "missing_store_file") return "Missing keystore";
  if (/missing/i.test(detail)) return compactMetricText(detail);
  return status && status !== "unknown" ? status : "Unknown";
}

function formatApkAttemptState(readiness: MobileReadinessLatest | null): string {
  if (!readiness?.apk_install_pairing_attempt_recorded) return "No attempt";
  const status = readiness.apk_install_pairing_attempt_status || "unknown";
  const labels: Record<string, string> = {
    verified: "Verified",
    dry_run: "Dry run",
    install_failed: "Install failed",
    pairing_failed: "Pairing failed",
    stale_apk: "Stale APK build",
    stale: "Stale",
    not_verified: "Not verified",
    none: "No attempt",
  };
  const label = labels[status] || status;
  if (status === "stale_apk") {
    const attempted = shortHash(readiness.apk_install_pairing_attempt_apk_sha256);
    const current = shortHash(readiness.apk_install_pairing_attempt_current_apk_sha256);
    const hashDetail = attempted && current
      ? ` ${attempted} -> ${current}`
      : "";
    return `${label}${hashDetail}`;
  }
  if (readiness.apk_install_pairing_attempt_message && status !== "verified") {
    return `${label}: ${compactMetricText(readiness.apk_install_pairing_attempt_message)}`;
  }
  if (readiness.apk_install_pairing_attempt_generated_at) {
    return `${label} ${new Date(readiness.apk_install_pairing_attempt_generated_at).toLocaleString()}`;
  }
  return label;
}

function formatApkRuntimeState(readiness: MobileReadinessLatest | null): string {
  const status = readiness?.apk_runtime_status || "none";
  const labels: Record<string, string> = {
    verified: "Verified",
    local_only: "Local only",
    observed: "Observed",
    stale: "Stale",
    none: "Not observed",
  };
  const label = labels[status] || status;
  if (readiness?.apk_runtime_generated_at && status !== "none") {
    return `${label} ${new Date(readiness.apk_runtime_generated_at).toLocaleString()}`;
  }
  return label;
}

function compactMetricText(value: string): string {
  return value.length > 72 ? `${value.slice(0, 69)}...` : value;
}

function formatVerificationSessionState(session: MobilePhoneVerificationSession | null): string {
  if (!session) return "Not loaded";
  if (session.status === "verified") return "Verified";
  if (session.status === "package_not_ready") return "Package not ready";
  const remaining = session.remaining_external_gates?.length ?? 0;
  const pending: string[] = [];
  const apkStatus = session.apk_install_pairing_attempt_status || "";
  if (apkStatus === "stale_apk") {
    pending.push("APK stale");
  } else if (apkStatus && !["verified", "none"].includes(apkStatus)) {
    pending.push(`APK ${apkStatus.replace(/_/g, " ")}`);
  }
  if (session.android_device_ready === false) pending.push("Android not ready");
  const dockerStatus = session.docker_engine_status || "";
  if (dockerStatus && !["available", "verified", "pass"].includes(dockerStatus)) {
    pending.push(`Docker ${dockerStatus.replace(/_/g, " ")}`);
  }
  if (pending.length > 0) {
    const gateText = remaining > 0 ? `${remaining} gate${remaining === 1 ? "" : "s"}` : "Pending";
    return compactMetricText(`${gateText}: ${pending.join(", ")}`);
  }
  if (remaining > 0) return `Pending ${remaining} gate${remaining === 1 ? "" : "s"}`;
  return session.status || "Unknown";
}

function formatFinalVerificationState(report: MobileFinalVerification | null): string {
  if (!report) return "Not loaded";
  if (report.status === "verified") return "Verified";
  if (report.status === "package_not_ready") return "Package not ready";
  const pending = report.gates
    ?.filter((gate) => !gate.satisfied)
    .map((gate) => gate.title.replace(/\s+proof$/i, ""))
    .slice(0, 3) ?? [];
  if (pending.length > 0) {
    return compactMetricText(`${pending.length} pending: ${pending.join(", ")}`);
  }
  if (report.remaining_external_gates?.length) {
    const remaining = report.remaining_external_gates.length;
    return `Pending ${remaining} gate${remaining === 1 ? "" : "s"}`;
  }
  return report.status || "Unknown";
}

function formatProofSessionState(session: MobileProofSession | null): string {
  if (!session) return "Not loaded";
  if (session.status === "verified") return "Verified";
  if (session.status === "package_not_ready") return "Package not ready";
  const remaining = session.remaining_external_gates?.length ?? 0;
  const pending = session.gates
    ?.filter((gate) => !gate.satisfied)
    .map((gate) => gate.title.replace(/\s+proof$/i, ""))
    .slice(0, 3) ?? [];
  if (pending.length > 0) {
    const gateText = remaining > 0 ? `${remaining} gate${remaining === 1 ? "" : "s"}` : "Pending";
    return compactMetricText(`${gateText}: ${pending.join(", ")}`);
  }
  if (remaining > 0) return `Pending ${remaining} gate${remaining === 1 ? "" : "s"}`;
  return session.status || "Unknown";
}

function formatDockerEngineState(readiness: MobileReadinessLatest | null): string {
  if (readiness?.docker_available) {
    return readiness.docker_server_version
      ? `Server ${readiness.docker_server_version}`
      : "Available";
  }
  const detail = readiness?.docker_engine_detail || "";
  if (/cli not found|docker .*not found|not recognized/i.test(detail)) return "CLI missing";
  if (/did not answer|timed out|daemon|engine did not answer/i.test(detail)) return "Engine down";
  if (readiness?.docker_wsl_checked && !readiness?.docker_wsl_engine_available) return "No local engine";
  const status = readiness?.docker_engine_status || "";
  return status && status !== "unknown" ? status : "Unknown";
}

function formatDockerInstallAttemptState(readiness: MobileReadinessLatest | null): string {
  const status = readiness?.docker_desktop_install_attempt_status || "";
  if (!status) return "No attempt";
  const labels: Record<string, string> = {
    admin_elevation_required: "Needs admin elevation",
    elevation_prompt_started: "UAC prompt launched",
    installed_or_started: "Install command completed",
    install_failed: "Install failed",
    timeout: "Timed out",
    winget_unavailable: "winget unavailable",
  };
  const label = labels[status] || status.replace(/_/g, " ");
  const code = readiness?.docker_desktop_install_attempt_installer_exit_code
    ?? readiness?.docker_desktop_install_attempt_returncode
    ?? null;
  return compactMetricText(code ? `${label} (${code})` : label);
}

function ReadinessMetric({ label, value, good }: { label: string; value: string; good: boolean }) {
  return (
    <div className="quick-start-readiness-metric">
      <span>{label}</span>
      <strong className={good ? "good" : "pending"}>{value}</strong>
    </div>
  );
}

function PhoneProofQrCode({
  url,
  mode,
  fallbackUrl,
  pairingNeedsLan = false,
}: {
  url: string;
  mode: "pairing" | "quick-start" | "apk-pairing";
  fallbackUrl: string;
  pairingNeedsLan?: boolean;
}) {
  const [dataUrl, setDataUrl] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const title = mode === "apk-pairing"
    ? "Scan after APK install"
    : mode === "pairing"
      ? "Scan pairing proof URL"
      : "Scan phone proof URL";
  const label = mode === "apk-pairing"
    ? "APK pairing QR"
    : mode === "pairing"
      ? "Phone pairing QR"
      : "Phone proof QR";
  const helper = mode === "apk-pairing"
    ? "Opens the installed Android app with owner token and direct API base."
    : mode === "pairing"
      ? pairingNeedsLan
        ? "Turn LAN access ON in Owner Access before scanning from the phone."
        : "Pairs a fresh phone, opens Quick Start, and lets it submit proof."
      : "Opens Quick Start; pair the phone first if proof cannot post.";

  useEffect(() => {
    let cancelled = false;
    setDataUrl(null);
    setFailed(false);
    void (async () => {
      try {
        const { default: QRCode } = await import("qrcode");
        const next = await QRCode.toDataURL(url, {
          errorCorrectionLevel: "M",
          margin: 1,
          width: 156,
          color: {
            dark: "#020617",
            light: "#f8fafc",
          },
        });
        if (!cancelled) setDataUrl(next);
      } catch {
        if (!cancelled) setFailed(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [url]);

  return (
    <div className="quick-start-phone-qr-panel">
      <div className="quick-start-phone-qr-copy">
        <span>{label}</span>
        <strong>{title}</strong>
        <p>{helper}</p>
        {pairingNeedsLan ? (
          <p className="quick-start-phone-qr-warning">LAN access is OFF, so a paired phone cannot submit owner-authenticated proof yet.</p>
        ) : null}
        <code>{redactSensitiveDisplayValue(url)}</code>
        {mode === "pairing" ? <small>Plain Quick Start: {redactSensitiveDisplayValue(fallbackUrl)}</small> : null}
      </div>
      <div className="quick-start-phone-qr-box">
        {failed ? (
          <span>QR unavailable</span>
        ) : dataUrl ? (
          <img alt={title} src={dataUrl} width={156} height={156} />
        ) : (
          <span>Generating QR...</span>
        )}
      </div>
    </div>
  );
}

function buildLaunchSequence(milestones: Milestone[]): LaunchSequenceStep[] {
  const status = (key: MilestoneKey): QuickStartStatus =>
    milestones.find((item) => item.key === key)?.status ?? "pending";
  const apiStatus = status("api");
  const mt5Status = status("mt5");
  const loopStatus = status("loop");
  const briefingStatus = status("briefing");
  const diagnosticsStatus: QuickStartStatus = mt5Status === "done" ? "done" : mt5Status === "running" ? "running" : "pending";
  return [
    {
      title: "Observe mode online",
      status: apiStatus,
      detail: "API and dashboard are reachable before any automation is treated as active.",
      href: "?page=dashboard",
    },
    {
      title: "Demo broker terminal connected",
      status: mt5Status,
      detail: "MT5 account visibility is confirmed before demo or paper execution is interpreted as broker evidence.",
      href: "?page=windows",
    },
    {
      title: "Risk profile and CAS dials reviewed",
      status: "pending",
      detail: "Owner risk, daily loss, exposure, and anti-impulse settings should be reviewed before increasing autonomy.",
      href: "?page=settings",
    },
    {
      title: "Broker diagnostics checked",
      status: diagnosticsStatus,
      detail: "Symbol mapping, spread/slippage tolerance, market availability, and terminal status need a fresh diagnostic pass.",
      href: "?page=settings",
    },
    {
      title: "Paper or demo loop running",
      status: loopStatus,
      detail: "The autonomous loop should prove paper/demo behavior before live-mode progression is considered.",
      href: "?page=trade",
    },
    {
      title: "First AI decision reviewed",
      status: briefingStatus,
      detail: "The owner should inspect the Operator briefing, latest decision chain, and trade explanation before escalation.",
      href: "?page=decisions",
    },
    {
      title: "Live unlock reviewed last",
      status: "pending",
      detail: "Live trading remains a final-stage owner decision after proof, diagnostics, emergency controls, and disclosure checks.",
      href: "?page=proof",
    },
  ];
}

function LaunchSequencePanel({ steps }: { steps: LaunchSequenceStep[] }) {
  return (
    <div className="quick-start-launch-sequence">
      <div className="quick-start-launch-header">
        <div>
          <div className="quick-start-launch-title">Professional Launch Sequence</div>
          <div className="quick-start-launch-subtitle">Autonomy should increase in this order.</div>
        </div>
        <span className="quick-start-launch-count">
          {steps.filter((step) => step.status === "done").length} / {steps.length}
        </span>
      </div>
      <div className="quick-start-launch-grid">
        {steps.map((step, index) => (
          <a className={`quick-start-launch-step quick-start-launch-step-${step.status}`} href={step.href ?? "#"} key={step.title}>
            <span className="quick-start-launch-index">{index + 1}</span>
            <span className="quick-start-launch-copy">
              <strong>{step.title}</strong>
              <small>{step.detail}</small>
            </span>
            <span className={`quick-start-status-chip quick-start-status-${step.status}`}>
              {quickStartStatusLabel(step.status)}
            </span>
          </a>
        ))}
      </div>
    </div>
  );
}

function quickStartStatusLabel(status: QuickStartStatus): string {
  if (status === "done") return "DONE";
  if (status === "running") return "CHECKING";
  if (status === "error") return "NEEDS ACTION";
  return "REVIEW";
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
