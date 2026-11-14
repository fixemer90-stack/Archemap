import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import vm from "node:vm";
import ts from "typescript";

// Exercise the shipped client, not a test-only DTO/error implementation.
const source = readFileSync("src/lib/api-client.ts", "utf8");
const clientModule = { exports: {} };
const retirement = {
  code: "legacy_career_generation_retired",
  message: "Career reports are created through the Career product flow.",
  target_path: "/products/career",
};
const compiled = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2022,
  },
}).outputText;
vm.runInNewContext(compiled, {
  module: clientModule,
  exports: clientModule.exports,
  fetch: async () =>
    new Response(JSON.stringify({ detail: retirement }), {
      status: 410,
      statusText: "Gone",
      headers: { "content-type": "application/json" },
    }),
});
await assert.rejects(
  clientModule.exports.api.post("/api/v1/reports/generate", {
    product: "career",
    profile_id: "profile-1",
  }),
  (error) => {
    assert.equal(error.status, 410);
    assert.deepEqual(JSON.parse(JSON.stringify(error.data.detail)), retirement);
    return true;
  },
);
console.log(
  "Legacy Career retirement API contract passed: HTTP 410 and structured detail remain observable",
);
