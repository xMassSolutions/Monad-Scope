"""Project API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.repositories import projects as projects_repo
from app.schemas.project import ProjectRead, ProjectWithContracts

router = APIRouter()


@router.get("/projects/{project_id}", response_model=ProjectWithContracts)
async def get_project(
    project_id: str, session: AsyncSession = Depends(get_session)
) -> ProjectWithContracts:
    p = await projects_repo.get_by_id(session, project_id)
    if p is None:
        raise HTTPException(404, detail="project not found")
    ids = await projects_repo.list_contract_ids(session, project_id)
    return ProjectWithContracts(project=ProjectRead.model_validate(p), contract_ids=ids)
