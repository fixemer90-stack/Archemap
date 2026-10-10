import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const sidebarPath = path.join(root, "src/components/layout/sidebar.tsx");
const headerPath = path.join(root, "src/components/layout/header.tsx");
const storePath = path.join(root, "src/stores/ui-store.ts");
const layoutPath = path.join(root, "src/app/layout.tsx");

const sidebar = fs.readFileSync(sidebarPath, "utf8");
const header = fs.readFileSync(headerPath, "utf8");
const store = fs.readFileSync(storePath, "utf8");
const layout = fs.readFileSync(layoutPath, "utf8");

for (const token of [
  "h-dvh",
  "overflow-y-auto",
  "max-w-[21rem]",
  'aria-modal="true"',
  "Закрыть меню",
  "xl:w-[17.5rem]",
  "motion-reduce:transition-none",
]) {
  if (!sidebar.includes(token)) {
    throw new Error(`responsive sidebar contract misses ${token}`);
  }
}

for (const token of ["Открыть меню", "toggleMobileSidebar", "md:hidden"]) {
  if (!header.includes(token)) {
    throw new Error(`dashboard header contract misses ${token}`);
  }
}

for (const forbidden of ["useTheme", "Включить светлую тему", "Moon", "Sun"]) {
  if (header.includes(forbidden)) {
    throw new Error(
      `dashboard header still exposes incomplete light theme via ${forbidden}`,
    );
  }
}

for (const token of ['className="dark"', 'forcedTheme="dark"']) {
  if (!layout.includes(token)) {
    throw new Error(
      `root layout does not lock the supported dark theme via ${token}`,
    );
  }
}

for (const token of [
  "mobileSidebarOpen",
  "toggleMobileSidebar",
  "setMobileSidebarOpen",
]) {
  if (!store.includes(token)) {
    throw new Error(`UI store contract misses ${token}`);
  }
}

console.log("dashboard shell UX contract passed");
