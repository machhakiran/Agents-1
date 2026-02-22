"""Core orchestration: pipeline (ticket → PR), PR feedback."""

from .pipeline import run_pipeline

__all__ = ["run_pipeline"]
