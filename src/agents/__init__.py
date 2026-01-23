"""
Agents module - 7 bots for academic writing workflow
"""
from src.agents.requirements_analyzer import analyze_requirements_node
from src.agents.writer import write_text_node
from src.agents.citation_integrator import integrate_citations_node
from src.agents.word_count_checker import check_word_count_node
from src.agents.quality_checker import check_quality_node
from src.agents.ai_detector import check_ai_detection_node
from src.agents.references_generator import generate_references_node

__all__ = [
    "analyze_requirements_node",
    "write_text_node",
    "integrate_citations_node",
    "check_word_count_node",
    "check_quality_node",
    "check_ai_detection_node",
    "generate_references_node",
]
