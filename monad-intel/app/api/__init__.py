"""FastAPI router aggregator."""

from fastapi import APIRouter

from app.api import (
    admin,
    auth,
    contracts,
    cron,
    health,
    library,
    outcomes,
    prime,
    projects,
    rulesets,
)


def get_api_router() -> APIRouter:
    r = APIRouter()
    r.include_router(health.router, tags=["health"])
    r.include_router(auth.router, tags=["auth"])
    r.include_router(contracts.router, tags=["contracts"])
    r.include_router(prime.router, tags=["prime"])
    r.include_router(projects.router, tags=["projects"])
    r.include_router(library.router, tags=["library"])
    r.include_router(admin.router, tags=["admin"])
    r.include_router(outcomes.router, tags=["outcomes"])
    r.include_router(rulesets.router, tags=["rulesets"])
    r.include_router(cron.router, tags=["cron"])
    return r
