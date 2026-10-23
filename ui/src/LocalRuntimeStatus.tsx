import { useEffect, useState, type ReactElement } from "react";
import { connected, eventStreamOrigin, onEvent } from "./events";

type PageObservation = Readonly<{ count: number; origins: readonly string[]; external: number; blocked: number; error: string }>;
type RuntimePolicy = Readonly<{ offline: boolean; violations: number }>;

export function LocalRuntimeStatus(): ReactElement {
  const [observation, setObservation] = useState<PageObservation>({ count: 0, origins: [], external: 0, blocked: 0, error: "" });
  const [policy, setPolicy] = useState<RuntimePolicy | null>(null);
  const [policyError, setPolicyError] = useState("");
  const [stream, setStream] = useState(connected());
  const refresh = async (): Promise<void> => {
    try {
      const response = await fetch("/api/runtime/policy");
      if (!response.ok) throw new Error(`Runtime policy request failed (${response.status})`);
      const value: unknown = await response.json();
      if (typeof value !== "object" || value === null || !("offline" in value) || !("browser_violations" in value)
        || typeof value.offline !== "boolean" || typeof value.browser_violations !== "number") throw new Error("Invalid runtime policy response");
      setPolicy({ offline: value.offline, violations: value.browser_violations }); setPolicyError("");
    } catch (error: unknown) { setPolicyError(String(error)); }
  };
  useEffect(() => { void refresh(); }, []);
  useEffect(() => {
    if (typeof PerformanceObserver === "undefined" || !PerformanceObserver.supportedEntryTypes.includes("resource")) {
      setObservation((previous) => ({ ...previous, error: "This browser does not expose page resource timing." })); return;
    }
    const origins = new Set<string>();
    let count = 0, external = 0, blocked = 0;
    const publish = (): void => setObservation({ count, external, blocked, origins: [...origins].sort(), error: "" });
    const observer = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        const url = new URL(entry.name, window.location.href);
        if (url.protocol !== "http:" && url.protocol !== "https:" && url.protocol !== "ws:" && url.protocol !== "wss:") continue;
        count++; origins.add(url.origin);
        if (url.origin !== window.location.origin) external++;
      }
      publish();
    });
    observer.observe({ type: "resource", buffered: true });
    const violation = (): void => { blocked++; publish(); };
    window.addEventListener("securitypolicyviolation", violation);
    const unsubscribe = onEvent((event: string) => { if (event === "connection") setStream(connected()); });
    return () => { observer.disconnect(); window.removeEventListener("securitypolicyviolation", violation); unsubscribe(); };
  }, []);
  return <details className="mv-runtime"><summary>Local runtime connection status</summary>
    <p>Observes resources requested by this Effigy page and its progress stream. Other desktop tabs and operating-system connections are outside this view.</p>
    {observation.error ? <p role="alert">{observation.error}</p> : <>
      <p>Observed page resource requests: {observation.count}. External page requests: {observation.external}. Blocked page requests: {observation.blocked}.</p>
      <p>Observed origins: {observation.origins.join(", ") || "No completed requests observed yet."}</p>
    </>}
    <p>Progress stream: {stream ? "connected" : "disconnected"} at {eventStreamOrigin()}.</p>
    <p>Offline application policy: {policy ? (policy.offline ? "active" : "inactive") : "unavailable"}. Server-recorded browser policy violations: {policy?.violations ?? "unavailable"}.</p>
    {policyError && <p role="alert">{policyError}</p>}
    <button onClick={() => { void refresh(); }}>Refresh policy status</button>
  </details>;
}
