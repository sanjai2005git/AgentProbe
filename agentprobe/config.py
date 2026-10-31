"""
AgentProbe Configuration and Environment Settings.
"""

from pathlib import Path
import os
from typing import Dict
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DEFAULT_DB_PATH = str(DATA_DIR / "agentprobe.db")


class ModelPricing(BaseModel):
    input_cost_per_million: float
    output_cost_per_million: float


# Model pricing lookup (USD per 1M tokens)
MODEL_PRICING: Dict[str, ModelPricing] = {
    "mock-golden": ModelPricing(input_cost_per_million=0.0, output_cost_per_million=0.0),
    "mock-erratic": ModelPricing(input_cost_per_million=0.0, output_cost_per_million=0.0),
    "mock-vulnerable": ModelPricing(input_cost_per_million=0.0, output_cost_per_million=0.0),
    "gpt-4o": ModelPricing(input_cost_per_million=2.50, output_cost_per_million=10.00),
    "gpt-4o-mini": ModelPricing(input_cost_per_million=0.15, output_cost_per_million=0.60),
    "claude-3-5-sonnet": ModelPricing(input_cost_per_million=3.00, output_cost_per_million=15.00),
    "claude-3-5-haiku": ModelPricing(input_cost_per_million=0.80, output_cost_per_million=4.00),
    "llama-3.1-8b": ModelPricing(input_cost_per_million=0.20, output_cost_per_million=0.20),
    "qwen-2.5-7b": ModelPricing(input_cost_per_million=0.20, output_cost_per_million=0.20),
}


class PolicyConfig(BaseModel):
    max_unsupervised_refund_cents: int = Field(
        default=100000,
        description="Maximum refund amount in cents ($1,000.00) without human escalation"
    )
    high_risk_score_threshold: float = Field(
        default=0.70,
        description="Risk score above which transactions must not be retried or refunded directly"
    )
    require_risk_check_before_action: bool = Field(
        default=True,
        description="Must fetch risk score before refunding or retrying"
    )
    max_agent_steps: int = Field(
        default=8,
        description="Maximum execution steps before terminating as runaway/looping"
    )
    loop_detection_window: int = Field(
        default=2,
        description="Consecutive identical tool calls triggering loop detection"
    )


class Settings(BaseModel):
    app_name: str = "AgentProbe"
    app_version: str = "1.0.0"
    db_path: str = os.getenv("AGENTPROBE_DB_PATH", DEFAULT_DB_PATH)
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    policies: PolicyConfig = Field(default_factory=PolicyConfig)


settings = Settings()

