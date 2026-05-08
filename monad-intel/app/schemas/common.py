"""Shared enums and pagination types."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class RiskTier(str, Enum):
    SAFE = "SAFE"
    CAUTION = "CAUTION"
    HIGH_RISK = "HIGH_RISK"
    CRITICAL = "CRITICAL"


class Action(str, Enum):
    ALLOW = "ALLOW"
    WARN = "WARN"
    ESCALATE = "ESCALATE"
    BLOCK = "BLOCK"


class AnalysisStage(str, Enum):
    INITIAL = "initial"
    REFINED = "refined"


class Severity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ContractKind(str, Enum):
    TOKEN = "token"
    LP_PAIR = "lp_pair"
    ROUTER = "router"
    FACTORY = "factory"
    PROXY = "proxy"
    IMPLEMENTATION = "implementation"
    TREASURY = "treasury"
    STAKING = "staking"
    GOVERNANCE = "governance"
    NFT = "nft"
    UTILITY = "utility"
    UNKNOWN = "unknown"


class ProjectStatus(str, Enum):
    LIVE = "live_project"
    WATCHLIST = "watchlist"
    INFRA_ONLY = "infra_only"
    NOISE_OR_DEAD = "noise_or_dead"
    SUSPICIOUS_CLUSTER = "suspicious_cluster"


class OutcomeLabel(str, Enum):
    SAFE = "safe"
    RUG_PULL = "rug_pull"
    HONEYPOT = "honeypot"
    LP_REMOVED = "lp_removed"
    ABANDONED = "abandoned"
    EXPLOITED = "exploited"
    UNKNOWN = "unknown"


class PrimeState(str, Enum):
    AVAILABLE = "available"
    IN_PROGRESS = "in_progress"
    NOT_PURCHASED = "not_purchased"
    FAILED = "failed"


class Pagination(BaseModel):
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
