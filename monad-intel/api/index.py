"""Vercel serverless entry point — re-exports the FastAPI app."""
import sys
from pathlib import Path

# Make the `app` package importable when Vercel sets cwd to the api/ folder.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app  # noqa: E402,F401  (imported for Vercel)
