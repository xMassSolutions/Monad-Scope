"""Project API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.schemas.common import ProjectStatus


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    canonical_name: str
    slug: str
    status: ProjectStatus
    creator_cluster: str | None
    website: str | None
    socials: dict[str, Any] | None
    first_seen_at: datetime
    last_seen_at: datetime


class ProjectWithContracts(BaseModel):
    project: ProjectRead
    contract_ids: list[str]
