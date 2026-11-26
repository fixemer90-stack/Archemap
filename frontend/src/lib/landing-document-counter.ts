import { channel } from "node:diagnostics_channel";
import type { IncomingMessage, ServerResponse } from "node:http";

const requestStart = channel("http.server.request.start");
const excludedHeaders = [
  "authorization",
  "purpose",
  "sec-purpose",
  "x-purpose",
  "rsc",
  "next-router-prefetch",
  "next-router-segment-prefetch",
  "next-router-state-tree",
  "x-middleware-prefetch",
] as const;

export function registerLandingDocumentCounter(record: () => Promise<void>) {
  let inFlight = 0;
  const observe = (message: unknown) => {
    const { request, response } = message as {
      request: IncomingMessage;
      response: ServerResponse;
    };
    const { headers } = request;
    if (
      request.method !== "GET" ||
      request.url !== "/" ||
      headers["x-astrotype-landing-document"] !== "1" ||
      headers["sec-fetch-mode"] !== "navigate" ||
      headers["sec-fetch-dest"] !== "document" ||
      !/(?:^|,)\s*text\/html(?:[\s;,]|$)/i.test(headers.accept ?? "") ||
      excludedHeaders.some((header) => headers[header] !== undefined) ||
      /(?:^|;\s*)__prerender_bypass=/.test(headers.cookie ?? "")
    )
      return;

    response.once("finish", () => {
      if (
        response.statusCode !== 200 ||
        !/^text\/html(?:\s*;|$)/i.test(
          String(response.getHeader("content-type")),
        ) ||
        inFlight >= 4
      )
        return;
      // Do not retain the request, wait for storage, retry, or log an exception.
      inFlight++;
      void Promise.resolve()
        .then(record)
        .catch(() => {})
        .finally(() => {
          inFlight--;
        });
    });
  };
  requestStart.subscribe(observe);
  return () => requestStart.unsubscribe(observe);
}
