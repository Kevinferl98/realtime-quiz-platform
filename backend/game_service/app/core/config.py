import os

class Config:
    ENV = os.getenv("APP_ENV", "development")
    DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t") or ENV == "development"
    LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG" if DEBUG else "INFO")

    # --- REDIS ---
    REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

    # --- OBSERVABILITY ---
    OTEL_SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "game_service")
    OTEL_EXPORTER_OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://tempo:4317")

    # --- KEYCLOAK ---
    KEYCLOAK_URL = os.getenv("KEYCLOAK_URL")
    KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM")
    KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID")
    KEYCLOAK_ISSUER = os.getenv("KEYCLOAK_ISSUER")

config = Config()
