"""Optional OTLP metrics export configured from environment."""

from __future__ import annotations

from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource

_configured = False


def configure_metrics(*, endpoint: str, service_name: str) -> bool:
    """Install one OTLP metric provider; stay disabled when no endpoint is set."""

    global _configured
    if not endpoint:
        return False
    if _configured:
        return True
    exporter = OTLPMetricExporter(endpoint=endpoint)
    reader = PeriodicExportingMetricReader(exporter)
    provider = MeterProvider(
        resource=Resource.create({"service.name": service_name}),
        metric_readers=[reader],
    )
    metrics.set_meter_provider(provider)
    _configured = True
    return True
