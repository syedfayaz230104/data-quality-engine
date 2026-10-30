import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Tuple, Set
from .models import RuleDefinition, EvaluationResult, QuarantinedRecord

class RuleEvaluator:
    """Evaluates individual data quality rules across datasets."""

    def __init__(self, run_id: str):
        self.run_id = run_id

    def evaluate_rule(
        self,
        rule: RuleDefinition,
        records: List[Dict[str, Any]],
        parent_records_map: Dict[str, Set[str]] = None
    ) -> EvaluationResult:
        """Evaluates a single rule over a list of record dictionaries."""
        if parent_records_map is None:
            parent_records_map = {}

        total_records = len(records)
        if total_records == 0:
            return EvaluationResult(
                eval_id=str(uuid.uuid4()),
                run_id=self.run_id,
                dataset=rule.dataset,
                rule_id=rule.rule_id,
                rule_name=rule.rule_name,
                rule_type=rule.rule_type,
                severity=rule.severity,
                records_evaluated=0,
                records_passed=0,
                records_failed=0,
                pass_rate=1.0,
                status="PASSED"
            )

        failed_record_ids = []
        failure_details = []

        if rule.rule_type == "completeness":
            failed_record_ids, failure_details = self._check_completeness(rule, records)
        elif rule.rule_type == "uniqueness":
            failed_record_ids, failure_details = self._check_uniqueness(rule, records)
        elif rule.rule_type == "referential_integrity":
            failed_record_ids, failure_details = self._check_referential_integrity(rule, records, parent_records_map)
        elif rule.rule_type == "range":
            failed_record_ids, failure_details = self._check_range(rule, records)
        elif rule.rule_type == "freshness":
            failed_record_ids, failure_details = self._check_freshness(rule, records)
        elif rule.rule_type == "custom":
            failed_record_ids, failure_details = self._check_custom(rule, records)
        else:
            raise ValueError(f"Unknown rule type: {rule.rule_type}")

        failed_count = len(failed_record_ids)
        passed_count = total_records - failed_count
        pass_rate = round(passed_count / total_records, 4) if total_records > 0 else 1.0
        status = "PASSED" if failed_count == 0 else ("WARNING" if rule.severity == "WARNING" else "FAILED")

        return EvaluationResult(
            eval_id=str(uuid.uuid4()),
            run_id=self.run_id,
            dataset=rule.dataset,
            rule_id=rule.rule_id,
            rule_name=rule.rule_name,
            rule_type=rule.rule_type,
            severity=rule.severity,
            records_evaluated=total_records,
            records_passed=passed_count,
            records_failed=failed_count,
            pass_rate=pass_rate,
            status=status,
            failed_record_ids=failed_record_ids,
            failure_details=failure_details
        )

    def _get_record_key(self, dataset: str, rec: Dict[str, Any]) -> str:
        key_map = {
            "customers": "customer_id",
            "products": "product_id",
            "orders": "order_id",
            "order_items": "item_id"
        }
        pk = key_map.get(dataset, "id")
        return str(rec.get(pk, "UNKNOWN_KEY"))

    def _check_completeness(self, rule: RuleDefinition, records: List[Dict[str, Any]]) -> Tuple[List[str], List[Dict[str, Any]]]:
        failed_ids = []
        details = []
        cols = rule.columns or ([rule.column] if rule.column else [])
        for rec in records:
            key = self._get_record_key(rule.dataset, rec)
            missing = [c for c in cols if c not in rec or rec[c] is None or (isinstance(rec[c], str) and rec[c].strip() == "")]
            if missing:
                failed_ids.append(key)
                details.append({
                    "record_key": key,
                    "reason": f"Null or empty values in columns: {missing}",
                    "record": rec
                })
        return failed_ids, details

    def _check_uniqueness(self, rule: RuleDefinition, records: List[Dict[str, Any]]) -> Tuple[List[str], List[Dict[str, Any]]]:
        failed_ids = []
        details = []
        seen = set()
        cols = rule.columns or ([rule.column] if rule.column else [])
        for rec in records:
            key = self._get_record_key(rule.dataset, rec)
            combo_val = tuple(rec.get(c) for c in cols)
            if combo_val in seen:
                failed_ids.append(key)
                details.append({
                    "record_key": key,
                    "reason": f"Duplicate key detected for {cols}: {combo_val}",
                    "record": rec
                })
            else:
                seen.add(combo_val)
        return failed_ids, details

    def _check_referential_integrity(
        self,
        rule: RuleDefinition,
        records: List[Dict[str, Any]],
        parent_map: Dict[str, Set[str]]
    ) -> Tuple[List[str], List[Dict[str, Any]]]:
        failed_ids = []
        details = []
        fk_col = rule.foreign_key
        parent_dataset = rule.parent_dataset
        valid_parent_keys = parent_map.get(parent_dataset, set())

        for rec in records:
            key = self._get_record_key(rule.dataset, rec)
            fk_val = str(rec.get(fk_col)) if rec.get(fk_col) is not None else None
            if not fk_val or fk_val not in valid_parent_keys:
                failed_ids.append(key)
                details.append({
                    "record_key": key,
                    "reason": f"Referential integrity failure: {fk_col}='{fk_val}' does not exist in {parent_dataset}",
                    "record": rec
                })
        return failed_ids, details

    def _check_range(self, rule: RuleDefinition, records: List[Dict[str, Any]]) -> Tuple[List[str], List[Dict[str, Any]]]:
        failed_ids = []
        details = []
        col = rule.column
        for rec in records:
            key = self._get_record_key(rule.dataset, rec)
            val = rec.get(col)
            if val is None:
                continue

            # Numeric range check
            if rule.min_value is not None and isinstance(val, (int, float)):
                if val < rule.min_value:
                    failed_ids.append(key)
                    details.append({
                        "record_key": key,
                        "reason": f"Value {val} in column '{col}' is below min_value {rule.min_value}",
                        "record": rec
                    })
                    continue

            if rule.max_value is not None and isinstance(val, (int, float)):
                if val > rule.max_value:
                    failed_ids.append(key)
                    details.append({
                        "record_key": key,
                        "reason": f"Value {val} in column '{col}' is above max_value {rule.max_value}",
                        "record": rec
                    })
                    continue

            # String length range check
            if rule.min_length is not None and isinstance(val, str):
                if len(val) < rule.min_length:
                    failed_ids.append(key)
                    details.append({
                        "record_key": key,
                        "reason": f"Length {len(val)} of column '{col}' is below min_length {rule.min_length}",
                        "record": rec
                    })
                    continue

            if rule.max_length is not None and isinstance(val, str):
                if len(val) > rule.max_length:
                    failed_ids.append(key)
                    details.append({
                        "record_key": key,
                        "reason": f"Length {len(val)} of column '{col}' exceeds max_length {rule.max_length}",
                        "record": rec
                    })
                    continue

        return failed_ids, details

    def _check_freshness(self, rule: RuleDefinition, records: List[Dict[str, Any]]) -> Tuple[List[str], List[Dict[str, Any]]]:
        failed_ids = []
        details = []
        col = rule.column
        now = datetime.now(timezone.utc)
        allowed_future = timedelta(seconds=rule.allow_future_seconds or 0)
        cutoff = now - timedelta(days=rule.max_days_old) if rule.max_days_old is not None else None

        for rec in records:
            key = self._get_record_key(rule.dataset, rec)
            val = rec.get(col)
            if not val:
                continue

            try:
                dt_val = datetime.fromisoformat(str(val).replace("Z", "+00:00"))
                if dt_val.tzinfo is None:
                    dt_val = dt_val.replace(tzinfo=timezone.utc)

                # Future check
                if dt_val > (now + allowed_future):
                    failed_ids.append(key)
                    details.append({
                        "record_key": key,
                        "reason": f"Freshness violation: timestamp '{val}' in '{col}' is in the future",
                        "record": rec
                    })
                    continue

                # Max age check
                if cutoff is not None and dt_val < cutoff:
                    failed_ids.append(key)
                    details.append({
                        "record_key": key,
                        "reason": f"Freshness violation: timestamp '{val}' in '{col}' is older than {rule.max_days_old} days",
                        "record": rec
                    })
                    continue
            except Exception as e:
                failed_ids.append(key)
                details.append({
                    "record_key": key,
                    "reason": f"Timestamp parsing failure in '{col}': {str(e)}",
                    "record": rec
                })

        return failed_ids, details

    def _check_custom(self, rule: RuleDefinition, records: List[Dict[str, Any]]) -> Tuple[List[str], List[Dict[str, Any]]]:
        failed_ids = []
        details = []
        expr = rule.expression

        # Standard safe evaluation context with precompiled bytecode for high throughput
        py_expr = expr
        py_expr = py_expr.replace(" IN (", " in [").replace(")", "]") if " IN (" in py_expr else py_expr

        try:
            compiled_code = compile(py_expr, "<dq_rule>", "eval")
        except Exception as e:
            compiled_code = None

        builtins_env = {
            "abs": abs,
            "round": round,
            "min": min,
            "max": max,
            "len": len,
        }

        for rec in records:
            key = self._get_record_key(rule.dataset, rec)
            if compiled_code is None:
                failed_ids.append(key)
                details.append({
                    "record_key": key,
                    "reason": f"Syntax error compiling custom rule expression '{expr}'",
                    "record": rec
                })
                continue

            eval_env = {**builtins_env, **rec}
            try:
                result = eval(compiled_code, {"__builtins__": {}}, eval_env)
                if not bool(result):
                    failed_ids.append(key)
                    details.append({
                        "record_key": key,
                        "reason": f"Custom rule failed: expression '{expr}' evaluated to False",
                        "record": rec
                    })
            except Exception as e:
                failed_ids.append(key)
                details.append({
                    "record_key": key,
                    "reason": f"Custom rule evaluation error for '{expr}': {str(e)}",
                    "record": rec
                })

        return failed_ids, details
