"""Small opt-in OpenTelemetry helpers."""

from __future__ import annotations

from contextlib import AbstractContextManager, nullcontext
from dataclasses import dataclass
from typing import Any

from ithildin_schemas import JsonObject, JsonValue
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor
from opentelemetry.trace import Span, Tracer

from ithildin_api.config import Settings


@dataclass(frozen=True)
class Telemetry:
    enabled: bool
    service_name: str
    console_export: bool
    otlp_endpoint: str
    tracer: Tracer | None = None

    def start_span(
        self,
        name: str,
        attributes: dict[str, str | int | bool | float] | None = None,
    ) -> AbstractContextManager[Span | None]:
        if not self.enabled or self.tracer is None:
            return nullcontext(None)
        return self.tracer.start_as_current_span(name, attributes=attributes or {})

    def status(self) -> JsonObject:
        exporters: list[JsonValue] = [exporter for exporter in self._exporters()]
        return {
            "enabled": self.enabled,
            "service_name": self.service_name,
            "console_export": self.console_export,
            "otlp_endpoint_configured": bool(self.otlp_endpoint),
            "exporters": exporters,
        }

    def _exporters(self) -> list[str]:
        exporters: list[str] = []
        if self.console_export:
            exporters.append("console")
        if self.otlp_endpoint:
            exporters.append("otlp_http")
        return exporters


def configure_telemetry(settings: Settings) -> Telemetry:
    if not settings.otel_enabled:
        return Telemetry(
            enabled=False,
            service_name=settings.otel_service_name,
            console_export=settings.otel_console_export,
            otlp_endpoint=settings.otel_otlp_endpoint,
        )

    provider = TracerProvider(
        resource=Resource.create(
            {
                "service.name": settings.otel_service_name,
                "ithildin.preview": True,
            }
        )
    )
    if settings.otel_console_export:
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    if settings.otel_otlp_endpoint:
        provider.add_span_processor(
            SimpleSpanProcessor(OTLPSpanExporter(endpoint=settings.otel_otlp_endpoint))
        )
    return Telemetry(
        enabled=True,
        service_name=settings.otel_service_name,
        console_export=settings.otel_console_export,
        otlp_endpoint=settings.otel_otlp_endpoint,
        tracer=provider.get_tracer("ithildin"),
    )


def safe_span_attributes(**attributes: Any) -> dict[str, str | int | bool | float]:
    safe: dict[str, str | int | bool | float] = {}
    for key, value in attributes.items():
        if isinstance(value, str | int | bool | float):
            safe[key] = value
    return safe
