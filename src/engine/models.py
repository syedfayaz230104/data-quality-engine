from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

@dataclass
class RuleDefinition:
    rule_id: str
    dataset: str
    rule_type: str
    rule_name: str
    severity: str = "ERROR" # INFO, WARNING, ERROR, CRITICAL
    description: str = ""
    columns: Optional[List[str]] = None
    column: Optional[str] = None
    expression: Optional[str] = None
    foreign_key: Optional[str] = None
    parent_dataset: Optional[str] = None
    parent_key: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    max_days_old: Optional[int] = None
    allow_future_seconds: Optional[int] = 0

@dataclass
class EvaluationResult:
    eval_id: str
    run_id: str
    dataset: str
    rule_id: str
    rule_name: str
    rule_type: str
    severity: str
    records_evaluated: int
    records_passed: int
    records_failed: int
    pass_rate: float
    status: str # PASSED, FAILED, WARNING
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    failed_record_ids: List[str] = field(default_factory=list)
    failure_details: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class QuarantinedRecord:
    quarantine_id: str
    run_id: str
    source_dataset: str
    source_record_key: Optional[str]
    rule_id: str
    rule_name: str
    severity: str
    failure_reason: str
    raw_record: Dict[str, Any]
    quarantined_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
