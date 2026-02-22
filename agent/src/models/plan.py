"""Implementation plan model (F3.1, F3.3)."""

from pydantic import BaseModel, Field


class PlanStep(BaseModel):
    """Single step in the implementation plan."""

    file_path: str = Field(..., description="Relative path to file")
    action: str = Field(..., description="create | modify | delete")
    reason: str = Field(default="", description="Short rationale")


class ImplementationPlan(BaseModel):
    """Structured plan: which files to create/modify and why (F3.1)."""

    steps: list[PlanStep] = Field(default_factory=list)
    summary: str = Field(default="", description="Optional high-level summary")
