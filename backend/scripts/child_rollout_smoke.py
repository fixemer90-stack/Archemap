"""Read-only authenticated Child rollout probes; failures never print response bodies.

Manifest is private JSON; tokens come only from named environment variables.
This probes pre-created fixtures, not provider execution, browser UX or deployment.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit
from uuid import UUID

import httpx

ENABLED_CASES = frozenset(
    {"exact", "approximate", "unknown", "two_child", "locked", "foreign", "provider_failure", "pdf"}
)
DISABLED_CASES = frozenset({"flag_off_read", "flag_off_write"})
LOCKED_KEYS = frozenset({"access_state", "report_type", "required_level", "reason", "upgrade_url"})


def pointer(body: Any, path: str) -> Any:
    value = body
    for key in path.strip("/").split("/"):
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


def check_response(case: dict[str, Any], response: httpx.Response) -> bool:
    name = case["name"]
    required_status = {"locked": 402, "foreign": 404, "flag_off_write": 503}.get(name, 200)
    if response.status_code != required_status:
        return False
    if name == "pdf":
        return response.headers.get("content-type", "").startswith("application/pdf") and response.content.startswith(
            b"%PDF-"
        )
    try:
        body = response.json()
        if name == "locked" and (set(body) != {"detail"} or set(body["detail"]) != LOCKED_KEYS):
            return False
        if name == "foreign" and body != {"detail": "Child resource not found"}:
            return False
        if name == "flag_off_write" and body != {"detail": "Child Report is not enabled"}:
            return False
        if name == "exact" and pointer(body, "/birth_time_confidence") != "exact":
            return False
        if name == "approximate" and (
            pointer(body, "/birth_time_confidence") != "approximate" or body["birth_time"] is None
        ):
            return False
        if name == "unknown" and (
            pointer(body, "/birth_time_confidence") != "unknown" or body["birth_time"] is not None
        ):
            return False
        if name == "provider_failure" and pointer(body, "/status") not in {"narrative_failed", "failed"}:
            return False
        assertions = case.get("equals", {})
        if not isinstance(assertions, dict):
            return False
        if name not in {"locked", "foreign", "flag_off_write"}:
            identity = (
                "/report_id" if name == "flag_off_read" else "/generation_id" if name == "provider_failure" else "/id"
            )
            if not isinstance(assertions.get(identity), str) or not assertions[identity]:
                return False
        if not all(pointer(body, path) == expected for path, expected in assertions.items()):
            return False
        serialized = json.dumps(body, sort_keys=True)
        forbidden = case.get("forbidden_values", [])
        if name == "two_child" and not forbidden:
            return False
        return all(isinstance(value, str) and value and value not in serialized for value in forbidden)
    except (KeyError, TypeError, ValueError):
        return False


def validate_path(case: dict[str, Any]) -> None:
    path = case["path"]
    if not isinstance(path, str):
        raise ValueError("invalid Child API path")
    parsed = urlsplit(path)
    if (
        parsed.scheme
        or parsed.netloc
        or not parsed.path.startswith("/api/v1/child/")
        or parsed.fragment
        or ".." in unquote(parsed.path)
    ):
        raise ValueError("only same-origin Child API paths are accepted")
    if case["name"] == "pdf":
        query = parse_qs(parsed.query, keep_blank_values=True)
        values = query.get("age_snapshot_id", [])
        if (
            not parsed.path.endswith("/pdf")
            or set(query) != {"age_snapshot_id"}
            or len(values) != 1
            or str(UUID(values[0])) != values[0]
        ):
            raise ValueError("PDF probe requires one canonical pinned age snapshot")
    elif parsed.query:
        raise ValueError("unexpected Child API query")


def smoke(
    *,
    base_url: str,
    cases: list[dict[str, Any]],
    phase: str,
    sha: str,
    client: httpx.Client,
    allow_local_http: bool = False,
    gateway_user_env: str | None = None,
    gateway_password_env: str | None = None,
) -> dict[str, Any]:
    parsed = urlsplit(base_url)
    if (
        (
            parsed.scheme != "https"
            and not (allow_local_http and parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1"})
        )
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("authenticated HTTPS required (HTTP allowed only explicit loopback)")
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("exact 40-character git SHA required")
    required = ENABLED_CASES if phase == "enabled" else DISABLED_CASES
    names = [case["name"] for case in cases]
    if len(names) != len(set(names)) or set(names) != required:
        raise ValueError("scenario inventory must exactly match selected rollout phase")
    gateway_auth = None
    if gateway_user_env is not None or gateway_password_env is not None:
        if not gateway_user_env or not gateway_password_env:
            raise ValueError("both gateway environment names are required")
        if not all(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key) for key in (gateway_user_env, gateway_password_env)):
            raise ValueError("invalid gateway environment names")
        username = os.environ.get(gateway_user_env, "")
        password = os.environ.get(gateway_password_env, "")
        if not username.strip() or not password.strip():
            raise ValueError("missing gateway authentication environment")
        gateway_auth = httpx.BasicAuth(username, password)
    results = []
    for case in cases:
        path = case["path"]
        method = "POST" if case["name"] == "flag_off_write" else "GET"
        # Only the canonical PDF snapshot query is allowed; never credentials or redirects.
        validate_path(case)
        token = os.environ.get(case["token_env"], "")
        if not token or not re.fullmatch(r"[A-Za-z0-9._~-]+", token):
            raise ValueError("missing authentication environment variable")
        passed = False
        status = None
        try:
            response = client.request(
                method,
                base_url.rstrip("/") + path,
                headers={
                    "Authorization": "" if gateway_auth else f"Bearer {token}",
                    "Cookie": f"access_token={token}" if gateway_auth else "",
                    "Idempotency-Key": "child-flagoff-smoke",
                },
                auth=gateway_auth,
                json=case.get("body") if method == "POST" else None,
                follow_redirects=False,
            )
            status = response.status_code
            passed = check_response(case, response)
        except httpx.HTTPError:
            pass
        results.append({"scenario": case["name"], "passed": passed, "http_status": status})
    return {
        "passed": all(item["passed"] for item in results),
        "phase": phase,
        "requested_sha": sha,
        "deployed_sha_verified": False,
        "observed_at": datetime.now(UTC).isoformat(),
        "results": results,
        "provider_execution": "NOT_PROVEN_BY_READ_PROBE",
        "staging_budgets": "NOT_MEASURED",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--phase", choices=["enabled", "disabled"], default="enabled")
    parser.add_argument("--allow-local-http", action="store_true")
    parser.add_argument("--gateway-user-env", help="Environment variable NAME containing gateway username")
    parser.add_argument("--gateway-password-env", help="Environment variable NAME containing gateway password")
    args = parser.parse_args()
    try:
        if args.report.exists() or args.report.is_symlink():
            raise ValueError("private report already exists")
        with httpx.Client(timeout=30, trust_env=False) as client:
            result = smoke(
                base_url=args.base_url,
                cases=json.loads(args.manifest.read_text()),
                phase=args.phase,
                sha=args.sha,
                client=client,
                allow_local_http=args.allow_local_http,
                gateway_user_env=args.gateway_user_env,
                gateway_password_env=args.gateway_password_env,
            )
        args.report.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(args.report, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as stream:
            stream.write(json.dumps(result, indent=2) + "\n")
    except (ValueError, KeyError, TypeError, OSError):
        parser.exit(1, "FAIL: invalid/private manifest, authentication, transport or output; inspect privately\n")
    parser.exit(0 if result["passed"] else 1, "PASS\n" if result["passed"] else "FAIL: see sanitized report\n")


if __name__ == "__main__":
    main()
