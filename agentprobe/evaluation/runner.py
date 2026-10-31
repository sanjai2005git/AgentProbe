"""
Evaluation Harness and Benchmark Suite Runner.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from pathlib import Path
import json
import csv
from pydantic import BaseModel, Field

from agentprobe.domain.database import PaymentDatabase
from agentprobe.domain.models import Transaction, Account, Merchant, RiskProfile, RiskLevel
from agentprobe.tools.registry import get_default_registry, ToolRegistry
from agentprobe.llm.base import BaseLLMProvider
from agentprobe.llm.mock_provider import MockBehavioralProvider
from agentprobe.agents.factory import create_agent
from agentprobe.agents.base import Trajectory
from agentprobe.scenarios.schema import Scenario
from agentprobe.evaluation.metrics import MetricsEvaluator, EvaluationMetricRecord
from agentprobe.evaluation.taxonomy import FailureMode


class BenchmarkSummary(BaseModel):
    total_runs: int
    task_success_rate: float
    avg_tool_precision: float
    avg_tool_recall: float
    avg_tool_f1: float
    avg_argument_correctness: float
    total_unnecessary_tool_calls: int
    avg_step_efficiency: float
    avg_latency_ms: float
    total_cost_usd: float
    adversarial_resistance_rate: Optional[float] = None
    failure_mode_breakdown: Dict[str, int] = Field(default_factory=dict)


class BenchmarkSuiteResult(BaseModel):
    suite_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    scenarios_evaluated: int
    models_tested: List[str]
    architectures_tested: List[str]
    overall_summary: BenchmarkSummary
    by_architecture: Dict[str, BenchmarkSummary] = Field(default_factory=dict)
    by_model: Dict[str, BenchmarkSummary] = Field(default_factory=dict)
    records: List[EvaluationMetricRecord] = Field(default_factory=list)


class EvaluationHarness:
    """Manages isolated test execution, database seeding, trajectory recording, and evaluation aggregation."""

    def __init__(self, tools: Optional[ToolRegistry] = None):
        self.tools = tools or get_default_registry()

    def _setup_isolated_db(self, scenario: Scenario) -> PaymentDatabase:
        """Creates a pristine in-memory SQLite database populated with the scenario's fixtures."""
        db = PaymentDatabase(":memory:")

        # Default base merchant and account fixtures
        db.insert_account(Account(id="ACCT-001", cardholder_name="Alice Standard", email="alice@example.com"))
        db.insert_account(Account(id="ACCT-CORP-1", cardholder_name="Acme Corp Ops", email="ops@acme.com"))
        db.insert_merchant(Merchant(id="MERCH-RETAIL-01", name="GlobalRetail Inc", category="RETAIL"))
        db.insert_merchant(Merchant(id="MERCH-SAAS-02", name="CloudSaaS Pro", category="SOFTWARE"))
        db.insert_merchant(Merchant(id="MERCH-CRYPTO-99", name="BitExchange Global", category="CRYPTO", risk_rating=0.45))
        db.insert_merchant(Merchant(id="MERCH-LUXURY-01", name="Prestige Watches", category="LUXURY"))

        # Seed initial state from scenario
        init_state = scenario.initial_db_state
        for tx_dict in init_state.get("transactions", []):
            db.insert_transaction(Transaction(**tx_dict))

        for rp_dict in init_state.get("risk_profiles", []):
            db.insert_risk_profile(RiskProfile(
                transaction_id=rp_dict["transaction_id"],
                risk_score=rp_dict["risk_score"],
                risk_level=RiskLevel(rp_dict["risk_level"]),
                anomaly_flags=rp_dict["anomaly_flags"],
                recommended_action=rp_dict["recommended_action"],
            ))

        return db

    def run_single(
        self,
        scenario: Scenario,
        architecture: str,
        llm: BaseLLMProvider,
    ) -> Tuple[Trajectory, EvaluationMetricRecord]:
        """Runs a single scenario in an isolated sandbox and returns trajectory and metrics."""
        db = self._setup_isolated_db(scenario)
        agent = create_agent(architecture=architecture, llm=llm, tools=self.tools)

        trajectory = agent.run(
            task_prompt=scenario.user_prompt,
            db=db,
            scenario_id=scenario.id,
        )

        metric_record = MetricsEvaluator.evaluate(trajectory, scenario, db)
        return trajectory, metric_record

    def run_benchmark(
        self,
        scenarios: List[Scenario],
        architectures: List[str],
        models: List[BaseLLMProvider],
    ) -> BenchmarkSuiteResult:
        """Executes full benchmark suite across scenarios, architectures, and models."""
        suite_id = f"BENCH-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
        all_records: List[EvaluationMetricRecord] = []

        for model in models:
            for arch in architectures:
                for scenario in scenarios:
                    _, record = self.run_single(scenario, arch, model)
                    all_records.append(record)

        # Aggregate overall summary
        overall_summary = self._summarize_records(all_records)

        # Aggregate by architecture
        by_arch: Dict[str, BenchmarkSummary] = {}
        for arch in architectures:
            arch_records = [r for r in all_records if r.architecture == arch]
            if arch_records:
                by_arch[arch] = self._summarize_records(arch_records)

        # Aggregate by model
        by_model: Dict[str, BenchmarkSummary] = {}
        for model in models:
            model_records = [r for r in all_records if r.model_name == model.model_name]
            if model_records:
                by_model[model.model_name] = self._summarize_records(model_records)

        return BenchmarkSuiteResult(
            suite_id=suite_id,
            scenarios_evaluated=len(scenarios),
            models_tested=[m.model_name for m in models],
            architectures_tested=architectures,
            overall_summary=overall_summary,
            by_architecture=by_arch,
            by_model=by_model,
            records=all_records,
        )

    def _summarize_records(self, records: List[EvaluationMetricRecord]) -> BenchmarkSummary:
        if not records:
            return BenchmarkSummary(
                total_runs=0,
                task_success_rate=0.0,
                avg_tool_precision=0.0,
                avg_tool_recall=0.0,
                avg_tool_f1=0.0,
                avg_argument_correctness=0.0,
                total_unnecessary_tool_calls=0,
                avg_step_efficiency=0.0,
                avg_latency_ms=0.0,
                total_cost_usd=0.0,
                failure_mode_breakdown={},
            )

        n = len(records)
        successes = sum(1 for r in records if r.task_success)
        precision = sum(r.tool_precision for r in records) / n
        recall = sum(r.tool_recall for r in records) / n
        f1 = sum(r.tool_f1 for r in records) / n
        arg_corr = sum(r.argument_correctness for r in records) / n
        unnecessary = sum(r.unnecessary_tool_calls for r in records)
        step_eff = sum(r.step_efficiency for r in records) / n
        lat = sum(r.total_duration_ms for r in records) / n
        cost = sum(r.estimated_cost_usd for r in records)

        # Adversarial resistance
        adv_records = [r for r in records if r.adversarial_resisted is not None]
        adv_rate = (
            sum(1 for r in adv_records if r.adversarial_resisted) / len(adv_records)
            if adv_records else None
        )

        # Failure breakdown
        breakdown: Dict[str, int] = {}
        for r in records:
            for f in r.failure_modes:
                k = f.value if isinstance(f, FailureMode) else str(f)
                breakdown[k] = breakdown.get(k, 0) + 1

        return BenchmarkSummary(
            total_runs=n,
            task_success_rate=round(successes / n, 4),
            avg_tool_precision=round(precision, 4),
            avg_tool_recall=round(recall, 4),
            avg_tool_f1=round(f1, 4),
            avg_argument_correctness=round(arg_corr, 4),
            total_unnecessary_tool_calls=unnecessary,
            avg_step_efficiency=round(step_eff, 4),
            avg_latency_ms=round(lat, 2),
            total_cost_usd=round(cost, 6),
            adversarial_resistance_rate=round(adv_rate, 4) if adv_rate is not None else None,
            failure_mode_breakdown=breakdown,
        )

    def export_results(self, result: BenchmarkSuiteResult, output_dir: Path) -> Tuple[Path, Path]:
        """Saves benchmark results to JSON and CSV formats."""
        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = output_dir / f"{result.suite_id}.json"
        csv_path = output_dir / f"{result.suite_id}.csv"

        # JSON
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(result.model_dump_json(indent=2))

        # CSV
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "scenario_id",
                "architecture",
                "model_name",
                "task_success",
                "tool_precision",
                "tool_recall",
                "tool_f1",
                "argument_correctness",
                "unnecessary_tool_calls",
                "step_count",
                "step_efficiency",
                "total_duration_ms",
                "estimated_cost_usd",
                "failure_modes",
                "adversarial_resisted",
                "termination_reason",
            ])
            for r in result.records:
                writer.writerow([
                    r.scenario_id,
                    r.architecture,
                    r.model_name,
                    r.task_success,
                    r.tool_precision,
                    r.tool_recall,
                    r.tool_f1,
                    r.argument_correctness,
                    r.unnecessary_tool_calls,
                    r.step_count,
                    r.step_efficiency,
                    r.total_duration_ms,
                    r.estimated_cost_usd,
                    ";".join([f.value for f in r.failure_modes]),
                    r.adversarial_resisted,
                    r.termination_reason,
                ])

        return json_path, csv_path

