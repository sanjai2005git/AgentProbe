"""
Scenario Schemas, Categories, and Ground-Truth Specifications.
"""

from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field


class ScenarioCategory(str, Enum):
    STANDARD_OPERATIONAL = "STANDARD_OPERATIONAL"
    EDGE_CASES = "EDGE_CASES"
    HALLUCINATION_TRAP = "HALLUCINATION_TRAP"
    INFINITE_LOOP_TRAP = "INFINITE_LOOP_TRAP"
    PREMATURE_STOP_TRAP = "PREMATURE_STOP_TRAP"
    CONSTRAINT_VIOLATION_TRAP = "CONSTRAINT_VIOLATION_TRAP"
    PROMPT_INJECTION_ADVERSARIAL = "PROMPT_INJECTION_ADVERSARIAL"
    APPROVAL_GATE_BYPASS = "APPROVAL_GATE_BYPASS"


class DifficultyLevel(str, Enum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"
    ADVERSARIAL = "ADVERSARIAL"


class Scenario(BaseModel):
    id: str
    category: ScenarioCategory
    title: str
    description: str
    user_prompt: str
    initial_db_state: Dict[str, Any] = Field(default_factory=dict)
    expected_tool_sequence: List[str] = Field(
        default_factory=list,
        description="Golden sequence of tools expected to be invoked."
    )
    forbidden_tools: List[str] = Field(
        default_factory=list,
        description="Tools that must NOT be called under policy constraints."
    )
    expected_outcome: str = Field(
        description="Expected final business state: e.g. 'REFUNDED', 'FLAGGED', 'ESCALATED', 'RETRY_SETTLED'"
    )
    expected_arguments: Dict[str, Any] = Field(
        default_factory=dict,
        description="Expected parameters for the terminal operational tool call."
    )
    requires_human_escalation: bool = False
    contains_injection: bool = False
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    tags: List[str] = Field(default_factory=list)

