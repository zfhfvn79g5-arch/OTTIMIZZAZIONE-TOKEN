"""Configurazione del progetto, letta da variabili d'ambiente e dal file `.env`."""

from __future__ import annotations

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_MODEL = "claude-opus-5-5"


class Settings(BaseSettings):
    """
    Impostazioni dell'applicazione.

    Le variabili hanno prefisso `OTTIMIZZAZIONE_`, tranne la chiave API che usa
    il nome standard `ANTHROPIC_API_KEY`.
    """

    model_config = SettingsConfigDict(
        env_prefix="OTTIMIZZAZIONE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Motivo: se la chiave manca, l'SDK risolve da solo ANTHROPIC_AUTH_TOKEN o il
    # profilo di `ant auth login`, quindi qui è facoltativa.
    anthropic_api_key: SecretStr | None = Field(default=None, validation_alias="ANTHROPIC_API_KEY")
    default_model: str = DEFAULT_MODEL
    max_retries: int = Field(default=2, ge=0)
    timeout: float = Field(default=600.0, gt=0)


def get_settings() -> Settings:
    """
    Carica le impostazioni correnti.

    Returns:
        Settings: Impostazioni lette da ambiente e `.env`.
    """
    return Settings()
