from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, Optional

@dataclass
class PipelineMetrics:
    run_id: str
    pipeline_name: str
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    status: str = "PENDING"
    input_counts: Dict[str, int] = field(default_factory=dict)
    target_counts: Dict[str, int] = field(default_factory=dict)
    quarantine_counts: Dict[str, int] = field(default_factory=dict)
    warning_count: int = 0
    error_count: int = 0
    error_summary: Optional[str] = None

    @property
    def total_input_rows(self) -> int:
        return sum(self.input_counts.values())

    @property
    def total_target_rows(self) -> int:
        return sum(self.target_counts.values())

    @property
    def total_quarantined_rows(self) -> int:
        return sum(self.quarantine_counts.values())

    @property
    def duration_seconds(self) -> float:
        if self.end_time and self.start_time:
            return round((self.end_time - self.start_time).total_seconds(), 4)
        return 0.0

    def mark_completed(self, status: str = "SUCCESS", error_summary: Optional[str] = None):
        self.end_time = datetime.now(timezone.utc)
        self.status = status
        self.error_summary = error_summary
