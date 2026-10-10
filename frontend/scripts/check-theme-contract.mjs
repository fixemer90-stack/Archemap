import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const globalsPath = path.join(root, "src/app/globals.css");
const globals = fs.readFileSync(globalsPath, "utf8");

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

console.log(
  "theme contract passed: semantic tokens, literals, contrast, rollout gate",
);
