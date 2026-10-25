from fastapi.routing import APIRoute

from app.modules.child.router import router

EXPECTED = {
    ("/child/children", "GET"),
    ("/child/children", "POST"),
    ("/child/children/{child_id}", "GET"),
    ("/child/children/{child_id}", "PATCH"),
    ("/child/children/{child_id}", "DELETE"),
    ("/child/children/{child_id}/export", "GET"),
    ("/child/children/{child_id}/questionnaires/current", "GET"),
    ("/child/questionnaires/{session_id}/answers", "PUT"),
    ("/child/questionnaires/{session_id}/complete", "POST"),
    ("/child/reports", "POST"),
    ("/child/generations/{generation_id}", "GET"),
    ("/child/reports/{report_id}", "GET"),
    ("/child/reports/{report_id}/sections", "GET"),
    ("/child/reports/{report_id}/versions", "GET"),
    ("/child/reports/{report_id}/regenerate", "POST"),
    ("/child/reports/{report_id}/age-updates", "POST"),
    ("/child/reports/{report_id}/age-snapshots", "GET"),
    ("/child/reports/{report_id}/pdf", "GET"),
}


def test_all_documented_routes_have_access_operation_and_response_contract() -> None:
    routes = [route for route in router.routes if isinstance(route, APIRoute)]
    assert {(route.path, method) for route in routes for method in (route.methods or set())} == EXPECTED
    for route in routes:
        assert getattr(route.endpoint, "child_access_operation", None)
        assert route.response_model or route.path.endswith("/pdf") or "DELETE" in (route.methods or set())


def test_child_openapi_matches_runtime_including_nested_component_schemas() -> None:
    from pathlib import Path

    import yaml

    from app.main import app

    spec = yaml.safe_load((Path(__file__).parents[4] / "contracts/openapi.yaml").read_text())
    runtime = app.openapi()
    paths = {
        path.removeprefix("/api"): value
        for path, value in runtime["paths"].items()
        if path.startswith("/api/v1/child/")
    }
    canonical = {path: value for path, value in spec["paths"].items() if path.startswith("/v1/child/")}
    assert set(paths) == set(canonical)
    refs: set[str] = set()

    def collect(value: object) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key == "$ref" and isinstance(item, str) and item.startswith("#/components/schemas/"):
                    refs.add(item.rsplit("/", 1)[-1])
                collect(item)
        elif isinstance(value, list):
            for item in value:
                collect(item)

    for path, item in paths.items():
        for method, operation in item.items():
            actual = canonical[path][method]
            assert actual["security"] == [{"bearerAuth": []}, {"ChildCookieAuth": []}]
            assert operation["security"] == [{"HTTPBearer": []}, {"ChildCookieAuth": []}]
            for key in ("parameters", "requestBody", "responses"):
                assert actual.get(key) == operation.get(key)
            collect(operation)
    checked: set[str] = set()
    while refs - checked:
        name = next(iter(refs - checked))
        expected = runtime["components"]["schemas"][name]
        assert spec["components"]["schemas"][name] == expected
        checked.add(name)
        collect(expected)
