import assert from "node:assert/strict";
import { createServer, request } from "node:http";
import { once } from "node:events";
import { test } from "node:test";
import { registerLandingDocumentCounter } from "../src/lib/landing-document-counter.ts";

const documentHeaders = {
  "x-astrotype-landing-document": "1",
  "sec-fetch-mode": "navigate",
  "sec-fetch-dest": "document",
  accept: "text/html",
};

test("only completed 200 HTML landing documents trigger a request-independent signal", async (t) => {
  let count = 0;
  const stop = registerLandingDocumentCounter(async () => {
    count++;
  });
  const server = createServer((req, res) => {
    res.statusCode = Number(req.headers["test-status"] ?? 200);
    res.setHeader(
      "content-type",
      req.headers["test-content-type"] ?? "text/html; charset=utf-8",
    );
    res.end("hello");
  }).listen(0, "127.0.0.1");
  t.after(() => {
    stop();
    server.close();
  });
  await once(server, "listening");
  const { port } = server.address();
  async function send({ path = "/", method = "GET", headers = {} } = {}) {
    await new Promise((resolve, reject) => {
      const req = request(
        {
          host: "127.0.0.1",
          port,
          path,
          method,
          headers: { ...documentHeaders, ...headers },
        },
        (res) => {
          res.resume();
          res.on("end", resolve);
        },
      );
      req.on("error", reject);
      req.end();
    });
  }

  await send({
    headers: {
      cookie: "sentinel=private",
      referer: "https://test.invalid/private",
    },
  });
  assert.equal(count, 1);
  for (const headers of [
    { "x-astrotype-landing-document": "0" },
    { "sec-fetch-mode": "cors" },
    { "sec-fetch-dest": "iframe" },
    { "sec-purpose": "prefetch;prerender" },
    { purpose: "prefetch" },
    { "x-purpose": "preview" },
    { "next-router-prefetch": "1" },
    { "next-router-segment-prefetch": "/_tree" },
    { rsc: "1" },
    { authorization: "Bearer unrelated" },
    { accept: "application/json" },
    { "test-content-type": "text/x-component" },
    ...[201, 204, 206, 302, 304, 404, 500].map((status) => ({
      "test-status": status,
    })),
  ])
    await send({ headers });
  for (const path of ["/?secret=private", "/dashboard", "/index.html", "//"])
    await send({ path });
  await send({ method: "HEAD" });
  assert.equal(count, 1);
});
