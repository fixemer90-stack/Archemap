import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

const registerPath = resolve("src/app/(auth)/register/page.tsx");
const loginPath = resolve("src/app/(auth)/login/page.tsx");
const callbackPath = resolve("src/app/(auth)/auth/callback/page.tsx");
const apiClientPath = resolve("src/lib/api-client.ts");
const authSessionPath = resolve("src/lib/auth-session.ts");
const authStorePath = resolve("src/stores/auth-store.ts");
const cookiesPath = resolve("src/lib/cookies.ts");
const dashboardPath = resolve("src/app/(dashboard)/dashboard/page.tsx");
const reportApiPath = resolve("src/lib/api/report.ts");
const reportPagePath = resolve(
  "src/app/(dashboard)/report/[profileId]/page.tsx",
);
const nextConfigPath = resolve("next.config.ts");

for (const path of [
  registerPath,
  loginPath,
  callbackPath,
  apiClientPath,
  authSessionPath,
  authStorePath,
  cookiesPath,
  dashboardPath,
  reportApiPath,
  reportPagePath,
]) {
  if (!existsSync(path)) {
    throw new Error(`Missing auth UX file: ${path}`);
  }
}

const registerPage = readFileSync(registerPath, "utf8");
const loginPage = readFileSync(loginPath, "utf8");
const callbackPage = readFileSync(callbackPath, "utf8");
const apiClient = readFileSync(apiClientPath, "utf8");
const authSession = readFileSync(authSessionPath, "utf8");
const authStore = readFileSync(authStorePath, "utf8");
const cookies = readFileSync(cookiesPath, "utf8");
const dashboardPage = readFileSync(dashboardPath, "utf8");
const reportApi = readFileSync(reportApiPath, "utf8");
const reportPage = readFileSync(reportPagePath, "utf8");
const nextConfig = readFileSync(nextConfigPath, "utf8");

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

for (const marker of [
  'fetch("/api/v1/auth/login"',
  'credentials: "include"',
  "bootstrapSession()",
]) {
  if (!loginPage.includes(marker)) {
    throw new Error(`Login page missing cookie-first marker: ${marker}`);
  }
}

for (const marker of [
  'credentials: "include"',
  'fetch("/api/v1/auth/refresh"',
  "body: JSON.stringify({})",
]) {
  if (!apiClient.includes(marker) && !authSession.includes(marker)) {
    throw new Error(
      `Cookie-first API/session helper missing marker: ${marker}`,
    );
  }
}

for (const forbidden of [
  "getPreferredAccessToken",
  "refreshAccessToken",
  "getAccessToken",
  "getRefreshToken",
  "setAccessToken",
  "setRefreshToken",
  "setTokens",
  "token: string | null",
  "Authorization: `Bearer",
]) {
  const source = `${apiClient}\n${authSession}\n${authStore}\n${cookies}\n${dashboardPage}\n${reportApi}\n${reportPage}\n${loginPage}\n${registerPage}`;
  if (source.includes(forbidden)) {
    throw new Error(`Browser auth must not use JS JWT marker: ${forbidden}`);
  }
}

for (const marker of [
  'fetch("/api/v1/users/me"',
  'fetch("/api/v1/auth/refresh"',
  "store.login(currentUser)",
  "store.logout()",
]) {
  if (!authSession.includes(marker)) {
    throw new Error(`Session bootstrap missing marker: ${marker}`);
  }
}

for (const marker of [
  "bootstrapSession",
  'fetch("/api/v1/profiles"',
  'credentials: "include"',
]) {
  if (!dashboardPage.includes(marker)) {
    throw new Error(
      `Dashboard cookie session bootstrap missing marker: ${marker}`,
    );
  }
}

for (const marker of [
  "sessionExpiredMessage",
  "Сессия истекла. Войдите снова, чтобы обновить отчёт.",
  "return;",
]) {
  if (!reportPage.includes(marker)) {
    throw new Error(`Report 401 resilience missing marker: ${marker}`);
  }
}

const poll401Branch = reportPage.match(
  /if \(pollError instanceof ApiError && pollError\.status === 401\) \{[\s\S]*?return;\n\s*\}/,
)?.[0];
if (!poll401Branch) {
  throw new Error("Report polling must handle 401 explicitly");
}
for (const destructiveMarker of [
  "setApiData(null)",
  "setCurrentReport(null)",
  "setData(null)",
]) {
  if (poll401Branch.includes(destructiveMarker)) {
    throw new Error(
      `Report polling 401 must not clear already loaded report data: ${destructiveMarker}`,
    );
  }
}

if (reportApi.includes("token?: string") || reportApi.includes(", token")) {
  throw new Error("Report API helpers must not require token parameters");
}

if (
  !nextConfig.includes("/api/:path*") ||
  !nextConfig.includes("BACKEND_URL")
) {
  throw new Error("Next config must proxy /api/* to BACKEND_URL");
}

console.log("Auth UX structure check passed");
