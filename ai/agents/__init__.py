"""Phase 8 agents (AI_ARCHITECTURE.md §3.2).

Public surface of the agent package: the Coordinator entry agent (rule-based or
LLM-backed), the data-driven Agent Manager registry, the intent-classifier
interface, and the specialist agents. The Admission and Examination agents are
delivered specialists (AI_ARCHITECTURE.md §5-6); the FAQ agent follows the same
shared-machinery contract (§3.5, §8).
"""

from ai.agents.admission import AdmissionAgent, create_admission_agent
from ai.agents.base import GenerationResult, SpecialistAgent
from ai.agents.coordinator import (
    DEFAULT_CONFIDENCE_THRESHOLD,
    CoordinatorAgent,
    create_coordinator,
    create_llm_coordinator,
)
from ai.agents.examination import ExaminationAgent, create_examination_agent
from ai.agents.intent_classifier import (
    IntentClassifier,
    IntentResult,
    LLMIntentClassifier,
    RuleBasedIntentClassifier,
)
from ai.agents.registry import AgentInfo, AgentRegistry, default_registry

__all__ = [
    "DEFAULT_CONFIDENCE_THRESHOLD",
    "AdmissionAgent",
    "AgentInfo",
    "AgentRegistry",
    "CoordinatorAgent",
    "ExaminationAgent",
    "GenerationResult",
    "IntentClassifier",
    "IntentResult",
    "LLMIntentClassifier",
    "RuleBasedIntentClassifier",
    "SpecialistAgent",
    "create_admission_agent",
    "create_coordinator",
    "create_examination_agent",
    "create_llm_coordinator",
    "default_registry",
]
