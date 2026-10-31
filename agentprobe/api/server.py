"""
FastAPI Server for AgentProbe Evaluation, Payment Ops Investigation, and Human-in-the-Loop Gates.
"""

from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field

from agentprobe.domain.database import PaymentDatabase
from agentprobe.domain.models import ApprovalGate, ApprovalStatus
from agentprobe.scenarios.schema import Scenario, ScenarioCategory
from agentprobe.scenarios.dataset import get_curated_scenarios
from agentprobe.scenarios.generator import ScenarioGenerator
from agentprobe.evaluation.runner import EvaluationHarness, BenchmarkSuiteResult
from agentprobe.evaluation.metrics import EvaluationMetricRecord
from agentprobe.llm.mock_provider import MockBehavioralProvider
from agentprobe.llm.openai_provider import OpenAIProvider
from agentprobe.llm.anthropic_provider import AnthropicProvider
from agentprobe.llm.ollama_provider import OllamaProvider
from agentprobe.config import settings

app = FastAPI(
    title="AgentProbe API",
    version=settings.app_version,
    description="Evaluation harness, failure-mode diagnostics, and payment ops agent service.",
)

# Persistent DB instance for live operations
live_db = PaymentDatabase(settings.db_path)
harness = EvaluationHarness()


class SingleEvalRequest(BaseModel):
    scenario_id: str
    architecture: str = Field(default="barebones_react", description="'barebones_react', 'langgraph_react', 'plan_and_execute'")
    model_name: str = Field(default="golden", description="'golden', 'hallucinating', 'looping', 'premature_stopping', 'constraint_violator', 'injection_vulnerable', 'gpt-4o-mini', 'claude-3-5-sonnet'")


class BenchmarkRequest(BaseModel):
    scenario_count: int = Field(default=20, ge=1, le=100)
    architectures: List[str] = Field(default=["barebones_react", "langgraph_react", "plan_and_execute"])
    models: List[str] = Field(default=["golden", "hallucinating", "looping", "constraint_violator", "injection_vulnerable"])


class InvestigateRequest(BaseModel):
    transaction_id: str
    prompt: str
    architecture: str = "barebones_react"
    model_name: str = "golden"


class ApprovalDecisionRequest(BaseModel):
    reviewer_name: str = "SupervisorOps"


def _resolve_llm(model_name: str):
    m = model_name.lower()
    if m in ["golden", "hallucinating", "looping", "premature_stopping", "constraint_violator", "injection_vulnerable"]:
        return MockBehavioralProvider(profile=m)
    elif "gpt" in m:
        return OpenAIProvider(model_name=m)
    elif "claude" in m:
        return AnthropicProvider(model_name=m)
    elif "llama" in m or "qwen" in m:
        return OllamaProvider(model_name=m)
    return MockBehavioralProvider(profile="golden")


def _normalize_scen_id(sid: str) -> str:
    cleaned = sid.strip().upper()
    if cleaned.isdigit():
        return f"SCEN-{int(cleaned):03d}"
    if cleaned.startswith("SCEN-"):
        parts = cleaned.split("-", 1)
        if parts[1].isdigit():
            return f"SCEN-{int(parts[1]):03d}"
    return cleaned


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "AgentProbe Evaluation Harness",
        "version": settings.app_version,
        "database": settings.db_path,
    }


@app.get("/scenarios", response_model=List[Scenario])
def list_scenarios(
    category: Optional[ScenarioCategory] = None,
    limit: int = Query(default=100, ge=1, le=200),
):
    scenarios = ScenarioGenerator().generate_suite(limit)
    if category:
        scenarios = [s for s in scenarios if s.category == category]
    return scenarios


@app.get("/scenarios/{scenario_id}")
def get_scenario(scenario_id: str):
    scenarios = ScenarioGenerator().generate_suite(100)
    norm_id = _normalize_scen_id(scenario_id)
    found = next((s for s in scenarios if s.id.upper() == norm_id), None)
    if not found:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found.")
    return found


@app.post("/eval/run-single")
def run_single_eval(req: SingleEvalRequest):
    scenarios = ScenarioGenerator().generate_suite(100)
    norm_id = _normalize_scen_id(req.scenario_id)
    scenario = next((s for s in scenarios if s.id.upper() == norm_id), None)
    if not scenario:
        raise HTTPException(status_code=404, detail=f"Scenario '{req.scenario_id}' not found.")

    llm = _resolve_llm(req.model_name)
    trajectory, metrics = harness.run_single(
        scenario=scenario,
        architecture=req.architecture,
        llm=llm,
    )

    return {
        "scenario_id": scenario.id,
        "metrics": metrics,
        "trajectory": trajectory,
    }


@app.post("/eval/benchmark", response_model=BenchmarkSuiteResult)
def run_benchmark(req: BenchmarkRequest):
    scenarios = ScenarioGenerator().generate_suite(req.scenario_count)
    models = [_resolve_llm(m) for m in req.models]
    result = harness.run_benchmark(
        scenarios=scenarios,
        architectures=req.architectures,
        models=models,
    )
    return result


@app.post("/investigate")
def investigate_transaction(req: InvestigateRequest):
    tx = live_db.get_transaction(req.transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail=f"Transaction '{req.transaction_id}' not found in live database.")

    llm = _resolve_llm(req.model_name)
    from agentprobe.agents.factory import create_agent
    agent = create_agent(architecture=req.architecture, llm=llm, tools=harness.tools)

    trajectory = agent.run(task_prompt=req.prompt, db=live_db)
    return {
        "transaction_id": req.transaction_id,
        "trajectory": trajectory,
        "final_output": trajectory.final_output,
    }


@app.get("/approval-gates")
def list_approval_gates(status: Optional[ApprovalStatus] = None):
    # Fetch from live DB
    cursor = live_db.conn.cursor()
    if status:
        cursor.execute("SELECT * FROM approval_gates WHERE status = ?", (status.value,))
    else:
        cursor.execute("SELECT * FROM approval_gates ORDER BY created_at DESC")
    rows = cursor.fetchall()
    return [dict(r) for r in rows]


@app.post("/approval-gates/{gate_id}/approve")
def approve_gate(gate_id: str, req: ApprovalDecisionRequest):
    token = live_db.approve_gate(gate_id, reviewer=req.reviewer_name)
    if not token:
        raise HTTPException(status_code=400, detail="Gate not found or already reviewed.")
    return {"gate_id": gate_id, "status": "APPROVED", "token": token}


@app.post("/approval-gates/{gate_id}/reject")
def reject_gate(gate_id: str, req: ApprovalDecisionRequest):
    ok = live_db.reject_gate(gate_id, reviewer=req.reviewer_name)
    if not ok:
        raise HTTPException(status_code=400, detail="Gate not found or already reviewed.")
    return {"gate_id": gate_id, "status": "REJECTED"}
