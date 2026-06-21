"""Aggregate API router (v1)."""

from fastapi import APIRouter

from app.api import (
    ai,
    auth,
    dashboards,
    documents,
    ethics,
    funding,
    kpi,
    organization,
    outputs,
    projects,
    proposals,
    reports,
    researchers,
    reviews,
    users,
    workflow,
)

api_router = APIRouter()
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(organization.router, prefix="/units", tags=["organization"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(researchers.router, prefix="/researchers", tags=["researchers"])
api_router.include_router(funding.router, tags=["funding"])
api_router.include_router(proposals.router, prefix="/proposals", tags=["proposals"])
api_router.include_router(reviews.router, tags=["reviews"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(outputs.router, tags=["outputs"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(workflow.router, tags=["workflow"])
api_router.include_router(dashboards.router, prefix="/dashboards", tags=["dashboards"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(ethics.router, prefix="/ethics", tags=["ethics"])
api_router.include_router(kpi.router, tags=["kpi"])
