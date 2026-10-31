"""
Tests for Scenarios Dataset, Ground Truth Specifications, and Scaling Generator.
"""

from agentprobe.scenarios.dataset import get_curated_scenarios
from agentprobe.scenarios.generator import ScenarioGenerator
from agentprobe.scenarios.schema import ScenarioCategory


def test_curated_dataset_integrity():
    scenarios = get_curated_scenarios()
    assert len(scenarios) == 60

    # Ensure all scenarios have required attributes
    for s in scenarios:
        assert s.id.startswith("SCEN-")
        assert len(s.user_prompt) > 0
        assert len(s.expected_tool_sequence) >= 2
        assert s.expected_outcome in ["REFUNDED", "FLAGGED", "RETRY_SETTLED", "ESCALATED"]


def test_scenario_categories_distribution():
    scenarios = get_curated_scenarios()
    categories = [s.category for s in scenarios]

    assert ScenarioCategory.STANDARD_OPERATIONAL in categories
    assert ScenarioCategory.EDGE_CASES in categories
    assert ScenarioCategory.CONSTRAINT_VIOLATION_TRAP in categories
    assert ScenarioCategory.PROMPT_INJECTION_ADVERSARIAL in categories
    assert ScenarioCategory.INFINITE_LOOP_TRAP in categories


def test_scenario_generator_scaling_to_100():
    generator = ScenarioGenerator(seed=123)
    suite = generator.generate_suite(100)
    assert len(suite) == 100

    # Verify unique IDs
    ids = [s.id for s in suite]
    assert len(ids) == len(set(ids))

