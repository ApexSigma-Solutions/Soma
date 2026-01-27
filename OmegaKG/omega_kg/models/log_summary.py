from typing import List, Optional
from pydantic import BaseModel


class LogSummaryStats(BaseModel):
    service: str
    level: str
    count: int


class CriticalError(BaseModel):
    service: str
    message: str
    timestamp: str
    count: int


class LogSummaryReport(BaseModel):
    date: str
    generated_at: str
    monitoring_started: str
    stats: List[LogSummaryStats] = []
    critical_errors: List[CriticalError] = []
    warnings: List[str] = []
    suggested_actions: List[str] = []


class LogSummaryResponse(BaseModel):
    status: str
    report: Optional[LogSummaryReport] = None
    message: Optional[str] = None
