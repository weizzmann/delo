# backend/app/api_v1/health.py
from . import bp

@bp.get("/health")
def health():
    return {"status": "ok"}
