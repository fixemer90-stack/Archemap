import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const checks = [
  {
    path: "src/app/(auth)/register/page.tsx",
    required: "router.push(`/report/v2/${result.profile_id}`)",
    forbidden: "router.push(`/report/${result.profile_id}`)",
  },
  {
    path: "src/app/(dashboard)/dashboard/page.tsx",
    required: "href={`/report/v2/${profile.id}`}",
    forbidden: "href={`/report/${profile.id}`}",
  },
  {
    path: "src/app/(dashboard)/products/self/page.tsx",
    required: "href={`/report/v2/${profile.id}`}",
    forbidden: "href={`/report/${profile.id}`}",
  },
];

for (const check of checks) {
  const source = readFileSync(resolve(check.path), "utf8");
  if (!source.includes(check.required)) {
    throw new Error(
      `${check.path} must route Self reports to ${check.required}`,
    );
  }
  if (source.includes(check.forbidden)) {
    throw new Error(
      `${check.path} still routes Self reports to legacy ${check.forbidden}`,
    );
  }
}

const v2Page = readFileSync(
  resolve("src/app/(dashboard)/report/v2/[profileId]/page.tsx"),
  "utf8",
);
for (const forbidden of [
  "@/lib/api/report",
  "@/lib/report/view-model",
  "socionics",
  "Socionics",
  "/api/v1/reports",
]) {
  if (v2Page.includes(forbidden)) {
    throw new Error(
      `V2 report page must not contain legacy marker: ${forbidden}`,
    );
  }
}

const publicCopy = readFileSync(resolve("src/app/page.tsx"), "utf8");
for (const forbiddenCopy of [
  "соционич",
  "Соционич",
  "socionics",
  "Socionics",
  "Model A",
]) {
  if (publicCopy.includes(forbiddenCopy)) {
    throw new Error(
      `Public landing page must not advertise legacy typology marker: ${forbiddenCopy}`,
    );
  }
}

const v2Api = readFileSync(resolve("src/lib/api/astrotype-v2.ts"), "utf8");
if (!v2Api.includes("/api/v1/astrotype-v2/reports")) {
  throw new Error("V2 API client must call /api/v1/astrotype-v2/reports");
}

console.log("V2 report routing check passed");
