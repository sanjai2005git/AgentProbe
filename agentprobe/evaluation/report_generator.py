"""
Markdown and Tabular Report Generator for Evaluation Results.
"""

from typing import Dict, Any
from agentprobe.evaluation.runner import BenchmarkSuiteResult, BenchmarkSummary


class ReportGenerator:
    """Generates formatted technical evaluation summaries and comparison tables."""

    @staticmethod
    def generate_markdown_report(result: BenchmarkSuiteResult) -> str:
        s = result.overall_summary
        md = []
        md.append(f"# AgentProbe Evaluation Benchmark Report")
        md.append(f"**Suite ID:** `{result.suite_id}` | **Generated:** {result.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        md.append(f"**Scenarios Evaluated:** {result.scenarios_evaluated} | **Total Test Runs:** {s.total_runs}\n")

        # Executive Summary Table
        md.append("## 1. Executive Performance Summary\n")
        md.append("| Metric | Result |")
        md.append("| :--- | :--- |")
        md.append(f"| **Overall Task Success Rate** | **{s.task_success_rate * 100:.1f}%** |")
        md.append(f"| **Tool Selection F1-Score** | {s.avg_tool_f1 * 100:.1f}% |")
        md.append(f"| **Tool Precision / Recall** | {s.avg_tool_precision * 100:.1f}% / {s.avg_tool_recall * 100:.1f}% |")
        md.append(f"| **Argument Correctness** | {s.avg_argument_correctness * 100:.1f}% |")
        md.append(f"| **Unnecessary Tool Calls (Waste)** | {s.total_unnecessary_tool_calls} calls |")
        md.append(f"| **Step Efficiency** | {s.avg_step_efficiency * 100:.1f}% |")
        md.append(f"| **Average Execution Latency** | {s.avg_latency_ms:.1f} ms |")
        md.append(f"| **Total Estimated Cost** | ${s.total_cost_usd:.4f} USD |")
        if s.adversarial_resistance_rate is not None:
            md.append(f"| **Adversarial Injection Defense Rate** | **{s.adversarial_resistance_rate * 100:.1f}%** |")
        md.append("")

        # Failure Taxonomy Matrix
        md.append("## 2. Failure Mode Taxonomy Breakdown\n")
        if s.failure_mode_breakdown:
            md.append("| Failure Mode Category | Occurrences | % of Total Runs |")
            md.append("| :--- | :---: | :---: |")
            for mode, count in sorted(s.failure_mode_breakdown.items(), key=lambda x: x[1], reverse=True):
                pct = (count / s.total_runs) * 100
                md.append(f"| `{mode}` | {count} | {pct:.1f}% |")
        else:
            md.append("No failure modes observed. Perfect compliance across all test runs.")
        md.append("")

        # Architecture Comparison
        md.append("## 3. Architecture Comparison (ReAct vs LangGraph vs Plan-and-Execute)\n")
        md.append("| Architecture | Runs | Success Rate | Tool F1 | Arg Correctness | Unnecessary Calls | Avg Latency |")
        md.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: |")
        for arch, summ in result.by_architecture.items():
            md.append(
                f"| `{arch}` | {summ.total_runs} | {summ.task_success_rate * 100:.1f}% | "
                f"{summ.avg_tool_f1 * 100:.1f}% | {summ.avg_argument_correctness * 100:.1f}% | "
                f"{summ.total_unnecessary_tool_calls} | {summ.avg_latency_ms:.1f} ms |"
            )
        md.append("")

        # Model Comparison
        md.append("## 4. Model Behavioral Profile Comparison\n")
        md.append("| Model / Profile | Runs | Success Rate | Tool F1 | Injection Resisted | Total Cost |")
        md.append("| :--- | :---: | :---: | :---: | :---: | :---: |")
        for model_name, summ in result.by_model.items():
            adv_str = f"{summ.adversarial_resistance_rate * 100:.1f}%" if summ.adversarial_resistance_rate is not None else "N/A"
            md.append(
                f"| `{model_name}` | {summ.total_runs} | {summ.task_success_rate * 100:.1f}% | "
                f"{summ.avg_tool_f1 * 100:.1f}% | {adv_str} | ${summ.total_cost_usd:.4f} |"
            )
        md.append("")

        return "\n".join(md)

