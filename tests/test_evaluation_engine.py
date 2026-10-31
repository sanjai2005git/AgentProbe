"""
Tests for Evaluation Metrics, Failure Taxonomy Classifier, and Benchmark Suite Runner.
"""

from agentprobe.scenarios.generator import ScenarioGenerator
from agentprobe.evaluation.runner import EvaluationHarness
from agentprobe.evaluation.taxonomy import FailureMode
from agentprobe.llm.mock_provider import MockBehavioralProvider


def test_harness_single_golden_run():
    scenarios = ScenarioGenerator().generate_suite(1)
    scenario = scenarios[0]

    harness = EvaluationHarness()
    llm = MockBehavioralProvider(profile="golden")

    trajectory, metrics = harness.run_single(
        scenario=scenario,
        architecture="barebones_react",
        llm=llm,
    )

    assert metrics.task_success is True
    assert metrics.tool_f1 >= 0.80
    assert len(metrics.failure_modes) == 0


def test_harness_constraint_violator_classification():
    # Find a high-value scenario requiring human escalation
    scenarios = ScenarioGenerator().generate_suite(60)
    high_value_scen = next(s for s in scenarios if s.requires_human_escalation and not s.contains_injection)

    harness = EvaluationHarness()
    # Constraint violator tries to refund directly without escalation
    llm = MockBehavioralProvider(profile="constraint_violator")

    trajectory, metrics = harness.run_single(
        scenario=high_value_scen,
        architecture="barebones_react",
        llm=llm,
    )

    assert metrics.task_success is False
    assert (
        FailureMode.APPROVAL_GATE_BYPASS in metrics.failure_modes
        or FailureMode.IGNORING_CONSTRAINTS in metrics.failure_modes
    )


def test_harness_adversarial_injection_classification():
    # Find prompt injection scenario
    scenarios = ScenarioGenerator().generate_suite(60)
    injection_scen = next(s for s in scenarios if s.contains_injection)

    harness = EvaluationHarness()

    # 1. Golden LLM should resist and escalate
    golden_llm = MockBehavioralProvider(profile="golden")
    _, golden_met = harness.run_single(injection_scen, "barebones_react", golden_llm)
    assert golden_met.adversarial_resisted is True

    # 2. Injection vulnerable LLM should succumb
    vulnerable_llm = MockBehavioralProvider(profile="injection_vulnerable")
    _, vuln_met = harness.run_single(injection_scen, "barebones_react", vulnerable_llm)
    assert vuln_met.adversarial_resisted is False
    assert FailureMode.UNSAFE_ACTION_PROMPT_INJECTION in vuln_met.failure_modes


def test_benchmark_suite_execution():
    scenarios = ScenarioGenerator().generate_suite(5)
    harness = EvaluationHarness()

    models = [
        MockBehavioralProvider(profile="golden", model_name="Mock-Golden"),
        MockBehavioralProvider(profile="looping", model_name="Mock-Looping"),
    ]
    archs = ["barebones_react", "langgraph_react"]

    result = harness.run_benchmark(
        scenarios=scenarios,
        architectures=archs,
        models=models,
    )

    # 5 scenarios * 2 architectures * 2 models = 20 test runs
    assert len(result.records) == 20
    assert result.overall_summary.total_runs == 20
    assert "barebones_react" in result.by_architecture
    assert "langgraph_react" in result.by_architecture
    assert "Mock-Golden" in result.by_model
    assert "Mock-Looping" in result.by_model

