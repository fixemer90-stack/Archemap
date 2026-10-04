import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";
import ts from "typescript";

const frontendRoot = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "..",
);
const root = path.resolve(frontendRoot, "..");
const fixture = JSON.parse(
  fs.readFileSync(
    path.join(root, "contracts/fixtures/career-report-read-v1-parity.json"),
    "utf8",
  ),
);
const source = fs.readFileSync(
  path.join(frontendRoot, "src/lib/career/report-view-model.ts"),
  "utf8",
);
const transpiled = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2022,
  },
}).outputText;
const compiledModule = { exports: {} };
vm.runInNewContext(transpiled, {
  module: compiledModule,
  exports: compiledModule.exports,
  require() {
    throw new Error(
      "The presentation builder must remain runtime dependency-free",
    );
  },
});

assert.equal(
  typeof compiledModule.exports.buildCareerReportPresentation,
  "function",
  "Frontend must export the renderer-neutral presentation builder",
);
const actual = compiledModule.exports.buildCareerReportPresentation(
  fixture.payload,
);
assert.deepEqual(
  JSON.parse(JSON.stringify(actual)),
  fixture.expected_manifest,
  "Frontend semantic manifest must match the shared web/PDF fixture",
);

const deterministicReady = structuredClone(fixture.payload);
deterministicReady.status = "deterministic_ready";
deterministicReady.sections = [];
deterministicReady.section_states = [];
const pending =
  compiledModule.exports.buildCareerReportPresentation(deterministicReady);
assert.equal(
  pending.blocks.filter((block) => block.kind === "narrative").length,
  10,
);
assert.deepEqual(
  [...new Set(pending.blocks.slice(0, 10).map((block) => block.status))],
  ["pending"],
);
assert.equal(pending.notice.kind, "deterministic_ready");
assert.equal(pending.blocks[10].kind, "dimensions");

const generatingSections = structuredClone(fixture.payload);
generatingSections.status = "generating_sections";
const generating =
  compiledModule.exports.buildCareerReportPresentation(generatingSections);
assert.equal(generating.notice.kind, "deterministic_ready");

const legacy = structuredClone(fixture.payload);
legacy.deterministic_payload.contract_version =
  "career_interpretation_facts_v1";
legacy.deterministic_payload.role_matches = [
  {
    role_family_key: "architecture",
    category: "strong_match",
    reasons: ["dimension:systems_thinking"],
    profession_examples: ["Solution Architect", "Systems Architect"],
    catalog_version: "career-role-catalog-1",
  },
];
const legacyManifest =
  compiledModule.exports.buildCareerReportPresentation(legacy);
const legacyRoles = legacyManifest.blocks.find(
  (block) => block.kind === "roles",
);
assert.equal(legacyManifest.contract_version, "career_report_presentation_v1");
assert.equal(legacyRoles.items[0].title, "Architecture");
assert.deepEqual(JSON.parse(JSON.stringify(legacyRoles.items[0].examples)), [
  "Solution Architect",
  "Systems Architect",
]);

console.log("Career report web/PDF semantic parity checks passed");
