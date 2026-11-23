import {
  attribution,
  safeContext,
  safeGoal,
  type PrivacyConfig,
} from "./privacy";

export interface AnalyticsPort {
  href(): string;
  referrer(): string;
  consent(): boolean;
  normalize(href: string): void;
  load(): Promise<void>;
  call(id: number, method: string, ...args: unknown[]): void;
}
/** A public-document lifetime, not an SPA tracker. SDK behavior and counter-side
 * automatic-goal settings still require real staging network verification.
 * Opaque failures are swallowed locally, never exported as URLs/error text. */
export function createRuntime(config: PrivacyConfig, port: AnalyticsPort) {
  let stopped = false;
  let initialized = false;
  let pending: Promise<void> | null = null;
  const allowed = () =>
    !stopped &&
    config.enabled &&
    port.consent() &&
    safeContext(port.href(), port.referrer()) !== null;
  const cleanContext = () =>
    allowed() &&
    safeContext(port.href(), port.referrer())?.href === port.href();
  function call(method: string, ...args: unknown[]) {
    try {
      if (config.counterId === null) return false;
      port.call(config.counterId, method, ...args);
      return true;
    } catch {
      /* fail closed; no telemetry */
      return false;
    }
  }
  function goal(value: unknown) {
    const goal = safeGoal(value);
    if (initialized && cleanContext() && goal) call("reachGoal", goal);
  }
  return {
    start(): Promise<void> {
      if (pending) return pending;
      if (!allowed()) return Promise.resolve();
      pending = (async () => {
        try {
          const context = safeContext(port.href(), port.referrer());
          if (!context) return;
          port.normalize(context.href);
          if (port.href() !== context.href) return;
          await port.load();
          if (!cleanContext() || port.href() !== context.href) return;
          initialized = call("init", {
            defer: true,
            webvisor: false,
            clickmap: false,
            trackLinks: false,
            accurateTrackBounce: false,
            trackHash: false,
            ecommerce: false,
            triggerEvent: false,
            childIframe: false,
            sendTitle: false,
          });
          if (!initialized) return;
          call("hit", context.href, {
            referer: context.referrer,
            title: "Public landing",
          });
          goal("landing_view");
        } catch {
          /* adblock/SDK failure must not affect signup */
        }
      })();
      return pending;
    },
    goal,
    clientId(timeoutMs = 250): Promise<string | null> {
      if (!initialized || !cleanContext()) return Promise.resolve(null);
      return new Promise((resolve) => {
        let settled = false;
        const finish = (value: unknown) => {
          if (settled) return;
          settled = true;
          clearTimeout(timer);
          resolve(
            cleanContext()
              ? attribution(value, config.policyVersion ?? "").clientId
              : null,
          );
        };
        const timer = setTimeout(
          () => finish(null),
          Math.min(Math.max(timeoutMs, 0), 500),
        );
        call("getClientID", finish);
      });
    },
    stop() {
      stopped = true;
      if (initialized) {
        call("destruct");
        initialized = false;
      }
    },
  };
}
export type AnalyticsRuntime = ReturnType<typeof createRuntime>;
