"""LangGraph workflow package (AI_ARCHITECTURE.md §11)."""

from ai.graphs.workflow import (
    NODE_AGGREGATE_RESPONSE,
    NODE_ASSEMBLE_CITATIONS,
    NODE_BUILD_CONTEXT,
    NODE_CLARIFY,
    NODE_DETECT_INTENT,
    NODE_GENERATE,
    NODE_PERSIST,
    NODE_RETRIEVE,
    NODE_ROUTE,
    build_workflow,
    detect_intent,
    route,
    route_after_detect,
)

__all__ = [
    "NODE_AGGREGATE_RESPONSE",
    "NODE_ASSEMBLE_CITATIONS",
    "NODE_BUILD_CONTEXT",
    "NODE_CLARIFY",
    "NODE_DETECT_INTENT",
    "NODE_GENERATE",
    "NODE_PERSIST",
    "NODE_RETRIEVE",
    "NODE_ROUTE",
    "build_workflow",
    "detect_intent",
    "route",
    "route_after_detect",
]
