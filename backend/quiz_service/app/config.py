import os

class Config:
    ENV = os.getenv("APP_ENV", "development")
    DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t") or ENV == "development"
    LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG" if DEBUG else "INFO")
    OTEL_SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "quiz_service")
    OTEL_EXPORTER_OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://tempo:4317")

config = Config()
