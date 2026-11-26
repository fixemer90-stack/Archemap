export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    if (process.env.LANDING_DOCUMENT_COUNTER_ENABLED !== "true") return;
    let sink: URL;
    try {
      sink = new URL("/_internal/landing-document", process.env.BACKEND_URL);
    } catch {
      return;
    }
    if (
      sink.protocol !== "http:" ||
      sink.username ||
      sink.password ||
      !["backend", "127.0.0.1", "[::1]"].includes(sink.hostname)
    )
      return;

    const { registerLandingDocumentCounter } =
      await import("./lib/landing-document-counter");
    registerLandingDocumentCounter(async () => {
      await fetch(sink, {
        method: "POST",
        headers: { "X-Astrotype-Landing-Signal": "1" },
        redirect: "error",
        signal: AbortSignal.timeout(400),
      });
    });
  }
}
