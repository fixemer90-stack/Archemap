"""Offline controller contracts; no Docker, DB, network or provider calls."""

from __future__ import annotations

import copy
import importlib
from typing import Any

import pytest


def native_config() -> dict[str, Any]:
    """Redacted native GET /config/ on staging gateway, 2026-10-31.

    Preserve adapted nesting/order, including metrics subroute and outer headers.
    Accounts below are synthetic; the real imported credentials were never saved.
    """

    def proxy(dial: str) -> dict[str, Any]:
        return {"handler": "reverse_proxy", "upstreams": [{"dial": dial}]}

    return {
        "apps": {
            "http": {
                "servers": {
                    "srv0": {
                        "listen": [":8080"],
                        "routes": [
                            {
                                "handle": [
                                    {
                                        "handler": "headers",
                                        "response": {
                                            "set": {
                                                "Referrer-Policy": ["no-referrer"],
                                                "X-Content-Type-Options": ["nosniff"],
                                                "X-Frame-Options": ["SAMEORIGIN"],
                                                "X-Robots-Tag": ["noindex, nofollow, noarchive"],
                                            }
                                        },
                                    },
                                    {
                                        "encodings": {"gzip": {}, "zstd": {}},
                                        "handler": "encode",
                                        "prefer": ["zstd", "gzip"],
                                    },
                                    {
                                        "handler": "subroute",
                                        "routes": [
                                            {
                                                "handle": [
                                                    {
                                                        "handler": "authentication",
                                                        "providers": {
                                                            "http_basic": {
                                                                "accounts": [
                                                                    {
                                                                        "username": "synthetic",
                                                                        "password": "synthetic-hash",
                                                                    }
                                                                ],
                                                                "hash": {"algorithm": "bcrypt"},
                                                                "hash_cache": {},
                                                            }
                                                        },
                                                    }
                                                ]
                                            },
                                            {
                                                "handle": [proxy("staging-backend:8000")],
                                                "match": [{"path": ["/api/*"]}],
                                            },
                                            {
                                                "handle": [
                                                    {
                                                        "handler": "static_response",
                                                        "headers": {"Location": ["/career-metrics/"]},
                                                        "status_code": 308,
                                                    }
                                                ],
                                                "match": [{"path": ["/career-metrics"]}],
                                            },
                                            {
                                                "handle": [
                                                    {
                                                        "handler": "subroute",
                                                        "routes": [
                                                            {
                                                                "handle": [
                                                                    {
                                                                        "handler": "rewrite",
                                                                        "strip_path_prefix": "/career-metrics",
                                                                    }
                                                                ]
                                                            },
                                                            {"handle": [proxy("prometheus:9090")]},
                                                        ],
                                                    }
                                                ],
                                                "match": [{"path": ["/career-metrics/*"]}],
                                            },
                                            {"handle": [proxy("staging-frontend:3000")]},
                                        ],
                                    },
                                ]
                            }
                        ],
                    }
                }
            }
        }
    }


def controller() -> Any:
    return importlib.import_module("scripts.child_staging_maintenance")


def test_native_shape_inserts_all_http_maintenance_after_auth_without_mutating_original() -> None:
    module = controller()
    original = native_config()
    saved = copy.deepcopy(original)
    frozen = module.maintenance_config(original)
    handles = frozen["apps"]["http"]["servers"]["srv0"]["routes"][0]["handle"]
    routes = handles[2]["routes"]
    assert original == saved
    assert handles[:2] == saved["apps"]["http"]["servers"]["srv0"]["routes"][0]["handle"][:2]
    assert routes[0] == saved["apps"]["http"]["servers"]["srv0"]["routes"][0]["handle"][2]["routes"][0]
    assert routes[1] == {
        "handle": [
            {
                "handler": "static_response",
                "status_code": 503,
                "body": "Staging maintenance\n",
                "headers": {"Retry-After": ["60"]},
            }
        ]
    }
    assert routes[2:] == saved["apps"]["http"]["servers"]["srv0"]["routes"][0]["handle"][2]["routes"][1:]


@pytest.mark.parametrize("change", ["auth", "headers", "upstream", "listener", "extra_server"])
def test_unsupported_native_shapes_fail_closed(change: str) -> None:
    original = native_config()
    server = original["apps"]["http"]["servers"]["srv0"]
    handles = server["routes"][0]["handle"]
    if change == "auth":
        handles[2]["routes"][0]["match"] = [{"path": ["/somewhere"]}]
    elif change == "headers":
        del handles[0]["response"]["set"]["X-Robots-Tag"]
    elif change == "upstream":
        handles[2]["routes"][1]["handle"][0]["upstreams"][0]["dial"] = "production-backend:8000"
    elif change == "listener":
        server["listen"] = [":80"]
    else:
        original["apps"]["http"]["servers"]["extra"] = server
    with pytest.raises(ValueError):
        controller().maintenance_config(original)
