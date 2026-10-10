import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const globalsPath = path.join(root, "src/app/globals.css");
const globals = fs.readFileSync(globalsPath, "utf8");
const playwrightConfig = fs.readFileSync(
  path.join(root, "playwright.config.ts"),
  "utf8",
);
const uiRoot = path.join(root, "src/components/ui");
const surfaceRoots = [
  path.join(root, "src/components/layout"),
  path.join(root, "src/components/product-surface"),
  path.join(root, "src/components/settings"),
  path.join(root, "src/components/billing"),
  path.join(root, "src/components/glossary"),
  path.join(root, "src/components/chart"),
  path.join(root, "src/components/report"),
  path.join(root, "src/components/astrotype-v2"),
  path.join(root, "src/app/page.tsx"),
  path.join(root, "src/app/(auth)"),
  path.join(root, "src/app/(dashboard)/dashboard"),
  path.join(root, "src/app/(dashboard)/settings"),
  path.join(root, "src/app/(dashboard)/billing"),
  path.join(root, "src/app/(dashboard)/subscriptions"),
  path.join(root, "src/app/(dashboard)/report"),
  path.join(root, "src/app/(dashboard)/products/self"),
  path.join(root, "src/app/(dashboard)/products/love"),
  path.join(root, "src/app/(dashboard)/products/child"),
  path.join(root, "src/app/(dashboard)/products/career"),
];

const requiredTokens = [
  "--canvas",
  "--surface",
  "--surface-elevated",
  "--surface-subtle",
  "--overlay",
  "--scrim",
  "--text-primary",
  "--text-secondary",
  "--text-muted",
  "--text-inverse",
  "--border-default",
  "--border-strong",
  "--control",
  "--control-hover",
  "--control-active",
  "--control-disabled",
  "--focus-ring",
  "--link",
  "--link-hover",
  "--state-success",
  "--state-warning",
  "--state-error",
  "--state-info",
  "--shadow-soft",
  "--shadow-elevated",
  "--chart-grid",
  "--chart-label",
  "--chart-series-1",
  "--chart-series-2",
  "--chart-series-3",
  "--chart-highlight",
];

for (const token of requiredTokens) {
  const declarations = globals.match(new RegExp(`${token}\\s*:`, "g")) ?? [];
  if (declarations.length < 2) {
    throw new Error(
      `theme contract requires light and dark declarations for ${token}`,
    );
  }
}

if (/--canvas:\s*(?:#fff(?:fff)?|white)\s*;/i.test(globals)) {
  throw new Error("light canvas must not be pure white");
}

const contrastPairs = [
  ["#201b2f", "#e9e4dc", 4.5, "light primary/canvas"],
  ["#675f72", "#f5f1ea", 4.5, "light secondary/surface"],
  ["#f6f1e8", "#0d0f16", 4.5, "dark primary/canvas"],
  ["#d8dce8", "#151925", 4.5, "dark secondary/surface"],
  ["#ffffff", "#5b3fd6", 4.5, "primary control label"],
  ["#fffaf2", "#735bea", 4.5, "dark control label"],
];

function luminance(hex) {
  const values = hex
    .slice(1)
    .match(/.{2}/g)
    .map((value) => Number.parseInt(value, 16) / 255)
    .map((value) =>
      value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4,
    );
  return 0.2126 * values[0] + 0.7152 * values[1] + 0.0722 * values[2];
}

for (const [foreground, background, minimum, label] of contrastPairs) {
  const light = Math.max(luminance(foreground), luminance(background));
  const dark = Math.min(luminance(foreground), luminance(background));
  const ratio = (light + 0.05) / (dark + 0.05);
  if (ratio < minimum) {
    throw new Error(
      `${label} contrast ${ratio.toFixed(2)} is below ${minimum}`,
    );
  }
}

function assertNoThemeLiterals(filePath, label) {
  const source = fs.readFileSync(filePath, "utf8");
  if (
    /(?:bg|text|border|ring|shadow|fill|stroke|from|via|to)-\[(?:#|rgba?\()/.test(
      source,
    ) ||
    /(?:bg|text|border)-(?:white|black)(?:\/\d+)?/.test(source) ||
    /#[0-9a-f]{3,8}\b|rgba?\(/i.test(source)
  ) {
    throw new Error(`${label} still uses a theme-sensitive literal`);
  }
}

for (const entry of fs.readdirSync(uiRoot)) {
  if (!entry.endsWith(".tsx")) continue;
  assertNoThemeLiterals(path.join(uiRoot, entry), `UI primitive ${entry}`);
}

function walk(target) {
  const stat = fs.statSync(target);
  if (stat.isFile()) return [target];
  return fs
    .readdirSync(target, { withFileTypes: true })
    .flatMap((entry) => walk(path.join(target, entry.name)));
}

for (const target of surfaceRoots.flatMap(walk)) {
  if (/\.(?:ts|tsx)$/.test(target)) {
    assertNoThemeLiterals(target, path.relative(root, target));
  }
}

for (const viewport of [390, 820, 1440]) {
  if (!playwrightConfig.includes(`width: ${viewport}`)) {
    throw new Error(`theme browser matrix misses ${viewport}px viewport`);
  }
}
if (
  !playwrightConfig.includes("theme(?:-visual|-accessibility)?\\.spec\\.ts")
) {
  throw new Error("tablet theme project must not expand unrelated e2e suites");
}

for (const spec of ["theme-visual.spec.ts", "theme-accessibility.spec.ts"]) {
  if (!fs.existsSync(path.join(root, "tests/e2e", spec))) {
    throw new Error(`theme browser completeness gate misses ${spec}`);
  }
}

console.log(
  "theme contract passed: semantic tokens, primitives, and product surfaces",
);
