from opentelemetry.distro import OpenTelemetryDistro
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.sdk.resources import Resource
import os
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

def configure_tracing(app):
    """Configures OpenTelemetry for the application."""
    os.environ["OTEL_SERVICE_NAME"] = "guardian-ai"
    distro = OpenTelemetryDistro()
    distro.configure()

    FastAPIInstrumentor.instrument_app(app)
    CeleryInstrumentor().instrument()
