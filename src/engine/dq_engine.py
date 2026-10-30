import yaml
import os
from typing import List, Dict, Any, Tuple, Set
from .models import RuleDefinition, EvaluationResult, QuarantinedRecord
from .rule_evaluator import RuleEvaluator
from ..utils.logger import setup_logger

class DataQualityEngine:
    """Configurable Data Quality Engine managing rule definitions, execution, and quarantine routing."""

    def __init__(self, rules_file_path: str, run_id: str):
        self.rules_file_path = rules_file_path
        self.run_id = run_id
        self.logger = setup_logger("DQEngine")
        self.rules: List[RuleDefinition] = self._load_rules()
        self.evaluator = RuleEvaluator(run_id=run_id)

    def _load_rules(self) -> List[RuleDefinition]:
        """Loads and parses rules from the YAML configuration."""
        if not os.path.exists(self.rules_file_path):
            self.logger.warning(f"Rules file not found at: {self.rules_file_path}. Using empty rules.")
            return []

        with open(self.rules_file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        rules = []
        for r in data.get("rules", []):
            rules.append(RuleDefinition(
                rule_id=r["rule_id"],
                dataset=r["dataset"],
                rule_type=r["rule_type"],
                rule_name=r["rule_name"],
                severity=r.get("severity", "ERROR"),
                description=r.get("description", ""),
                columns=r.get("columns"),
                column=r.get("column"),
                expression=r.get("expression"),
                foreign_key=r.get("foreign_key"),
                parent_dataset=r.get("parent_dataset"),
                parent_key=r.get("parent_key"),
                min_value=r.get("min_value"),
                max_value=r.get("max_value"),
                min_length=r.get("min_length"),
                max_length=r.get("max_length"),
                max_days_old=r.get("max_days_old"),
                allow_future_seconds=r.get("allow_future_seconds", 0)
            ))
        return rules

    def get_rules_for_dataset(self, dataset: str) -> List[RuleDefinition]:
        return [r for r in self.rules if r.dataset == dataset]

    def evaluate_dataset(
        self,
        dataset: str,
        records: List[Dict[str, Any]],
        parent_keys_map: Dict[str, Set[str]] = None
    ) -> Tuple[List[Dict[str, Any]], List[QuarantinedRecord], List[EvaluationResult]]:
        """
        Runs all rules defined for the dataset.
        Records violating ERROR or CRITICAL rules are filtered to quarantine.
        Records violating WARNING rules generate an audit entry but pass through.
        """
        rules = self.get_rules_for_dataset(dataset)
        eval_results: List[EvaluationResult] = []
        quarantined_record_ids: Set[int] = set()
        quarantined_list: List[QuarantinedRecord] = []

        for rule in rules:
            result = self.evaluator.evaluate_rule(rule, records, parent_keys_map)
            eval_results.append(result)

            if result.records_failed > 0:
                self.logger.info(
                    f"Rule [{rule.rule_id}] {rule.rule_name} ({rule.severity}) failed for {result.records_failed} records."
                )

                # Route to quarantine if ERROR or CRITICAL
                if rule.severity in ["ERROR", "CRITICAL"]:
                    for fail_detail in result.failure_details:
                        rec = fail_detail["record"]
                        rec_obj_id = id(rec)
                        rec_key = fail_detail["record_key"]
                        if rec_obj_id not in quarantined_record_ids:
                            quarantined_record_ids.add(rec_obj_id)
                            quarantined_list.append(QuarantinedRecord(
                                quarantine_id=f"QUAR_{self.run_id[:8]}_{dataset}_{rec_key}_{len(quarantined_list)+1}",
                                run_id=self.run_id,
                                source_dataset=dataset,
                                source_record_key=rec_key,
                                rule_id=rule.rule_id,
                                rule_name=rule.rule_name,
                                severity=rule.severity,
                                failure_reason=fail_detail["reason"],
                                raw_record=rec
                            ))

        # Separate valid records from quarantined
        valid_records = [
            r for r in records
            if id(r) not in quarantined_record_ids
        ]

        return valid_records, quarantined_list, eval_results
