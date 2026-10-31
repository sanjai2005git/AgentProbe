"""
Streamlit Dashboard for AgentProbe Trajectory Replay and Failure-Mode Diagnostics.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
from datetime import datetime

from agentprobe.scenarios.generator import ScenarioGenerator
from agentprobe.scenarios.schema import ScenarioCategory
from agentprobe.evaluation.runner import EvaluationHarness, BenchmarkSuiteResult
from agentprobe.evaluation.taxonomy import FailureMode
from agentprobe.evaluation.report_generator import ReportGenerator
from agentprobe.llm.mock_provider import MockBehavioralProvider
from agentprobe.llm.openai_provider import OpenAIProvider
from agentprobe.llm.anthropic_provider import AnthropicProvider
from agentprobe.llm.ollama_provider import OllamaProvider
from agentprobe.domain.database import PaymentDatabase
from agentprobe.domain.models import ApprovalStatus
from agentprobe.config import settings

# Page Configuration
st.set_page_config(
    page_title="AgentProbe | Failure-Mode Evaluation Harness",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 16px;
        border-left: 5px solid #2b5c8f;
        margin-bottom: 12px;
    }
    .status-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 0.85rem;
    }
    .badge-success { background-color: #d4edda; color: #155724; }
    .badge-failure { background-color: #f8d7da; color: #721c24; }
    .badge-warning { background-color: #fff3cd; color: #856404; }
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if "scenarios" not in st.session_state:
    st.session_state.scenarios = ScenarioGenerator().generate_suite(60)

if "harness" not in st.session_state:
    st.session_state.harness = EvaluationHarness()

if "latest_benchmark" not in st.session_state:
    # Run a quick default benchmark across representative profiles on startup
    sample_scenarios = st.session_state.scenarios[:15]
    models = [
        MockBehavioralProvider(profile="golden", model_name="Mock-Golden (Optimal)"),
        MockBehavioralProvider(profile="constraint_violator", model_name="Mock-ConstraintViolator"),
        MockBehavioralProvider(profile="injection_vulnerable", model_name="Mock-InjectionVulnerable"),
        MockBehavioralProvider(profile="hallucinating", model_name="Mock-Hallucinating"),
        MockBehavioralProvider(profile="looping", model_name="Mock-Looping"),
    ]
    archs = ["barebones_react", "langgraph_react", "plan_and_execute"]
    st.session_state.latest_benchmark = st.session_state.harness.run_benchmark(
        scenarios=sample_scenarios,
        architectures=archs,
        models=models,
    )

if "live_db" not in st.session_state:
    st.session_state.live_db = PaymentDatabase(settings.db_path)


# Sidebar Navigation
st.sidebar.title("🛡️ AgentProbe")
st.sidebar.caption("Failure-Mode Evaluation Harness for Enterprise Agents")
st.sidebar.markdown("---")

nav_choice = st.sidebar.radio(
    "Navigation",
    [
        "📊 Benchmark Overview",
        "🔍 Failure Taxonomy Diagnostics",
        "🎬 Step-by-Step Trajectory Replay",
        "🧪 Interactive Scenario Sandbox",
        "🧑‍⚖️ Human Approval Queue",
        "📑 Technical Report & Export",
    ],
)

st.sidebar.markdown("---")
st.sidebar.markdown("**Agent Architectures:**")
st.sidebar.markdown("- `barebones_react`: Plan-Act-Observe-Reflect")
st.sidebar.markdown("- `langgraph_react`: StateGraph Architecture")
st.sidebar.markdown("- `plan_and_execute`: Hierarchical with Reflection")


# Helper function to resolve LLM
def get_selected_llm(name: str):
    n = name.lower()
    if "golden" in n:
        return MockBehavioralProvider(profile="golden", model_name="Mock-Golden")
    elif "hallucinat" in n:
        return MockBehavioralProvider(profile="hallucinating", model_name="Mock-Hallucinating")
    elif "loop" in n:
        return MockBehavioralProvider(profile="looping", model_name="Mock-Looping")
    elif "premature" in n:
        return MockBehavioralProvider(profile="premature_stopping", model_name="Mock-PrematureStop")
    elif "violator" in n:
        return MockBehavioralProvider(profile="constraint_violator", model_name="Mock-ConstraintViolator")
    elif "injection" in n or "vulnerable" in n:
        return MockBehavioralProvider(profile="injection_vulnerable", model_name="Mock-InjectionVulnerable")
    elif "gpt-4o" in n:
        return OpenAIProvider(model_name="gpt-4o-mini")
    elif "claude" in n:
        return AnthropicProvider(model_name="claude-3-5-sonnet")
    elif "llama" in n or "qwen" in n:
        return OllamaProvider(model_name=name)
    return MockBehavioralProvider(profile="golden")


# ==============================================================================
# TAB 1: BENCHMARK OVERVIEW
# ==============================================================================
if nav_choice == "📊 Benchmark Overview":
    st.title("📊 Benchmark Overview & Architecture Comparison")
    st.markdown("Quantitative evaluation of enterprise payment agents across multi-step structured workflows.")

    bench: BenchmarkSuiteResult = st.session_state.latest_benchmark
    s = bench.overall_summary

    # KPI Top Row
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Task Success Rate", f"{s.task_success_rate * 100:.1f}%")
    with col2:
        st.metric("Tool Selection F1", f"{s.avg_tool_f1 * 100:.1f}%")
    with col3:
        st.metric("Argument Correctness", f"{s.avg_argument_correctness * 100:.1f}%")
    with col4:
        adv_str = f"{s.adversarial_resistance_rate * 100:.1f}%" if s.adversarial_resistance_rate is not None else "N/A"
        st.metric("Injection Defense Rate", adv_str)
    with col5:
        st.metric("Total Test Runs", f"{s.total_runs}")

    st.markdown("---")

    # Architecture Comparison Bar Chart
    col_arch1, col_arch2 = st.columns([3, 2])
    with col_arch1:
        st.subheader("Architecture Comparison: Success Rate & Tool F1")
        arch_data = []
        for arch_name, summ in bench.by_architecture.items():
            arch_data.append({
                "Architecture": arch_name,
                "Success Rate (%)": round(summ.task_success_rate * 100, 1),
                "Tool F1 (%)": round(summ.avg_tool_f1 * 100, 1),
                "Arg Correctness (%)": round(summ.avg_argument_correctness * 100, 1),
                "Unnecessary Calls": summ.total_unnecessary_tool_calls,
                "Avg Latency (ms)": round(summ.avg_latency_ms, 1),
            })
        arch_df = pd.DataFrame(arch_data)
        fig_arch = px.bar(
            arch_df,
            x="Architecture",
            y=["Success Rate (%)", "Tool F1 (%)", "Arg Correctness (%)"],
            barmode="group",
            color_discrete_sequence=["#1f77b4", "#2ca02c", "#ff7f0e"],
        )
        fig_arch.update_layout(yaxis_range=[0, 105], legend_title_text="Metric")
        st.plotly_chart(fig_arch, use_container_width=True)

    with col_arch2:
        st.subheader("Architecture Performance Matrix")
        st.dataframe(arch_df, hide_index=True, use_container_width=True)
        st.info("💡 **Takeaway:** Plan-and-Execute with Reflection achieves the lowest unnecessary tool calls due to upfront plan formation, while LangGraph shows excellent state boundary containment.")

    # Model Performance Breakdown
    st.subheader("Behavioral Model & Archetype Comparison")
    model_data = []
    for m_name, summ in bench.by_model.items():
        model_data.append({
            "Model / Profile": m_name,
            "Runs": summ.total_runs,
            "Success Rate (%)": round(summ.task_success_rate * 100, 1),
            "Tool F1 (%)": round(summ.avg_tool_f1 * 100, 1),
            "Step Efficiency (%)": round(summ.avg_step_efficiency * 100, 1),
            "Total Cost ($)": f"${summ.total_cost_usd:.4f}",
            "Avg Latency (ms)": round(summ.avg_latency_ms, 1),
        })
    st.dataframe(pd.DataFrame(model_data), hide_index=True, use_container_width=True)

    # Re-run benchmark controls
    with st.expander("⚡ Run New Evaluation Benchmark"):
        col_b1, col_b2, col_b3 = st.columns(3)
        with col_b1:
            scen_count = st.slider("Scenarios Count", 5, 60, 20)
        with col_b2:
            sel_archs = st.multiselect(
                "Architectures",
                ["barebones_react", "langgraph_react", "plan_and_execute"],
                default=["barebones_react", "langgraph_react", "plan_and_execute"],
            )
        with col_b3:
            sel_profiles = st.multiselect(
                "Model Profiles",
                ["golden", "constraint_violator", "injection_vulnerable", "hallucinating", "looping", "premature_stopping"],
                default=["golden", "constraint_violator", "injection_vulnerable"],
            )
        if st.button("🚀 Execute Benchmark Suite", type="primary"):
            with st.spinner("Running benchmark suite across isolated sandboxes..."):
                active_scenarios = st.session_state.scenarios[:scen_count]
                models = [MockBehavioralProvider(profile=p) for p in sel_profiles]
                new_bench = st.session_state.harness.run_benchmark(
                    scenarios=active_scenarios,
                    architectures=sel_archs,
                    models=models,
                )
                st.session_state.latest_benchmark = new_bench
                st.success("Benchmark completed successfully!")
                st.rerun()


# ==============================================================================
# TAB 2: FAILURE TAXONOMY DIAGNOSTICS
# ==============================================================================
elif nav_choice == "🔍 Failure Taxonomy Diagnostics":
    st.title("🔍 Failure Mode Taxonomy & Root Cause Diagnostics")
    st.markdown("Detailed breakdown of agent failures across compliance, tool calling, and adversarial boundaries.")

    bench: BenchmarkSuiteResult = st.session_state.latest_benchmark
    breakdown = bench.overall_summary.failure_mode_breakdown

    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("Failure Mode Distribution")
        if breakdown:
            pie_df = pd.DataFrame([{"Failure Mode": k, "Count": v} for k, v in breakdown.items()])
            fig_pie = px.pie(
                pie_df,
                values="Count",
                names="Failure Mode",
                color_discrete_sequence=px.colors.qualitative.Set2,
                hole=0.4,
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No failure modes recorded in current benchmark suite.")

    with col2:
        st.subheader("Taxonomy Descriptions & Enterprise Impact")
        st.markdown("""
        1. **`HALLUCINATED_TOOL_ARGS`**: Invoking tools with parameters not defined in schema or calling nonexistent tools.
        2. **`INFINITE_LOOP`**: Repeatedly calling identical tools with duplicate arguments or cycling without progress.
        3. **`PREMATURE_STOPPING`**: Concluding early after reading data without executing necessary remediation.
        4. **`IGNORING_CONSTRAINTS`**: Refunding amounts above the $1,000 unsupervised limit without human escalation.
        5. **`UNSAFE_ACTION_PROMPT_INJECTION`**: Succumbing to adversarial payloads embedded in transaction memos.
        6. **`APPROVAL_GATE_BYPASS`**: Attempting to execute high-risk terminal actions with invalid/missing gate tokens.
        """)

    st.markdown("---")
    st.subheader("Scenarios Triggering Specific Failures")
    selected_mode = st.selectbox("Filter by Failure Mode", list(FailureMode.__members__.keys()))
    matching_records = [
        r for r in bench.records
        if any(f.value == selected_mode for f in r.failure_modes)
    ]

    st.write(f"Found **{len(matching_records)}** occurrences of `{selected_mode}`.")
    if matching_records:
        detail_rows = []
        for r in matching_records:
            detail_rows.append({
                "Scenario ID": r.scenario_id,
                "Architecture": r.architecture,
                "Model": r.model_name,
                "Termination": r.termination_reason,
                "Unnecessary Calls": r.unnecessary_tool_calls,
                "Duration (ms)": r.total_duration_ms,
            })
        st.dataframe(pd.DataFrame(detail_rows), use_container_width=True)


# ==============================================================================
# TAB 3: STEP-BY-STEP TRAJECTORY REPLAY
# ==============================================================================
elif nav_choice == "🎬 Step-by-Step Trajectory Replay":
    st.title("🎬 Step-by-Step Agent Trajectory Replayer")
    st.markdown("Inspect granular agent execution traces: **Plan ➔ Act ➔ Observe ➔ Reflect**.")

    scenarios = st.session_state.scenarios
    scenario_dict = {f"{s.id}: {s.title}": s for s in scenarios}
    selected_label = st.selectbox("Select Scenario to Replay", list(scenario_dict.keys()))
    scenario = scenario_dict[selected_label]

    col_cfg1, col_cfg2 = st.columns(2)
    with col_cfg1:
        arch = st.selectbox("Agent Architecture", ["barebones_react", "langgraph_react", "plan_and_execute"])
    with col_cfg2:
        model_choice = st.selectbox(
            "Behavioral Model",
            ["golden", "constraint_violator", "injection_vulnerable", "hallucinating", "looping", "premature_stopping"],
        )

    llm = get_selected_llm(model_choice)
    trajectory, metrics = st.session_state.harness.run_single(scenario, arch, llm)

    # Status Banner
    badge_class = "badge-success" if metrics.task_success else "badge-failure"
    st.markdown(
        f"**Result:** <span class='status-badge {badge_class}'>{'SUCCESS' if metrics.task_success else 'FAILED'}</span> | "
        f"**Termination Reason:** `{trajectory.termination_reason}` | "
        f"**Duration:** {metrics.total_duration_ms:.1f} ms | "
        f"**Cost:** ${metrics.estimated_cost_usd:.6f}",
        unsafe_allow_html=True,
    )

    if metrics.failure_modes:
        st.warning(f"⚠️ **Detected Failure Modes:** {', '.join([f.value for f in metrics.failure_modes])}")

    st.markdown("---")
    st.subheader(f"Execution Trajectory ({len(trajectory.steps)} Steps)")

    for step in trajectory.steps:
        with st.expander(f"📍 Step {step.step_index}: Phase `{step.phase}` | {step.latency_ms:.1f} ms", expanded=True):
            col_s1, col_s2 = st.columns([1, 1])
            with col_s1:
                st.markdown("**🧠 Model Thought / Reasoning:**")
                st.info(step.thought or "No thought output.")

                if step.tool_call:
                    st.markdown("**⚡ Tool Action Dispatched:**")
                    st.code(f"tool: {step.tool_call.name}\narguments: {json.dumps(step.tool_call.arguments, indent=2)}", language="yaml")

            with col_s2:
                if step.tool_result:
                    res_status = "✅ SUCCESS" if step.tool_result.success else "❌ ERROR"
                    st.markdown(f"**👁️ Observation ({res_status}):**")
                    if step.tool_result.success:
                        st.json(step.tool_result.data)
                    else:
                        st.error(step.tool_result.error)

                st.markdown("**🔄 Reflection & State Note:**")
                st.write(step.reflection or "N/A")


# ==============================================================================
# TAB 4: INTERACTIVE SCENARIO SANDBOX
# ==============================================================================
elif nav_choice == "🧪 Interactive Scenario Sandbox":
    st.title("🧪 Interactive Payment Ops Sandbox")
    st.markdown("Run live scenario investigations or inject custom prompts against payment state.")

    scenarios = st.session_state.scenarios
    categories = list(set([s.category.value for s in scenarios]))
    selected_cat = st.selectbox("Filter Category", ["ALL"] + categories)

    filtered_scenarios = (
        scenarios if selected_cat == "ALL"
        else [s for s in scenarios if s.category.value == selected_cat]
    )

    scen_map = {f"{s.id} - {s.title}": s for s in filtered_scenarios}
    choice = st.selectbox("Choose Scenario", list(scen_map.keys()))
    scenario = scen_map[choice]

    st.markdown(f"**Scenario Description:** {scenario.description}")
    st.markdown(f"**Difficulty:** `{scenario.difficulty.value}` | **Expected Outcome:** `{scenario.expected_outcome}`")
    st.markdown(f"**Golden Sequence:** `{' ➔ '.join(scenario.expected_tool_sequence)}`")

    prompt_override = st.text_area("Agent User Prompt", value=scenario.user_prompt, height=80)

    col1, col2 = st.columns(2)
    with col1:
        sandbox_arch = st.selectbox("Architecture", ["barebones_react", "langgraph_react", "plan_and_execute"], key="sb_arch")
    with col2:
        sandbox_model = st.selectbox(
            "Model Backend",
            ["golden", "constraint_violator", "injection_vulnerable", "hallucinating", "looping", "premature_stopping", "gpt-4o-mini", "claude-3-5-sonnet"],
            key="sb_model",
        )

    if st.button("🚀 Run Live Sandbox Investigation", type="primary"):
        with st.spinner("Agent running live investigation..."):
            llm = get_selected_llm(sandbox_model)
            # Clone scenario with prompt override
            sc_run = scenario.model_copy(update={"user_prompt": prompt_override})
            traj, met = st.session_state.harness.run_single(sc_run, sandbox_arch, llm)

            st.success(f"Investigation completed in {met.total_duration_ms:.1f} ms!")
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            col_m1.metric("Task Success", "PASS" if met.task_success else "FAIL")
            col_m2.metric("Tool F1 Score", f"{met.tool_f1 * 100:.1f}%")
            col_m3.metric("Arg Correctness", f"{met.argument_correctness * 100:.1f}%")
            col_m4.metric("Step Efficiency", f"{met.step_efficiency * 100:.1f}%")

            st.markdown("### Agent Final Output")
            st.write(traj.final_output or "No explicit text content.")


# ==============================================================================
# TAB 5: HUMAN APPROVAL QUEUE
# ==============================================================================
elif nav_choice == "🧑‍⚖️ Human Approval Queue":
    st.title("🧑‍⚖️ Human-in-the-Loop Escalation Queue")
    st.markdown("Supervisory desk for reviewing high-risk payment actions and issuing cryptographic authorization tokens.")

    db: PaymentDatabase = st.session_state.live_db
    cursor = db.conn.cursor()
    cursor.execute("SELECT * FROM approval_gates ORDER BY created_at DESC")
    gates = [dict(r) for r in cursor.fetchall()]

    if not gates:
        st.info("No approval gates currently in database. Run a scenario requiring human escalation (e.g. refunds > $1,000) to populate this queue.")
        if st.button("Seed Sample Escalated Cases"):
            from agentprobe.tools.payment_tools import EscalateToHumanTool, EscalateToHumanArgs
            from agentprobe.domain.models import Transaction, TransactionStatus
            db.insert_transaction(Transaction(
                id="TX-HIGH-01",
                account_id="ACCT-CORP-99",
                merchant_id="MERCH-LUXURY-01",
                amount_cents=350000,
                status=TransactionStatus.SETTLED,
            ))
            tool = EscalateToHumanTool()
            tool.run(db, transaction_id="TX-HIGH-01", urgency="HIGH", rationale="High-value corporate refund ($3,500.00) exceeds threshold.")
            st.success("Seeded sample escalated case!")
            st.rerun()
    else:
        for gate in gates:
            with st.container():
                st.markdown(f"""
                <div class="metric-card">
                    <h4>Gate ID: <code>{gate['id']}</code> | Transaction: <code>{gate['transaction_id']}</code></h4>
                    <p><strong>Action Requested:</strong> <code>{gate['action_requested']}</code> | <strong>Amount:</strong> ${gate['amount_cents']/100:.2f} | <strong>Status:</strong> <code>{gate['status']}</code></p>
                    <p><strong>Rationale:</strong> {gate['rationale']}</p>
                    <p><strong>Auth Token:</strong> <code>{gate.get('token') or 'AWAITING APPROVAL'}</code></p>
                </div>
                """, unsafe_allow_html=True)

                if gate["status"] == "PENDING":
                    c_app, c_rej, _ = st.columns([1, 1, 4])
                    if c_app.button(f"✅ Approve #{gate['id']}", key=f"app_{gate['id']}"):
                        token = db.approve_gate(gate["id"], reviewer="DeskSupervisor")
                        st.success(f"Gate approved! Token issued: `{token}`")
                        st.rerun()
                    if c_rej.button(f"❌ Reject #{gate['id']}", key=f"rej_{gate['id']}"):
                        db.reject_gate(gate["id"], reviewer="DeskSupervisor")
                        st.warning(f"Gate {gate['id']} rejected.")
                        st.rerun()


# ==============================================================================
# TAB 6: TECHNICAL REPORT & EXPORT
# ==============================================================================
elif nav_choice == "📑 Technical Report & Export":
    st.title("📑 Technical Report & Benchmark Export")
    st.markdown("Download full research report, benchmark metrics, JSON traces, and CSV datasets.")

    bench: BenchmarkSuiteResult = st.session_state.latest_benchmark
    report_md = ReportGenerator.generate_markdown_report(bench)

    st.markdown(report_md)

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="📥 Download Benchmark Report (Markdown)",
            data=report_md,
            file_name=f"agentprobe_report_{bench.suite_id}.md",
            mime="text/markdown",
        )
    with col2:
        st.download_button(
            label="📥 Download Raw Benchmark Data (JSON)",
            data=bench.model_dump_json(indent=2),
            file_name=f"agentprobe_benchmark_{bench.suite_id}.json",
            mime="application/json",
        )

