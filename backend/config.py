"""Loads settings from environment variables (.env locally, dashboard on Render).

Secrets are only ever read here and never logged.
"""
import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    BUSINESS_ACCOUNT_ID = os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID", "")
    GRAPH_API_VERSION = os.getenv("GRAPH_API_VERSION", "v23.0")
    META_API_BASE = os.getenv("META_API_BASE", "https://graph.facebook.com").rstrip("/")
    VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN", "")
    APP_SECRET = os.getenv("META_APP_SECRET", "")
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///whatsapp.db")
    FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")

    @classmethod
    def missing(cls):
        """Names of required settings that are empty (names only, never values)."""
        required = {
            "WHATSAPP_ACCESS_TOKEN": cls.ACCESS_TOKEN,
            "WHATSAPP_PHONE_NUMBER_ID": cls.PHONE_NUMBER_ID,
            "WEBHOOK_VERIFY_TOKEN": cls.VERIFY_TOKEN,
        }
        return [name for name, value in required.items() if not value]
