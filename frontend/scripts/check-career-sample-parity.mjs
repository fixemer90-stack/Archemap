import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const frontendRoot = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "..",
);
const root = path.resolve(frontendRoot, "..");
const protocolPath = path.join(
  root,
  "docs/design/astrotype-career-report-parity-protocol.json",
);
const protocol = JSON.parse(fs.readFileSync(protocolPath, "utf8"));
const canonical = fs.readFileSync(
  path.join(root, protocol.canonical.html),
  "utf8",
);
const reader = fs.readFileSync(path.join(root, protocol.reader), "utf8");

for (const relativePath of [
  protocol.canonical.desktop_preview,
  protocol.canonical.mobile_preview,
]) {
  const bytes = fs.readFileSync(path.join(root, relativePath));
  assert.equal(
    bytes.subarray(1, 4).toString(),
    "PNG",
    `${relativePath} must be a PNG`,
  );
  assert.ok(
    bytes.length > 10_000,
    `${relativePath} must contain real preview evidence`,
  );
}

for (const pair of protocol.component_pairs) {
  const canonicalMarker = pair.canonical_selector.startsWith("#")
    ? `id="${pair.canonical_selector.slice(1)}"`
    : pair.canonical_selector === ".calculation"
      ? 'class="calculation reveal"'
      : pair.canonical_selector === ".section-index"
        ? 'class="section-index reveal"'
        : 'class="hero reveal"';
  assert.ok(
    canonical.includes(canonicalMarker),
    `Canonical sample is missing ${pair.name}: ${pair.canonical_selector}`,
  );
}

for (const key of [
  "professional_summary",
  "dimensions",
  "contradictions",
  "context",
  "roles",
  "technical_basis",
]) {
  const hasMarker =
    key === "professional_summary"
      ? reader.includes("data-presentation-key={section.key}")
      : reader.includes(`data-presentation-key=\"${key}\"`);
  assert.ok(hasMarker, `Reader is missing semantic crop marker: ${key}`);
}

assert.ok(
  reader.includes("max-w-5xl"),
  "Reader must keep a bounded responsive web canvas",
);
assert.ok(
  reader.includes("bg-[#111927]"),
  "Reader must keep the dark report surface language",
);
assert.ok(
  reader.includes("text-[#D7B466]"),
  "Reader must keep the gold accent direction",
);
assert.ok(
  protocol.checklist.some((item) => item.includes("not an acceptance signal")),
  "Protocol must reject meaningless full-page pixel equality",
);

console.log("Career canonical-sample component parity protocol checks passed");
