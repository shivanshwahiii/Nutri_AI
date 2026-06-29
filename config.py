"""
nutri_ai/config.py
──────────────────
Single source of truth for all configuration.
Loads .env at import time — every other module imports from here.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the same directory as this file
_HERE = Path(__file__).parent
load_dotenv(dotenv_path=_HERE / ".env", override=True)

# ── Required ──────────────────────────────────────────────────────────────────
# Strip whitespace/carriage returns — fixes Windows \r\n line ending issues
GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "").strip()

if not GOOGLE_API_KEY or "paste" in GOOGLE_API_KEY.lower():
    raise EnvironmentError(
        "\n\n❌  GOOGLE_API_KEY not set!\n"
        "   1. Open .env file\n"
        "   2. Set GOOGLE_API_KEY=your_actual_key\n"
        "   3. Run again.\n"
    )

# Set BOTH env vars — ADK reads GOOGLE_API_KEY, some tools read GEMINI_API_KEY
os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY
os.environ["GEMINI_API_KEY"] = GOOGLE_API_KEY

# ── Optional with sensible defaults ──────────────────────────────────────────
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip()
GRADIO_PORT: int   = int(os.getenv("GRADIO_PORT", "7860").strip())
GRADIO_SHARE: bool = os.getenv("GRADIO_SHARE", "False").strip().lower() == "true"

# ── App constants ─────────────────────────────────────────────────────────────
APP_NAME   = "NutriAI"
USER_ID    = "default_user"
SESS_PFX   = "nutriai"

# Shared cuisine context injected into every agent system prompt
CUISINE = (
    "Indian non-vegetarian cuisine — including North Indian (Butter Chicken, "
    "Rogan Josh, Keema Matar, Tandoori Chicken, Chicken Korma), South Indian "
    "(Chettinad Chicken), Coastal (Goan Fish Curry, Prawn Masala), Hyderabadi "
    "(Mutton Biryani, Chicken Biryani), and Pan-Indian (Egg Bhurji, Fish Curry)."
)