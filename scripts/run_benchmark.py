"""
CLI Benchmark Runner Script for AgentProbe.
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agentprobe.scenarios.generator import ScenarioGenerator
from agentprobe.evaluation.runner import EvaluationHarness
from agentprobe.evaluation.report_generator import ReportGenerator
from agentprobe.llm.mock_provider import MockBehavioralProvider
from agentprobe.llm.openai_provider import OpenAIProvider
from agentprobe.llm.anthropic_provider import AnthropicProvider
from agentprobe.llm.ollama_provider import OllamaProvider


def resolve_llm_provider(name: str):
    n = name.lower()
    if n in ["golden", "hallucinating", "looping", "premature_stopping", "constraint_violator", "injection_vulnerable"]:
        return MockBehavioralProvider(profile=n, model_name=f"Mock-{n}")
    elif "gpt" in n:
        return OpenAIProvider(model_name=n)
    elif "claude" in n:
        return AnthropicProvider(model_name=n)
    elif "llama" in n or "qwen" in n:
        return OllamaProvider(model_name=n)
    return MockBehavioralProvider(profile="golden", model_name="Mock-golden")


def main():
    parser = argparse.ArgumentParser(description="AgentProbe Benchmark Evaluation CLI")
    parser.add_argument("--count", type=int, default=20, help="Number of scenarios to evaluate (up to 100)")
    parser.add_argument(
        "--architectures",
        nargs="+",
        default=["barebones_react", "langgraph_react", "plan_and_execute"],
        help="Agent architectures to evaluate",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=["golden", "constraint_violator", "injection_vulnerable", "hallucinating", "looping"],
        help="Model behavioral profiles or API model names",
    )
    parser.add_argument("--output-dir", type=str, default="benchmark_results", help="Directory to save artifacts")
    args = parser.parse_args()

    print("================================================================")
    print(" [AgentProbe] Evaluation Benchmark Harness")
    print("================================================================")
    print(f"Scenarios:      {args.count}")
    print(f"Architectures:  {', '.join(args.architectures)}")
    print(f"Models:         {', '.join(args.models)}")
    print(f"Output Dir:     {args.output_dir}\n")

    # Generate test suite
    print("Generating scenario dataset...")
    scenarios = ScenarioGenerator().generate_suite(args.count)
    print(f"Loaded {len(scenarios)} ground-truth scenarios.")

    # Initialize harness
    harness = EvaluationHarness()
    models = [resolve_llm_provider(m) for m in args.models]

    print("Running evaluation across isolated sandboxes...")
    result = harness.run_benchmark(
        scenarios=scenarios,
        architectures=args.architectures,
        models=models,
    )

    out_path = Path(args.output_dir)
    json_path, csv_path = harness.export_results(result, out_path)
    print(f"Exported JSON: {json_path}")
    print(f"Exported CSV:  {csv_path}")

    # Generate and save report
    report_md = ReportGenerator.generate_markdown_report(result)
    report_path = out_path / f"{result.suite_id}_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)
    print(f"Exported Report: {report_path}\n")

    # Print summary
    s = result.overall_summary
    print("----------------------------------------------------------------")
    print(" EXECUTIVE BENCHMARK RESULTS")
    print("----------------------------------------------------------------")
    print(f"Total Test Runs:         {s.total_runs}")
    print(f"Task Success Rate:       {s.task_success_rate * 100:.1f}%")
    print(f"Tool Selection F1:       {s.avg_tool_f1 * 100:.1f}%")
    print(f"Argument Correctness:    {s.avg_argument_correctness * 100:.1f}%")
    print(f"Unnecessary Tool Calls:  {s.total_unnecessary_tool_calls}")
    print(f"Avg Latency:             {s.avg_latency_ms:.1f} ms")
    if s.adversarial_resistance_rate is not None:
        print(f"Injection Defense Rate:  {s.adversarial_resistance_rate * 100:.1f}%")
    print("----------------------------------------------------------------")


if __name__ == "__main__":
    main()

