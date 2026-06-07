import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

const registerPath = resolve("src/app/(auth)/register/page.tsx");
const callbackPath = resolve("src/app/(auth)/auth/callback/page.tsx");
const apiClientPath = resolve("src/lib/api-client.ts");
const nextConfigPath = resolve("next.config.ts");
const dashboardPath = resolve("src/app/(dashboard)/dashboard/page.tsx");

if (!existsSync(registerPath)) {
  throw new Error("Missing register page");
}
if (!existsSync(callbackPath)) {
  throw new Error(
    "Missing OAuth callback page at src/app/(auth)/callback/page.tsx",
  );
}

const registerPage = readFileSync(registerPath, "utf8");
const callbackPage = readFileSync(callbackPath, "utf8");
const apiClient = readFileSync(apiClientPath, "utf8");
const nextConfig = readFileSync(nextConfigPath, "utf8");
const dashboardPage = readFileSync(dashboardPath, "utf8");

for (const marker of [
  'window.location.href = "/api/v1/auth/oauth/yandex/start"',
  'searchParams.get("birth_date")',
  'searchParams.get("email")',
  'credentials: "include"',
  "router.push(`/report/${result.profile_id}`)",
]) {
  if (!registerPage.includes(marker)) {
    throw new Error(`Register OAuth flow missing marker: ${marker}`);
  }
}

for (const marker of [
  "useSearchParams",
  "needs_profile",
  "birth_date",
  "email",
  "router.replace",
  "/register?step=2",
  "/dashboard",
]) {
  if (!callbackPage.includes(marker)) {
    throw new Error(`OAuth callback page missing marker: ${marker}`);
  }
}

if (!apiClient.includes('credentials: "include"')) {
  throw new Error("API client must include cookies for HttpOnly OAuth session");
}

for (const marker of [
  'fetch("/api/v1/users/me"',
  'fetch("/api/v1/profiles"',
  'credentials: "include"',
]) {
  if (!dashboardPage.includes(marker)) {
    throw new Error(
      `Dashboard OAuth session bootstrap missing marker: ${marker}`,
    );
  }
}

if (
  !nextConfig.includes("/api/:path*") ||
  !nextConfig.includes("BACKEND_URL")
) {
  throw new Error("Next config must proxy /api/* to BACKEND_URL");
}

console.log("Auth UX structure check passed");
